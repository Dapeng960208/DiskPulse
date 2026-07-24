# -*- coding: utf-8 -*-
"""Router primitives for HTTP write transaction boundaries."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from dependencies import get_write_db


_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class TransactionalAPIRouter(APIRouter):
    """Attach the request write transaction dependency to mutating routes."""

    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        methods = {method.upper() for method in kwargs.get("methods") or ()}
        if methods & _WRITE_METHODS:
            dependencies = list(kwargs.get("dependencies") or ())
            dependencies.append(Depends(get_write_db, scope="function"))
            kwargs["dependencies"] = dependencies
        super().add_api_route(path, endpoint, **kwargs)
