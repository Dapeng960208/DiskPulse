# -*- coding: utf-8 -*-
import requests
from fastapi.responses import Response


def raise_for_device_status(response, *, logger=None, context: str) -> None:
    """Raise HTTPError without replacing the device response, and log its message."""
    try:
        response.raise_for_status()
    except requests.HTTPError:
        if logger:
            message = response.text.strip() or response.reason or "<empty response>"
            log_message = (
                f"{context} device_status={response.status_code} "
                f"device_response={message}"
            )
            if hasattr(logger, "error"):
                logger.error(log_message)
            else:
                logger._log("error", log_message)
        raise


def device_error_response(error: requests.HTTPError) -> Response | None:
    """Build an HTTP response with the device status, body and content type unchanged."""
    response = error.response
    if response is None:
        return None
    headers = {}
    content_type = response.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
    )
