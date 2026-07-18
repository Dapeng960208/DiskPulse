# -*- coding: utf-8 -*-
import asyncio
from copy import copy
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from models import User
from services.audit_service import ai_tool_actor_context
from utils.auth_service import is_super_admin
from utils.security import issue_token


class _ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class ToolParameter:
    name: str
    alias: str
    in_path: bool


@dataclass(frozen=True)
class AIToolDefinition:
    name: str
    description: str
    route_path: str
    input_model: type[_ToolInput]
    parameters: tuple[ToolParameter, ...]
    method: str = "GET"
    system_management: bool = False


_READ_ONLY_METHODS = {"GET"}
_SYSTEM_MANAGEMENT_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}


def _field_alias(field) -> str:
    return getattr(field, "alias", None) or getattr(field.field_info, "alias", None) or field.name


def _body_input_field(route: APIRoute) -> tuple[Any, Field] | None:
    body_field = getattr(route, "body_field", None)
    if body_field is None:
        return None
    field_info = getattr(body_field, "field_info", None)
    annotation = getattr(field_info, "annotation", None) or getattr(body_field, "type_", None)
    if annotation is None:
        return None
    is_required = getattr(field_info, "is_required", None)
    default = ... if callable(is_required) and is_required() else getattr(field_info, "default", None)
    return annotation, Field(default=default)


def _input_model(name: str, route: APIRoute) -> tuple[type[_ToolInput], tuple[ToolParameter, ...]]:
    # The route remains the single source of truth for aliases, defaults and validation.
    fields: dict[str, tuple[Any, Any]] = {}
    parameters: list[ToolParameter] = []
    for field in [*route.dependant.path_params, *route.dependant.query_params]:
        info = copy(field.field_info)
        fields[field.name] = (info.annotation, info)
        parameters.append(
            ToolParameter(
                name=field.name,
                alias=_field_alias(field),
                in_path=field in route.dependant.path_params,
            )
        )
    body_field = _body_input_field(route)
    if body_field is not None:
        if "body" in fields:
            raise RuntimeError(f"AI 工具 {name} 保留了 body 参数名")
        fields["body"] = body_field
    return (
        create_model(f"{name.title().replace('_', '')}Input", __base__=_ToolInput, **fields),
        tuple(parameters),
    )


def _route_method(route: APIRoute, *, system_management: bool) -> str | None:
    allowed_methods = _SYSTEM_MANAGEMENT_METHODS if system_management else _READ_ONLY_METHODS
    matching_methods = sorted(set(route.methods or ()) & allowed_methods)
    return matching_methods[0] if len(matching_methods) == 1 else None


def build_tool_registry(app: FastAPI, *, current_user: User | None = None) -> dict[str, AIToolDefinition]:
    registry: dict[str, AIToolDefinition] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        meta = route.openapi_extra if isinstance(route.openapi_extra, dict) else {}
        # Explicit metadata is the safety boundary; route paths never imply system-management access.
        if meta.get("ai_exposed") is not True:
            continue
        system_management = meta.get("ai_system_management") is True
        method = _route_method(route, system_management=system_management)
        if method is None:
            continue
        if system_management and (current_user is None or not is_super_admin(current_user)):
            continue
        name = str(meta.get("ai_name") or route.name or route.path)
        if name in registry:
            raise RuntimeError(f"duplicate AI tool name: {name}")
        model, parameters = _input_model(name, route)
        registry[name] = AIToolDefinition(
            name=name,
            description=str(meta.get("ai_description") or route.summary or route.name or route.path),
            route_path=route.path,
            input_model=model,
            parameters=parameters,
            method=method,
            system_management=system_management,
        )
    return registry


def tool_definitions(registry: dict[str, AIToolDefinition], provider: str) -> list[dict[str, Any]]:
    if provider == "claude":
        return [
            {"name": item.name, "description": item.description, "input_schema": item.input_model.model_json_schema()}
            for item in registry.values()
        ]
    return [
        {
            "type": "function",
            "function": {
                "name": item.name,
                "description": item.description,
                "parameters": item.input_model.model_json_schema(),
            },
        }
        for item in registry.values()
    ]


def _request_parts(definition: AIToolDefinition, payload: _ToolInput) -> tuple[str, dict[str, Any], object | None]:
    raw = payload.model_dump(mode="json", exclude_none=True, exclude_computed_fields=True)
    aliased = payload.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
        exclude_computed_fields=True,
    )
    raw.pop("body", None)
    body = aliased.pop("body", None)
    path = definition.route_path
    query: dict[str, Any] = {}
    for parameter in definition.parameters:
        if parameter.in_path:
            path = path.replace(f"{{{parameter.name}}}", str(raw[parameter.name]))
        elif parameter.alias in aliased:
            query[parameter.alias] = aliased[parameter.alias]
    return path, query, body


def _unwrap(body: object) -> object:
    # Give providers one compact list envelope while preserving DiskPulse pagination fields.
    if not isinstance(body, dict):
        return body
    if "content" in body:
        return {"items": body.get("content") or [], **{key: value for key, value in body.items() if key != "content"}}
    if "data" in body and "meta" in body:
        data = body.get("data")
        return {"items": data, **(body.get("meta") or {})} if isinstance(data, list) else data
    return body.get("data", body)


async def _execute(
    *,
    app: FastAPI,
    definition: AIToolDefinition,
    payload: _ToolInput,
    user_id: int | None,
) -> dict[str, Any]:
    path, query, body = _request_parts(definition, payload)
    headers = {"Authorization": f"Bearer {issue_token(user_id)}"} if user_id is not None else {}
    # In-process ASGI avoids network trust changes; the token preserves normal API authorization.
    with ai_tool_actor_context():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://diskpulse-ai.internal",
        ) as client:
            request_kwargs: dict[str, Any] = {"params": query, "headers": headers}
            if body is not None:
                request_kwargs["json"] = body
            response = await client.request(definition.method, path, **request_kwargs)
    if response.status_code == 204:
        return {"ok": True, "data": None}
    try:
        body = response.json()
    except ValueError:
        return {"ok": False, "error": "工具返回了非 JSON 响应"}
    if response.status_code >= 400:
        message = body.get("detail") if isinstance(body, dict) else None
        return {"ok": False, "error": str(message or f"工具请求失败 ({response.status_code})")}
    return {"ok": True, "data": _unwrap(body)}


def execute_tool(
    *,
    app: FastAPI,
    registry: dict[str, AIToolDefinition],
    tool_name: str,
    arguments: dict[str, Any],
    user_id: int | None = None,
    current_user: User | None = None,
) -> dict[str, Any]:
    definition = registry.get(tool_name)
    if definition is None:
        return {"ok": False, "error": f"工具 {tool_name} 未获授权"}
    if definition.system_management and (current_user is None or not is_super_admin(current_user)):
        return {"ok": False, "error": "系统管理工具仅限超级管理员"}
    try:
        payload = definition.input_model.model_validate(arguments)
    except ValidationError as error:
        return {"ok": False, "error": "工具参数无效", "details": error.errors()}
    try:
        effective_user_id = current_user.id if current_user is not None else user_id
        return asyncio.run(_execute(app=app, definition=definition, payload=payload, user_id=effective_user_id))
    except Exception:
        return {"ok": False, "error": "工具执行失败"}
