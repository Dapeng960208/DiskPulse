# -*- coding: utf-8 -*-
"""Safe, cancellable Claude Agent SDK adapter for DiskPulse MCP tools."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any, Iterator

from models import AIConfig, User
from services.ai_client import AIClientError, AICompletionStreamEvent
from services.ai_security import decrypt_secret


def build_claude_code_options(
    config: AIConfig,
    *,
    tool_names: list[str],
    reasoning: str = "auto",
    mcp_server: object | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    key = decrypt_secret(config.api_key_encrypted)
    options: dict[str, Any] = {
        "model": config.model,
        # Explicitly disable Claude Code's built-in Read/Write/Edit/Bash tools.
        "tools": [],
        "mcp_servers": {
            "diskpulse": mcp_server
            if mcp_server is not None
            else {"type": "sdk", "name": "diskpulse"}
        },
        "allowed_tools": [f"mcp__diskpulse__{name}" for name in tool_names],
        "env": {"ANTHROPIC_API_KEY": key},
        "max_turns": 4,
        "strict_mcp_config": True,
        "include_partial_messages": True,
        "setting_sources": [],
        "skills": [],
    }
    if system_prompt:
        options["system_prompt"] = system_prompt
    if reasoning != "auto":
        options["effort"] = reasoning
    return options


def safe_options_for_log(options: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": options.get("model"),
        "tools": list(options.get("tools") or []),
        "mcp_servers": list((options.get("mcp_servers") or {}).keys()),
        "allowed_tools": list(options.get("allowed_tools") or []),
        "effort": options.get("effort", "auto"),
        "max_turns": options.get("max_turns"),
        "strict_mcp_config": bool(options.get("strict_mcp_config")),
        "include_partial_messages": bool(options.get("include_partial_messages")),
    }


def _prompt(messages: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"{str(item.get('role') or 'user').upper()}:\n{item.get('content', '')}"
        for item in messages
        if item.get("role") != "system"
    )


def _text_parts(message: object) -> list[str]:
    parts = []
    for block in getattr(message, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return parts


def _partial_text(message: object) -> str:
    event = getattr(message, "event", None)
    if not isinstance(event, dict) or event.get("type") != "content_block_delta":
        return ""
    delta = event.get("delta") or {}
    if delta.get("type") != "text_delta":
        return ""
    return str(delta.get("text") or "")


@dataclass
class _ToolRequest:
    tool_name: str
    arguments: dict[str, Any]
    _response: Queue

    def respond(self, result: dict[str, Any]) -> None:
        self._response.put(result)

    async def wait(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._response.get)


def _sdk_tools(
    *,
    registry: dict[str, Any],
    request_queue: Queue,
) -> list[object]:
    try:
        from claude_agent_sdk import tool
    except ImportError as error:  # pragma: no cover - deployment dependency guard
        raise AIClientError("Claude Code SDK 未安装") from error

    tools = []
    for definition in registry.values():
        async def handler(arguments, *, _name=definition.name):
            response = Queue(maxsize=1)
            request = _ToolRequest(
                tool_name=_name,
                arguments=dict(arguments or {}),
                _response=response,
            )
            request_queue.put(request)
            result = await request.wait()
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, default=str),
                    }
                ]
            }

        tools.append(
            tool(
                definition.name,
                definition.description,
                definition.input_model.model_json_schema(),
            )(handler)
        )
    return tools


class _ClientState:
    def __init__(self) -> None:
        self.cancelled = Event()
        self._lock = Lock()
        self._loop = None
        self._client = None

    def bind(self, loop, client) -> None:
        with self._lock:
            self._loop = loop
            self._client = client

    def unbind(self) -> None:
        with self._lock:
            self._loop = None
            self._client = None

    async def _cancel_client(self, client) -> None:
        try:
            await client.interrupt()
        except Exception:
            pass
        try:
            await client.disconnect()
        except Exception:
            pass

    def cancel(self) -> None:
        self.cancelled.set()
        with self._lock:
            loop = self._loop
            client = self._client
        if loop is None or client is None or loop.is_closed():
            return
        future = asyncio.run_coroutine_threadsafe(
            self._cancel_client(client),
            loop,
        )
        try:
            future.result(timeout=2)
        except Exception:
            future.cancel()


async def _run_sdk(
    config: AIConfig,
    messages: list[dict[str, Any]],
    *,
    registry: dict[str, Any],
    reasoning: str,
    output: Queue,
    state: _ClientState,
) -> None:
    try:
        from claude_agent_sdk import (
            ClaudeAgentOptions,
            ClaudeSDKClient,
            create_sdk_mcp_server,
        )
    except ImportError as error:  # pragma: no cover - deployment dependency guard
        output.put(("error", AIClientError("Claude Code SDK 未安装")))
        output.put(("done", None))
        return

    sdk_tools = _sdk_tools(registry=registry, request_queue=output)
    server = create_sdk_mcp_server(
        name="diskpulse",
        version="1.0.0",
        tools=sdk_tools,
    )
    raw_options = build_claude_code_options(
        config,
        tool_names=list(registry),
        reasoning=reasoning,
        mcp_server=server,
        system_prompt="\n\n".join(
            str(item.get("content") or "")
            for item in messages
            if item.get("role") == "system"
        )
        or None,
    )
    options = ClaudeAgentOptions(**raw_options)
    client = ClaudeSDKClient(options)
    state.bind(asyncio.get_running_loop(), client)
    partial_seen = False
    try:
        if state.cancelled.is_set():
            return
        await client.connect()
        if state.cancelled.is_set():
            return
        await client.query(_prompt(messages))
        async for message in client.receive_response():
            if state.cancelled.is_set():
                break
            partial = _partial_text(message)
            if partial:
                partial_seen = True
                output.put(("delta", partial))
            elif not partial_seen:
                for text in _text_parts(message):
                    output.put(("delta", text))
    except Exception:
        if not state.cancelled.is_set():
            output.put(("error", AIClientError("Claude Code 调用失败")))
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
        state.unbind()
        output.put(("done", None))


def _default_tool_handler(
    *,
    app: Any,
    registry: dict[str, Any],
    current_user: User | None,
    user_id: int | None,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    from services.ai_quota_confirmation_service import is_quota_write_tool
    from services.ai_tool_service import execute_tool

    if is_quota_write_tool(tool_name):
        return {
            "ok": False,
            "error": "该工具需要用户确认，当前调用未建立配额确认上下文",
        }
    return execute_tool(
        app=app,
        registry=registry,
        tool_name=tool_name,
        arguments=arguments,
        user_id=user_id,
        current_user=current_user,
    )


def claude_code_completion_stream(
    config: AIConfig,
    messages: list[dict[str, Any]],
    *,
    app: Any,
    registry: dict[str, Any],
    current_user: User | None,
    user_id: int | None,
    reasoning: str = "auto",
    tool_handler: Any = None,
    on_tool_result: Any = None,
    timeout_seconds: float = 60,
) -> Iterator[AICompletionStreamEvent]:
    output: Queue = Queue()
    state = _ClientState()
    thread = Thread(
        target=lambda: asyncio.run(
            _run_sdk(
                config,
                messages,
                registry=registry,
                reasoning=reasoning,
                output=output,
                state=state,
            )
        ),
        name="diskpulse-claude-code",
        daemon=True,
    )
    thread.start()
    text_parts: list[str] = []
    finished = False
    try:
        while True:
            try:
                # Bound every wait for SDK output so a provider that never
                # finishes cannot pin the HTTP stream and its worker forever.
                item = output.get(timeout=max(float(timeout_seconds), 0.001))
            except Empty as error:
                raise AIClientError("Claude Code 调用超时") from error
            if isinstance(item, _ToolRequest):
                try:
                    if tool_handler is None:
                        result = _default_tool_handler(
                            app=app,
                            registry=registry,
                            current_user=current_user,
                            user_id=user_id,
                            tool_name=item.tool_name,
                            arguments=item.arguments,
                        )
                    else:
                        result = tool_handler(item.tool_name, item.arguments)
                except Exception:
                    result = {"ok": False, "error": "工具执行失败"}
                if on_tool_result is not None:
                    on_tool_result(item.tool_name, item.arguments, result)
                item.respond(result)
                continue
            kind, value = item
            if kind == "delta":
                text = str(value)
                text_parts.append(text)
                yield AICompletionStreamEvent(kind="delta", text=text)
            elif kind == "error":
                raise value
            elif kind == "done":
                finished = True
                break
        text = "".join(text_parts).strip()
        if not text:
            raise AIClientError("Claude Code 返回空内容")
        yield AICompletionStreamEvent(
            kind="completed",
            text=text,
            tool_calls=[],
            stop_reason="final",
        )
    finally:
        if not finished:
            state.cancel()
        thread.join(timeout=2)
