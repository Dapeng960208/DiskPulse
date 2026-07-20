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


def apply_numeric_range(query, column, minimum: float | None, maximum: float | None):
    if minimum is not None:
        query = query.where(column >= minimum)
    if maximum is not None:
        query = query.where(column <= maximum)
    return query


def apply_use_ratio_range(query, model, use_ratio_min: float | None, use_ratio_max: float | None):
    return apply_numeric_range(query, model.use_ratio, use_ratio_min, use_ratio_max)


def filter_tree_by_use_ratio(
    nodes: list[dict],
    use_ratio_min: float | None,
    use_ratio_max: float | None,
) -> list[dict]:
    if use_ratio_min is None and use_ratio_max is None:
        return nodes

    filtered_nodes = []
    for node in nodes:
        children = filter_tree_by_use_ratio(
            node.get("children", []),
            use_ratio_min,
            use_ratio_max,
        )
        used_ratio = node.get("used_ratio")
        matches = used_ratio is not None
        if use_ratio_min is not None:
            matches = matches and used_ratio >= use_ratio_min
        if use_ratio_max is not None:
            matches = matches and used_ratio <= use_ratio_max
        if matches or children:
            filtered_node = node.copy()
            if "children" in node:
                filtered_node["children"] = children
            filtered_nodes.append(filtered_node)
    return filtered_nodes
