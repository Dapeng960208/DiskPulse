# -*- coding: utf-8 -*-
from dataclasses import dataclass
import json
from typing import Any, Iterator

import httpx

from appConfig import base_config
from models import AIConfig
from services.ai_security import decrypt_secret


class AIClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIClientToolCall:
    tool_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AICompletionResult:
    text: str
    tool_calls: list[AIClientToolCall]
    stop_reason: str


@dataclass(frozen=True)
class AICompletionStreamEvent:
    kind: str
    text: str = ""
    tool_calls: list[AIClientToolCall] | None = None
    stop_reason: str = ""


def _base_url(config: AIConfig) -> str:
    base = (config.base_url or "").strip().rstrip("/")
    if base:
        lowered = base.lower()
        if config.provider == "openrouter" and not lowered.endswith(("/v1", "/api/v1")):
            return f"{base}/api/v1"
        if config.provider in {"openai", "ollama"} and not lowered.endswith(("/v1", "/api/v1")):
            return f"{base}/v1"
        return base
    return {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "ollama": "http://localhost:11434/v1",
        "claude": "https://api.anthropic.com",
    }.get(config.provider, "")


def _timeout() -> int:
    return int(base_config.get("ai.request_timeout_seconds", 60))


def _decode_arguments(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError as error:
            raise AIClientError("AI 工具参数不是有效 JSON") from error
        if isinstance(parsed, dict):
            return parsed
    raise AIClientError("AI 工具参数必须是对象")


def _headers(config: AIConfig) -> dict[str, str]:
    key = decrypt_secret(config.api_key_encrypted)
    headers = {"Content-Type": "application/json"}
    if config.provider == "claude":
        headers["anthropic-version"] = "2023-06-01"
        if key:
            headers["x-api-key"] = key
    elif key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _openai_payload(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    stream: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": float(config.temperature),
        "max_tokens": config.max_tokens,
        "stream": stream,
    }
    if tools:
        payload.update({"tools": tools, "tool_choice": "auto"})
    return payload


def _claude_payload(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    stream: bool,
) -> dict[str, Any]:
    system = [str(item["content"]) for item in messages if item.get("role") == "system"]
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [item for item in messages if item.get("role") != "system"],
        "temperature": float(config.temperature),
        "max_tokens": config.max_tokens,
        "stream": stream,
    }
    if system:
        payload["system"] = "\n\n".join(system)
    if tools:
        payload["tools"] = tools
    return payload


def _raise_provider_error(error: httpx.HTTPError) -> None:
    if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
        raise AIClientError(f"AI 服务返回 HTTP {error.response.status_code}") from error
    if isinstance(error, httpx.TimeoutException):
        raise AIClientError("AI 服务请求超时") from error
    raise AIClientError("AI 服务请求失败") from error


def chat_completion(
    config: AIConfig,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
) -> AICompletionResult:
    base = _base_url(config)
    if not base:
        raise AIClientError("AI base_url 未配置")
    tool_defs = tools or []
    try:
        if config.provider == "claude":
            response = httpx.post(
                f"{base}/v1/messages",
                json=_claude_payload(config, messages, tool_defs, stream=False),
                headers=_headers(config),
                timeout=_timeout(),
            )
            response.raise_for_status()
            blocks = response.json().get("content", [])
            text_parts = [str(block.get("text", "")) for block in blocks if block.get("type") == "text"]
            calls = [
                AIClientToolCall(
                    tool_id=str(block.get("id") or ""),
                    name=str(block.get("name") or ""),
                    arguments=_decode_arguments(block.get("input") or {}),
                )
                for block in blocks
                if block.get("type") == "tool_use"
            ]
        else:
            response = httpx.post(
                f"{base}/chat/completions",
                json=_openai_payload(config, messages, tool_defs, stream=False),
                headers=_headers(config),
                timeout=_timeout(),
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            text_parts = [str(message.get("content") or "")]
            calls = [
                AIClientToolCall(
                    tool_id=str(item.get("id") or ""),
                    name=str(item.get("function", {}).get("name") or ""),
                    arguments=_decode_arguments(item.get("function", {}).get("arguments") or "{}"),
                )
                for item in message.get("tool_calls") or []
            ]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        if isinstance(error, httpx.HTTPError):
            _raise_provider_error(error)
        raise AIClientError("AI 服务响应格式无效") from error
    text = "".join(text_parts).strip()
    if not text and not calls:
        raise AIClientError("AI 服务返回空内容")
    return AICompletionResult(text=text, tool_calls=calls, stop_reason="tool_calls" if calls else "final")


def _openai_stream(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> Iterator[AICompletionStreamEvent]:
    text_parts: list[str] = []
    calls: dict[int, dict[str, str]] = {}
    with httpx.stream(
        "POST",
        f"{_base_url(config)}/chat/completions",
        json=_openai_payload(config, messages, tools, stream=True),
        headers=_headers(config),
        timeout=_timeout(),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            data = json.loads(raw)
            delta = data.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                text = str(content)
                text_parts.append(text)
                yield AICompletionStreamEvent(kind="delta", text=text)
            for item in delta.get("tool_calls") or []:
                index = int(item.get("index", 0))
                current = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                current["id"] = str(item.get("id") or current["id"])
                function = item.get("function") or {}
                current["name"] += str(function.get("name") or "")
                current["arguments"] += str(function.get("arguments") or "")
    tool_calls = [
        AIClientToolCall(
            tool_id=value["id"] or f"tool_{index}",
            name=value["name"],
            arguments=_decode_arguments(value["arguments"] or "{}"),
        )
        for index, value in sorted(calls.items())
    ]
    yield AICompletionStreamEvent(
        kind="completed",
        text="".join(text_parts).strip(),
        tool_calls=tool_calls,
        stop_reason="tool_calls" if tool_calls else "final",
    )


def _claude_stream(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> Iterator[AICompletionStreamEvent]:
    text_parts: list[str] = []
    calls: dict[int, dict[str, str]] = {}
    with httpx.stream(
        "POST",
        f"{_base_url(config)}/v1/messages",
        json=_claude_payload(config, messages, tools, stream=True),
        headers=_headers(config),
        timeout=_timeout(),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data:"):
                continue
            data = json.loads(line[5:].strip())
            event_type = data.get("type")
            if event_type == "content_block_start":
                block = data.get("content_block") or {}
                if block.get("type") == "tool_use":
                    initial_input = block.get("input")
                    calls[int(data.get("index", 0))] = {
                        "id": str(block.get("id") or ""),
                        "name": str(block.get("name") or ""),
                        "arguments": json.dumps(initial_input) if initial_input else "",
                    }
            elif event_type == "content_block_delta":
                delta = data.get("delta") or {}
                if delta.get("type") == "text_delta":
                    text = str(delta.get("text") or "")
                    text_parts.append(text)
                    yield AICompletionStreamEvent(kind="delta", text=text)
                elif delta.get("type") == "input_json_delta":
                    current = calls.setdefault(int(data.get("index", 0)), {"id": "", "name": "", "arguments": ""})
                    current["arguments"] += str(delta.get("partial_json") or "")
            elif event_type == "message_stop":
                break
    tool_calls = [
        AIClientToolCall(
            tool_id=value["id"] or f"tool_{index}",
            name=value["name"],
            arguments=_decode_arguments(value["arguments"] or "{}"),
        )
        for index, value in sorted(calls.items())
    ]
    yield AICompletionStreamEvent(
        kind="completed",
        text="".join(text_parts).strip(),
        tool_calls=tool_calls,
        stop_reason="tool_calls" if tool_calls else "final",
    )


def chat_completion_stream(
    config: AIConfig,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
) -> Iterator[AICompletionStreamEvent]:
    if not _base_url(config):
        raise AIClientError("AI base_url 未配置")
    try:
        if config.provider == "claude":
            yield from _claude_stream(config, messages, tools or [])
        else:
            yield from _openai_stream(config, messages, tools or [])
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, httpx.HTTPError):
            _raise_provider_error(error)
        raise AIClientError("AI 流式响应格式无效") from error
