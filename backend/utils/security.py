# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from appConfig import base_config


def _config_value(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value is not None:
        return value
    configured = base_config.get(key, default)
    return str(configured) if configured is not None else default


def _config_int(key: str, default: int) -> int:
    try:
        return int(_config_value(key, str(default)))
    except (TypeError, ValueError):
        return default


def _jwt_secret_key() -> str:
    secret = _config_value("JWT_SECRET_KEY").strip()
    if len(secret) < 8 or secret.lower().startswith(("replace-with", "change-me", "changeme")):
        raise RuntimeError("JWT_SECRET_KEY must be configured with a non-placeholder value")
    return secret


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _token_signature(message: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64encode(digest)


def issue_token(user_id: int, token_type: str = "access") -> str:
    now = datetime.now(UTC)
    ttl_minutes = _config_int("JWT_ACCESS_TTL_MINUTES", 60)
    payload = {
        "sub": user_id,
        "type": token_type,
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
        "iat": int(now.timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    return f"{encoded_header}.{encoded_payload}.{_token_signature(message, _jwt_secret_key())}"


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from error

    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _token_signature(message, _jwt_secret_key())
    if not hmac.compare_digest(encoded_signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token signature")

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token payload") from error

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token type")
    if int(payload.get("exp", 0)) <= int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")
    return payload


def parse_authorization_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    if " " not in authorization:
        return authorization
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authorization header")
