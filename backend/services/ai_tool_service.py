# -*- coding: utf-8 -*-
import asyncio
from copy import copy
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, ValidationError, create_model

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


def _field_alias(field) -> str:
    return getattr(field, "alias", None) or getattr(field.field_info, "alias", None) or field.name


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
    return (
        create_model(f"{name.title().replace('_', '')}Input", __base__=_ToolInput, **fields),
        tuple(parameters),
    )


def build_tool_registry(app: FastAPI) -> dict[str, AIToolDefinition]:
    registry: dict[str, AIToolDefinition] = {}
    for route in app.routes:
        # Explicit opt-in plus GET-only is the safety boundary; naming conventions are insufficient.
        if not isinstance(route, APIRoute) or "GET" not in route.methods:
            continue
        meta = route.openapi_extra if isinstance(route.openapi_extra, dict) else {}
        if not meta.get("ai_exposed"):
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


def _request_parts(definition: AIToolDefinition, payload: _ToolInput) -> tuple[str, dict[str, Any]]:
    raw = payload.model_dump(mode="json", exclude_none=True)
    aliased = payload.model_dump(mode="json", by_alias=True, exclude_none=True)
    path = definition.route_path
    query: dict[str, Any] = {}
    for parameter in definition.parameters:
        if parameter.in_path:
            path = path.replace(f"{{{parameter.name}}}", str(raw[parameter.name]))
        elif parameter.alias in aliased:
            query[parameter.alias] = aliased[parameter.alias]
    return path, query


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
    path, query = _request_parts(definition, payload)
    headers = {"Authorization": f"Bearer {issue_token(user_id)}"} if user_id is not None else {}
    # In-process ASGI avoids network trust changes; the token preserves normal API authorization.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://diskpulse-ai.internal",
    ) as client:
        response = await client.get(path, params=query, headers=headers)
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
) -> dict[str, Any]:
    definition = registry.get(tool_name)
    if definition is None:
        return {"ok": False, "error": f"工具 {tool_name} 未获授权"}
    try:
        payload = definition.input_model.model_validate(arguments)
    except ValidationError as error:
        return {"ok": False, "error": "工具参数无效", "details": error.errors()}
    try:
        return asyncio.run(_execute(app=app, definition=definition, payload=payload, user_id=user_id))
    except Exception:
        return {"ok": False, "error": "工具执行失败"}
