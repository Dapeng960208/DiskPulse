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


class AIClientToolArgumentsError(AIClientError):
    """A provider emitted a tool call whose arguments cannot be safely executed."""

    def __init__(self, *, tool_id: str, tool_name: str, reason: str):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.reason = reason
        message = "AI 工具参数不是有效 JSON" if reason == "invalid_json" else "AI 工具参数必须是对象"
        super().__init__(message)


@dataclass(frozen=True)
class AIClientToolCall:
    tool_id: str
    name: str
    arguments: dict[str, Any]
    reasoning_content: str = ""


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
        "deepseek": "https://api.deepseek.com",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "moonshot": "https://api.moonshot.cn/v1",
        "minimax": "https://api.minimaxi.com/v1",
        "qianfan": "https://qianfan.baidubce.com/v2",
        "hunyuan": "https://tokenhub.tencentmaas.com/v1",
    }.get(config.provider, "")


def _ollama_root(config: AIConfig) -> str:
    base = _base_url(config).rstrip("/")
    return base[:-3] if base.lower().endswith("/v1") else base


def _timeout() -> int:
    return int(base_config.get("ai.request_timeout_seconds", 60))


def _decode_arguments(
    raw: object,
    *,
    tool_id: str = "",
    tool_name: str = "",
) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as error:
            raise AIClientToolArgumentsError(
                tool_id=tool_id,
                tool_name=tool_name,
                reason="invalid_json",
            ) from error
        if isinstance(parsed, dict):
            return parsed
    raise AIClientToolArgumentsError(
        tool_id=tool_id,
        tool_name=tool_name,
        reason="non_object",
    )


def _headers(config: AIConfig) -> dict[str, str]:
    key = decrypt_secret(config.api_key_encrypted)
    headers = {"Content-Type": "application/json"}
    if provider_protocol(config) == "claude":
        headers["anthropic-version"] = "2023-06-01"
        if key:
            headers["x-api-key"] = key
    elif key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def provider_protocol(config: AIConfig) -> str:
    if config.provider == "claude":
        return "claude"
    if (
        config.provider == "minimax"
        and (config.base_url or "").strip().rstrip("/").lower().endswith("/anthropic")
    ):
        return "claude"
    if config.provider == "ollama":
        return "ollama"
    if config.provider == "claude_code":
        return "claude_code"
    return "openai"


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


def _provider_payload(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    stream: bool,
    reasoning: str = "auto",
) -> dict[str, Any]:
    if provider_protocol(config) == "claude" or config.provider == "claude_code":
        payload = _claude_payload(config, messages, tools, stream=stream)
    elif config.provider == "ollama":
        payload = {
            "model": config.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": float(config.temperature),
                "num_predict": config.max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools
    else:
        payload = _openai_payload(config, messages, tools, stream=stream)

    if reasoning == "auto":
        return payload
    if config.provider == "zhipu":
        if reasoning in {"on", "off"}:
            payload["thinking"] = {
                "type": "enabled" if reasoning == "on" else "disabled"
            }
        else:
            payload["reasoning_effort"] = reasoning
    elif config.provider == "moonshot":
        if reasoning in {"on", "off"}:
            payload["thinking"] = {
                "type": "enabled" if reasoning == "on" else "disabled"
            }
        else:
            payload["reasoning_effort"] = reasoning
    elif config.provider == "hunyuan":
        model_name = config.model.strip().lower()
        if model_name.startswith("qwen3.5-"):
            payload["enable_thinking"] = reasoning == "on"
        elif model_name.startswith("minimax-m3"):
            payload["thinking"] = {
                "type": "adaptive" if reasoning == "on" else "disabled"
            }
        elif reasoning in {"on", "off"}:
            payload["thinking"] = {
                "type": "enabled" if reasoning == "on" else "disabled"
            }
        else:
            payload["reasoning_effort"] = reasoning
    elif config.provider == "openai":
        payload["reasoning_effort"] = reasoning
    elif config.provider == "openrouter":
        payload["reasoning"] = {"effort": reasoning}
    elif config.provider == "ollama":
        payload["think"] = reasoning if reasoning not in {"on", "off"} else reasoning == "on"
    elif config.provider in {"claude", "claude_code"}:
        payload["output_config"] = {"effort": reasoning}
        payload["thinking"] = {"type": "adaptive"}
        payload.pop("temperature", None)
    elif config.provider == "deepseek":
        if reasoning in {"on", "off"}:
            payload["thinking"] = {"type": "enabled" if reasoning == "on" else "disabled"}
        else:
            payload["reasoning_effort"] = reasoning
        payload.pop("temperature", None)
    elif config.provider == "dashscope":
        payload["enable_thinking"] = reasoning == "on"
    elif config.provider == "qianfan":
        model_name = config.model.strip().lower()
        if model_name.startswith("qwen3"):
            payload["enable_thinking"] = reasoning == "on"
        elif reasoning in {"on", "off"}:
            payload["thinking"] = {
                "type": "enabled" if reasoning == "on" else "disabled"
            }
        else:
            payload["reasoning_effort"] = reasoning
    elif config.provider == "volcengine":
        payload["thinking"] = {"type": "enabled" if reasoning == "on" else "disabled"}
    return payload


def reasoning_wire_value(config: AIConfig, reasoning: str) -> object | None:
    if reasoning == "auto":
        return None
    payload = _provider_payload(
        config,
        [],
        [],
        stream=False,
        reasoning=reasoning,
    )
    for key in (
        "reasoning",
        "reasoning_effort",
        "think",
        "output_config",
        "thinking",
        "enable_thinking",
    ):
        if key in payload:
            return payload[key]
    return None


def _raise_provider_error(error: httpx.HTTPError) -> None:
    if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
        raise AIClientError(f"AI 服务返回 HTTP {error.response.status_code}") from error
    if isinstance(error, httpx.TimeoutException):
        raise AIClientError("AI 服务请求超时") from error
    raise AIClientError("AI 服务请求失败") from error


def list_provider_models(config: AIConfig) -> list[str]:
    """Return a bounded, provider-normalized list without exposing upstream metadata."""
    if config.provider == "claude_code":
        raise AIClientError("Claude Code 不支持自动获取模型列表")

    base = _base_url(config)
    if not base:
        raise AIClientError("AI base_url 未配置")
    if provider_protocol(config) == "claude":
        url = f"{base.rstrip('/')}/v1/models"
        field = "data"
    elif config.provider == "ollama":
        url = f"{_ollama_root(config).rstrip('/')}/api/tags"
        field = "models"
    else:
        url = f"{base.rstrip('/')}/models"
        field = "data"

    try:
        response = httpx.get(url, headers=_headers(config), timeout=min(_timeout(), 10))
        response.raise_for_status()
        rows = response.json().get(field)
    except httpx.HTTPError as error:
        _raise_provider_error(error)
    except (AttributeError, ValueError, json.JSONDecodeError) as error:
        raise AIClientError("模型列表响应无效") from error

    if not isinstance(rows, list):
        raise AIClientError("模型列表响应无效")
    model_ids: list[str] = []
    for item in rows:
        raw_id = item.get("id") or item.get("name") if isinstance(item, dict) else item
        if not isinstance(raw_id, str):
            continue
        model_id = raw_id.strip()
        if not model_id or len(model_id) > 200 or model_id in model_ids:
            continue
        model_ids.append(model_id)
        if len(model_ids) == 200:
            break
    if not model_ids:
        raise AIClientError("未获取到可用模型")
    return model_ids


def chat_completion(
    config: AIConfig,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    reasoning: str = "auto",
) -> AICompletionResult:
    base = _base_url(config)
    if not base:
        raise AIClientError("AI base_url 未配置")
    tool_defs = tools or []
    try:
        if config.provider == "ollama":
            response = httpx.post(
                f"{_ollama_root(config)}/api/chat",
                json=_provider_payload(
                    config,
                    messages,
                    tool_defs,
                    stream=False,
                    reasoning=reasoning,
                ),
                headers=_headers(config),
                timeout=_timeout(),
            )
            response.raise_for_status()
            message = response.json()["message"]
            text_parts = [str(message.get("content") or "")]
            calls = [
                AIClientToolCall(
                    tool_id=str(item.get("id") or f"tool_{index}"),
                    name=str(item.get("function", {}).get("name") or ""),
                    arguments=_decode_arguments(
                        (item.get("function") or {}).get("arguments", {}),
                        tool_id=str(item.get("id") or f"tool_{index}"),
                        tool_name=str(item.get("function", {}).get("name") or ""),
                    ),
                )
                for index, item in enumerate(message.get("tool_calls") or [])
            ]
        elif provider_protocol(config) == "claude":
            response = httpx.post(
                f"{base}/v1/messages",
                json=_provider_payload(
                    config,
                    messages,
                    tool_defs,
                    stream=False,
                    reasoning=reasoning,
                ),
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
                    arguments=_decode_arguments(
                        block.get("input", {}),
                        tool_id=str(block.get("id") or ""),
                        tool_name=str(block.get("name") or ""),
                    ),
                )
                for block in blocks
                if block.get("type") == "tool_use"
            ]
        else:
            response = httpx.post(
                f"{base}/chat/completions",
                json=_provider_payload(
                    config,
                    messages,
                    tool_defs,
                    stream=False,
                    reasoning=reasoning,
                ),
                headers=_headers(config),
                timeout=_timeout(),
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            text_parts = [str(message.get("content") or "")]
            reasoning_content = str(message.get("reasoning_content") or "")
            calls = [
                AIClientToolCall(
                    tool_id=str(item.get("id") or ""),
                    name=str(item.get("function", {}).get("name") or ""),
                    arguments=_decode_arguments(
                        (item.get("function") or {}).get("arguments", "{}"),
                        tool_id=str(item.get("id") or ""),
                        tool_name=str(item.get("function", {}).get("name") or ""),
                    ),
                    reasoning_content=reasoning_content,
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
    *,
    reasoning: str = "auto",
) -> Iterator[AICompletionStreamEvent]:
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    # OpenAI-compatible providers split and interleave tool fields; index is the stable join key.
    calls: dict[int, dict[str, Any]] = {}
    with httpx.stream(
        "POST",
        f"{_base_url(config)}/chat/completions",
        json=_provider_payload(
            config,
            messages,
            tools,
            stream=True,
            reasoning=reasoning,
        ),
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
            choices = data.get("choices", [{}])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                text = str(content)
                text_parts.append(text)
                yield AICompletionStreamEvent(kind="delta", text=text)
            reasoning_content = delta.get("reasoning_content")
            if reasoning_content:
                reasoning_parts.append(str(reasoning_content))
            for item in delta.get("tool_calls") or []:
                index = int(item.get("index", 0))
                current = calls.setdefault(index, {"id": "", "name": "", "arguments": "", "has_arguments": False})
                current["id"] = str(item.get("id") or current["id"])
                function = item.get("function") or {}
                current["name"] += str(function.get("name") or "")
                if "arguments" in function:
                    current["arguments"] += str(function["arguments"])
                    current["has_arguments"] = True
    tool_calls = [
        AIClientToolCall(
            tool_id=value["id"] or f"tool_{index}",
            name=value["name"],
            arguments=_decode_arguments(
                value["arguments"] if value["has_arguments"] else "{}",
                tool_id=value["id"] or f"tool_{index}",
                tool_name=value["name"],
            ),
            reasoning_content="".join(reasoning_parts),
        )
        for index, value in sorted(calls.items())
    ]
    yield AICompletionStreamEvent(
        kind="completed",
        text="".join(text_parts).strip(),
        tool_calls=tool_calls,
        stop_reason="tool_calls" if tool_calls else "final",
    )


def _ollama_stream(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    reasoning: str = "auto",
) -> Iterator[AICompletionStreamEvent]:
    text_parts: list[str] = []
    calls: list[AIClientToolCall] = []
    with httpx.stream(
        "POST",
        f"{_ollama_root(config)}/api/chat",
        json=_provider_payload(
            config,
            messages,
            tools,
            stream=True,
            reasoning=reasoning,
        ),
        headers=_headers(config),
        timeout=_timeout(),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.strip():
                continue
            data = json.loads(line)
            message = data.get("message") or {}
            content = str(message.get("content") or "")
            if content:
                text_parts.append(content)
                yield AICompletionStreamEvent(kind="delta", text=content)
            for index, item in enumerate(message.get("tool_calls") or []):
                function = item.get("function") or {}
                calls.append(
                    AIClientToolCall(
                        tool_id=str(item.get("id") or f"tool_{len(calls) + index}"),
                        name=str(function.get("name") or ""),
                        arguments=_decode_arguments(
                            function.get("arguments", {}),
                            tool_id=str(item.get("id") or f"tool_{len(calls) + index}"),
                            tool_name=str(function.get("name") or ""),
                        ),
                    )
                )
            if data.get("done") is True:
                break
    yield AICompletionStreamEvent(
        kind="completed",
        text="".join(text_parts).strip(),
        tool_calls=calls,
        stop_reason="tool_calls" if calls else "final",
    )


def _claude_stream(
    config: AIConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    reasoning: str = "auto",
) -> Iterator[AICompletionStreamEvent]:
    text_parts: list[str] = []
    calls: dict[int, dict[str, Any]] = {}
    with httpx.stream(
        "POST",
        f"{_base_url(config)}/v1/messages",
        json=_provider_payload(
            config,
            messages,
            tools,
            stream=True,
            reasoning=reasoning,
        ),
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
                    has_initial_input = "input" in block
                    initial_input = block.get("input")
                    # Empty input must stay empty or later input_json_delta fragments would follow "{}".
                    has_arguments = has_initial_input and initial_input != {}
                    calls[int(data.get("index", 0))] = {
                        "id": str(block.get("id") or ""),
                        "name": str(block.get("name") or ""),
                        "arguments": json.dumps(initial_input) if has_arguments else "",
                        "has_arguments": has_arguments,
                    }
            elif event_type == "content_block_delta":
                delta = data.get("delta") or {}
                if delta.get("type") == "text_delta":
                    text = str(delta.get("text") or "")
                    text_parts.append(text)
                    yield AICompletionStreamEvent(kind="delta", text=text)
                elif delta.get("type") == "input_json_delta":
                    current = calls.setdefault(
                        int(data.get("index", 0)),
                        {"id": "", "name": "", "arguments": "", "has_arguments": False},
                    )
                    if "partial_json" in delta:
                        current["arguments"] += str(delta["partial_json"])
                        current["has_arguments"] = True
            elif event_type == "message_stop":
                break
    tool_calls = [
        AIClientToolCall(
            tool_id=value["id"] or f"tool_{index}",
            name=value["name"],
            arguments=_decode_arguments(
                value["arguments"] if value["has_arguments"] else "{}",
                tool_id=value["id"] or f"tool_{index}",
                tool_name=value["name"],
            ),
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
    reasoning: str = "auto",
    app: Any = None,
    registry: dict[str, Any] | None = None,
    current_user: Any = None,
    user_id: int | None = None,
    tool_handler: Any = None,
    on_tool_result: Any = None,
) -> Iterator[AICompletionStreamEvent]:
    if config.provider != "claude_code" and not _base_url(config):
        raise AIClientError("AI base_url 未配置")
    try:
        # Normalize provider-specific streams before the chat orchestration layer sees them.
        if config.provider == "claude_code":
            from services.claude_code_adapter import claude_code_completion_stream

            yield from claude_code_completion_stream(
                config,
                messages,
                app=app,
                registry=registry or {},
                current_user=current_user,
                user_id=user_id,
                reasoning=reasoning,
                tool_handler=tool_handler,
                on_tool_result=on_tool_result,
            )
        elif provider_protocol(config) == "claude":
            yield from _claude_stream(
                config,
                messages,
                tools or [],
                reasoning=reasoning,
            )
        elif config.provider == "ollama":
            yield from _ollama_stream(
                config,
                messages,
                tools or [],
                reasoning=reasoning,
            )
        else:
            yield from _openai_stream(
                config,
                messages,
                tools or [],
                reasoning=reasoning,
            )
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, httpx.HTTPError):
            _raise_provider_error(error)
        raise AIClientError("AI 流式响应格式无效") from error
