# -*- coding: utf-8 -*-
from datetime import UTC, datetime

import redis
from fastapi import HTTPException, status

from appConfig import base_config


def _redis_client():
    return redis.Redis(
        host=base_config.get("redis.host", "localhost"),
        port=base_config.get("redis.port", 6379),
        db=7,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def enforce_ai_rate_limit(user_id: int, *, client=None) -> None:
    limit = int(base_config.get("ai.chat_rate_limit_per_minute", 10))
    # UTC minute keys implement a shared fixed window without per-process state.
    window = datetime.now(UTC).strftime("%Y%m%d%H%M")
    key = f"diskpulse:ai:rate:{user_id}:{window}"
    redis_client = client or _redis_client()
    try:
        count = int(redis_client.incr(key))
        if count == 1:
            redis_client.expire(key, 60)
        if count > limit:
            retry_after = redis_client.ttl(key)
            retry_after = retry_after if isinstance(retry_after, int) and retry_after > 0 else 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI 请求过于频繁，请稍后重试",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except redis.RedisError as error:
        # Fail closed: chatting must not silently bypass the shared abuse control.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 限流服务暂不可用",
        ) from error
