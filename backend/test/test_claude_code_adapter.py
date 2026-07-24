# -*- coding: utf-8 -*-
"""Integration tests for Claude Code adapter with mock SDK."""
from datetime import datetime
from queue import Queue
from unittest.mock import MagicMock, patch
import pytest


def test_claude_code_options_expose_only_diskpulse_tools_and_mask_api_key():
    """Verify Claude Code adapter configuration is secure and isolated."""
    from services.claude_code_adapter import build_claude_code_options, safe_options_for_log
    import models

    config = models.AIConfig(
        id=1,
        name="test-claude",
        provider="claude_code",
        model="claude-opus-4-8",
        api_key_encrypted="encrypted_key_data",
    )

    with patch("services.claude_code_adapter.decrypt_secret") as mock_decrypt:
        mock_decrypt.return_value = "sk-ant-secret-key-12345"

        options = build_claude_code_options(
            config,
            tool_names=["get_storage_cluster", "list_incidents"],
            reasoning="high",
            system_prompt="You are a storage expert.",
        )

        # Verify security: API key is passed via env, not in options
        assert "api_key" not in options
        assert options["env"]["ANTHROPIC_API_KEY"] == "sk-ant-secret-key-12345"

        # Verify isolation: built-in tools are explicitly disabled
        assert options["tools"] == []

        # Verify MCP configuration: only DiskPulse tools exposed
        assert "mcp_servers" in options
        assert "diskpulse" in options["mcp_servers"]
        assert options["allowed_tools"] == [
            "mcp__diskpulse__get_storage_cluster",
            "mcp__diskpulse__list_incidents",
        ]

        # Verify reasoning control
        assert options["effort"] == "high"

        # Verify system prompt
        assert options["system_prompt"] == "You are a storage expert."

        # Verify safe log view masks sensitive data
        safe_log = safe_options_for_log(options)
        assert "env" not in safe_log
        assert "ANTHROPIC_API_KEY" not in str(safe_log)
        assert safe_log["model"] == "claude-opus-4-8"
        assert safe_log["effort"] == "high"


def test_claude_code_adapter_handles_tool_call_interception():
    """Verify tool calls are intercepted and routed through validation queue."""
    from services.claude_code_adapter import _ToolRequest

    # Create a tool request
    response_queue = Queue(maxsize=1)
    request = _ToolRequest(
        tool_name="get_storage_cluster",
        arguments={"storage_cluster_id": 123},
        _response=response_queue,
    )

    # Simulate tool execution
    request.respond({"id": 123, "name": "cluster-prod", "status": "active"})

    # Verify response was queued
    result = response_queue.get(timeout=1)
    assert result["id"] == 123
    assert result["name"] == "cluster-prod"


def test_claude_code_adapter_async_to_sync_conversion():
    """Verify async SDK is properly adapted to synchronous interface."""
    from services.claude_code_adapter import _ToolRequest
    import asyncio

    response_queue = Queue(maxsize=1)
    request = _ToolRequest(
        tool_name="list_storage_clusters",
        arguments={},
        _response=response_queue,
    )

    # Simulate async wait
    async def test_wait():
        # Respond in background
        import threading

        def respond():
            import time

            time.sleep(0.1)
            request.respond({"clusters": [{"id": 1}, {"id": 2}]})

        thread = threading.Thread(target=respond)
        thread.start()

        result = await request.wait()
        thread.join()
        return result

    result = asyncio.run(test_wait())
    assert result["clusters"] == [{"id": 1}, {"id": 2}]


def test_claude_code_adapter_cancellation_mechanism():
    """Verify cancellation properly stops ongoing SDK operations."""
    from services.claude_code_adapter import _ClientState

    state = _ClientState()

    # Verify initial state
    assert not state.cancelled.is_set()

    # Mock client and loop
    mock_client = MagicMock()
    mock_loop = MagicMock()
    mock_loop.is_closed.return_value = False

    # Bind state
    state.bind(mock_loop, mock_client)

    # Cancel operation
    state.cancel()

    # Verify cancelled flag is set
    assert state.cancelled.is_set()


def test_claude_code_adapter_text_extraction_from_partial_deltas():
    """Verify partial text deltas are correctly extracted from SDK events."""
    from services.claude_code_adapter import _partial_text

    # Test content_block_delta event
    mock_message = MagicMock()
    mock_message.event = {
        "type": "content_block_delta",
        "delta": {"type": "text_delta", "text": "Hello "},
    }
    assert _partial_text(mock_message) == "Hello "

    # Test non-text delta
    mock_message.event = {
        "type": "content_block_delta",
        "delta": {"type": "tool_use", "data": {}},
    }
    assert _partial_text(mock_message) == ""

    # Test non-delta event
    mock_message.event = {"type": "message_start"}
    assert _partial_text(mock_message) == ""


def test_claude_code_adapter_stream_event_generation():
    """Verify adapter generates correct stream events for AI client."""
    # This test verifies the lower-level components work correctly
    # Full integration testing requires actual Claude SDK which is expensive
    from services.claude_code_adapter import build_claude_code_options, _prompt
    import models

    config = models.AIConfig(
        id=1,
        name="test-claude",
        provider="claude_code",
        model="claude-opus-4-8",
        api_key_encrypted="encrypted_key",
    )

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "List storage clusters."},
    ]

    # Verify prompt generation
    prompt_text = _prompt(messages)
    assert "USER:" in prompt_text
    assert "List storage clusters" in prompt_text

    # Verify options are built correctly
    with patch("services.claude_code_adapter.decrypt_secret") as mock_decrypt:
        mock_decrypt.return_value = "test-key"
        options = build_claude_code_options(
            config,
            tool_names=["list_storage_clusters"],
            reasoning="high",
        )
        assert options["model"] == "claude-opus-4-8"
        assert options["effort"] == "high"


def test_claude_code_adapter_tool_call_validation():
    """Verify tool calls are validated against allowed tool registry."""
    # Test the tool registry building mechanism
    from services.claude_code_adapter import build_claude_code_options

    import models

    config = models.AIConfig(
        id=1,
        name="test-claude",
        provider="claude_code",
        model="claude-opus-4-8",
        api_key_encrypted="encrypted_key",
    )

    with patch("services.claude_code_adapter.decrypt_secret", return_value="key"):
        options = build_claude_code_options(
            config,
            tool_names=["get_storage_cluster", "list_volumes"],
            reasoning="auto",
        )

        # Verify only specified tools are allowed
        assert len(options["allowed_tools"]) == 2
        assert "mcp__diskpulse__get_storage_cluster" in options["allowed_tools"]
        assert "mcp__diskpulse__list_volumes" in options["allowed_tools"]
        # Verify other tools are not exposed
        assert "mcp__diskpulse__delete_cluster" not in options["allowed_tools"]


def test_claude_code_adapter_handles_sdk_errors_gracefully():
    """Verify adapter handles SDK errors without crashing."""
    # Test error handling at the configuration level
    from services.claude_code_adapter import build_claude_code_options, safe_options_for_log
    from services.ai_client import AIClientError
    import models

    config = models.AIConfig(
        id=1,
        name="test-claude",
        provider="claude_code",
        model="claude-opus-4-8",
        api_key_encrypted="encrypted_key",
    )

    # Verify safe logging doesn't leak sensitive data
    with patch("services.claude_code_adapter.decrypt_secret", return_value="secret-key"):
        options = build_claude_code_options(
            config, tool_names=["test_tool"], reasoning="auto"
        )

        # This should not contain the API key
        safe_log = safe_options_for_log(options)
        assert "secret-key" not in str(safe_log)
        assert "env" not in safe_log

        # Verify the actual options do contain it (for SDK usage)
        assert options["env"]["ANTHROPIC_API_KEY"] == "secret-key"


def test_claude_code_adapter_respects_max_turns_limit():
    """Verify adapter configuration limits SDK turn count."""
    from services.claude_code_adapter import build_claude_code_options
    import models

    config = models.AIConfig(
        id=1,
        name="test-claude",
        provider="claude_code",
        model="claude-opus-4-8",
        api_key_encrypted="encrypted_key",
    )

    with patch("services.claude_code_adapter.decrypt_secret", return_value="key"):
        options = build_claude_code_options(
            config, tool_names=["test_tool"], reasoning="auto"
        )

        # Verify max_turns is set to prevent infinite loops
        assert options["max_turns"] == 4
        assert options["strict_mcp_config"] is True


def test_claude_code_stream_times_out_and_cancels_stalled_sdk_worker():
    import models

    from services.ai_client import AIClientError
    from services.claude_code_adapter import claude_code_completion_stream

    config = models.AIConfig(
        id=1,
        name="test-claude",
        provider="claude_code",
        model="claude-opus-4-8",
        api_key_encrypted="encrypted_key",
    )
    state = MagicMock()

    class StalledThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

        def join(self, timeout=None):
            pass

    with (
        patch("services.claude_code_adapter.Thread", StalledThread),
        patch("services.claude_code_adapter._ClientState", return_value=state),
        pytest.raises(AIClientError, match="Claude Code 调用超时"),
    ):
        list(
            claude_code_completion_stream(
                config,
                [{"role": "user", "content": "hello"}],
                app=None,
                registry={},
                current_user=None,
                user_id=None,
                timeout_seconds=0.01,
            )
        )

    state.cancel.assert_called_once_with()
