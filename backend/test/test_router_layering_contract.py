# -*- coding: utf-8 -*-
import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_forecast_incident_router_does_not_import_orm_models():
    router_path = BACKEND_ROOT / "routers" / "forecast_incidents.py"
    module = ast.parse(router_path.read_text(encoding="utf-8"))

    model_imports = [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.module == "models"
    ]

    assert model_imports == []
