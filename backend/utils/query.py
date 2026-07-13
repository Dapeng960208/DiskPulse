# -*- coding: utf-8 -*-
from fastapi import HTTPException, status


def get_sort_column(model, prop: str | None):
    if not prop:
        return None
    if prop.startswith("_") or not hasattr(model, prop):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort property: {prop}")
    column = getattr(model, prop)
    if not hasattr(column, "asc") or not hasattr(column, "desc"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort property: {prop}")
    return column


def require_allowed(value: str, allowed: set[str], field_name: str) -> str:
    if value not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name}: {value}")
    return value
