# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AIProvider = Literal[
    "openai",
    "openrouter",
    "ollama",
    "claude",
    "claude_code",
    "deepseek",
    "dashscope",
    "volcengine",
    "zhipu",
    "moonshot",
    "minimax",
    "qianfan",
    "hunyuan",
]
ReasoningValue = Literal[
    "auto",
    "off",
    "on",
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
]


from schemas.base import UTCBaseModel as BaseModel


class AIModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    provider: AIProvider = "openai"
    base_url: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=200)
    enabled: bool = False
    enable_chat: bool = True
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=128000)
    system_prompt: str | None = Field(default=None, max_length=8000)


class AIModelPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    provider: AIProvider | None = None
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    enable_chat: bool | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    system_prompt: str | None = Field(default=None, max_length=8000)


class AIModelDiscoveryRequest(BaseModel):
    provider: AIProvider = "openai"
    base_url: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=500)


class AIModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    provider: str
    base_url: str
    api_key_masked: str
    api_key_configured: bool
    model: str
    enabled: bool
    enable_chat: bool
    temperature: float
    max_tokens: int
    system_prompt: str | None
    capability_status: str
    capability_error: str | None
    capability_updated_at: datetime | None
    reasoning_control: dict[str, Any]
    is_default: bool
    created_by: int | None
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=255)
    model_id: int | None = Field(default=None, ge=1)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
    reasoning: ReasoningValue = "auto"


class AIPlatformSettingsPatch(BaseModel):
    default_chat_model_id: int | None = Field(default=None, ge=1)
    name_obfuscation_enabled: bool | None = None


class QuotaConfirmationDecision(BaseModel):
    decision: Literal["confirm", "cancel"]
