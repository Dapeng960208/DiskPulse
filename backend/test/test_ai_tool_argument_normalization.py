# -*- coding: utf-8 -*-
from fastapi import APIRouter, FastAPI

from services.ai_tool_service import build_tool_registry, execute_tool


def _usage_tool():
    app = FastAPI()
    router = APIRouter()

    @router.get(
        "/storage-usages",
        openapi_extra={"ai_exposed": True, "ai_name": "list_storage_usages"},
    )
    def list_storage_usages(
        page: int = 1,
        size: int = 20,
        use_ratio_min: float | None = None,
        use_ratio_max: float | None = None,
    ):
        return {
            "page": page,
            "size": size,
            "use_ratio_min": use_ratio_min,
            "use_ratio_max": use_ratio_max,
        }

    app.include_router(router)
    return app, build_tool_registry(app)


def test_tool_accepts_provider_style_utilization_argument_names():
    app, registry = _usage_tool()

    result = execute_tool(
        app=app,
        registry=registry,
        tool_name="list_storage_usages",
        arguments={
            "page": 1,
            "size": 100,
            "use ratio min": 70,
            "use_max": 90,
        },
    )

    assert result == {
        "ok": True,
        "data": {
            "page": 1,
            "size": 100,
            "use_ratio_min": 70,
            "use_ratio_max": 90,
        },
    }


def test_tool_ignores_unknown_null_placeholders_but_rejects_unknown_values():
    app, registry = _usage_tool()

    placeholder_result = execute_tool(
        app=app,
        registry=registry,
        tool_name="list_storage_usages",
        arguments={
            "page": 1,
            "size": 100,
            "use ratio min": None,
            "use_max": None,
        },
    )
    unexpected_value_result = execute_tool(
        app=app,
        registry=registry,
        tool_name="list_storage_usages",
        arguments={"unexpected_filter": "value"},
    )

    assert placeholder_result == {
        "ok": True,
        "data": {
            "page": 1,
            "size": 100,
            "use_ratio_min": None,
            "use_ratio_max": None,
        },
    }
    assert unexpected_value_result["error"] == "工具参数无效"
