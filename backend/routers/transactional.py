# -*- coding: utf-8 -*-
"""Router primitives for HTTP write transaction boundaries."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from dependencies import get_write_db


_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_SKIP_WRITE_TRANSACTION_ATTRIBUTE = "__skip_router_write_transaction__"


def skip_write_transaction(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a streaming endpoint that owns short persistence checkpoints itself."""
    setattr(endpoint, _SKIP_WRITE_TRANSACTION_ATTRIBUTE, True)
    return endpoint


class TransactionalAPIRouter(APIRouter):
    """Attach the request write transaction dependency to mutating routes."""

    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        methods = {method.upper() for method in kwargs.get("methods") or ()}
        if methods & _WRITE_METHODS and not getattr(endpoint, _SKIP_WRITE_TRANSACTION_ATTRIBUTE, False):
            dependencies = list(kwargs.get("dependencies") or ())
            dependencies.append(Depends(get_write_db, scope="function"))
            kwargs["dependencies"] = dependencies
        super().add_api_route(path, endpoint, **kwargs)
