# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis
from fastapi import HTTPException, status

from appConfig import base_config


DEFAULT_ACCESS_TTL_MINUTES = 7 * 24 * 60
TOKEN_CACHE_PREFIX = "diskpulse:auth:token"


def _redis_client():
    return redis.Redis(
        host=base_config.get("redis.host", "localhost"),
        port=base_config.get("redis.port", 6379),
        db=7,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )


def _access_ttl_seconds() -> int:
    ttl_minutes = int(base_config.get("jwt.access_ttl_minutes", DEFAULT_ACCESS_TTL_MINUTES))
    if ttl_minutes <= 0:
        raise RuntimeError("jwt.access_ttl_minutes must be greater than zero")
    return ttl_minutes * 60


def _token_cache_key(payload: dict[str, Any]) -> str:
    token_id = str(payload.get("jti") or "")
    if not token_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token id")
    return f"{TOKEN_CACHE_PREFIX}:{token_id}"


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cache_token(token: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    try:
        _redis_client().set(
            _token_cache_key(payload),
            _token_digest(token),
            ex=ttl_seconds,
        )
    except redis.RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication session service unavailable",
        ) from error


def _require_cached_token(token: str, payload: dict[str, Any]) -> None:
    try:
        cached_digest = _redis_client().get(_token_cache_key(payload))
    except redis.RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication session service unavailable",
        ) from error
    if not cached_digest or not hmac.compare_digest(str(cached_digest), _token_digest(token)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token session expired")


def _delete_cached_token(payload: dict[str, Any]) -> None:
    try:
        _redis_client().delete(_token_cache_key(payload))
    except redis.RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication session service unavailable",
        ) from error


def _jwt_secret_key() -> str:
    secret = str(base_config.get("jwt.secret_key", "")).strip()
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
    ttl_seconds = _access_ttl_seconds()
    payload = {
        "sub": user_id,
        "type": token_type,
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    token = f"{encoded_header}.{encoded_payload}.{_token_signature(message, _jwt_secret_key())}"
    _cache_token(token, payload, ttl_seconds)
    return token


def decode_token(token: str, expected_type: str = "access", *, verify_session: bool = True) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from error

    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _token_signature(message, _jwt_secret_key())
    if not hmac.compare_digest(encoded_signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token signature")

    try:
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token payload") from error

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token header")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token type")
    if int(payload.get("exp", 0)) <= int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")
    if verify_session:
        _require_cached_token(token, payload)
    return payload


def revoke_token(token: str, expected_type: str = "access") -> None:
    payload = decode_token(token, expected_type, verify_session=False)
    _delete_cached_token(payload)


def parse_authorization_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authorization header")
