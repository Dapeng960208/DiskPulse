# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)


StorageType = Literal["netapp", "isilon"]
AssociationType = Literal[
    "fault_log",
    "performance_anomaly",
    "capacity_threshold",
    "system_activity",
    "telemetry_degradation",
    "unknown",
]
ReviewStatus = Literal["reviewed", "pending"]
Severity = Literal["critical", "error", "warning", "info"]
_OFFICIAL_REFERENCE_DOMAINS_BY_STORAGE_TYPE = {
    "netapp": ("netapp.com",),
    "isilon": ("dell.com", "delltechnologies.com"),
}
_OFFICIAL_REFERENCE_DOMAINS = tuple(
    domain
    for domains in _OFFICIAL_REFERENCE_DOMAINS_BY_STORAGE_TYPE.values()
    for domain in domains
)


def _validate_event_code(value: str | None) -> str | None:
    if value is None:
        return None
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("事件代码不能包含空白字符或控制字符")
    return value


def _validate_reference_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or any(character.isspace() or ord(character) < 32 for character in value)
    ):
        raise ValueError("官方参考地址必须是有效的 HTTPS 地址")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("官方参考地址不能包含认证信息")
    try:
        explicit_port = parsed.port
    except ValueError as error:
        raise ValueError("官方参考地址端口格式无效") from error
    if explicit_port is not None or parsed.hostname.endswith(".") or "@" in value:
        raise ValueError("官方参考地址不能包含端口、尾点或 @ 字符")
    hostname = parsed.hostname.rstrip(".").lower()
    if not any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in _OFFICIAL_REFERENCE_DOMAINS
    ):
        raise ValueError("官方参考地址必须属于 NetApp 或 Dell 官方域名")
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            parsed.path or "/",
            parsed.query,
            parsed.fragment,
        )
    )


def validate_reviewed_definition_values(
    *,
    storage_type: str,
    review_status: str,
    association_type: str,
    official_reference_url: str | None,
    version_scope: str | None,
    recommended_solution_zh: str | None,
) -> None:
    if official_reference_url:
        normalized_reference = _validate_reference_url(official_reference_url)
        hostname = urlsplit(normalized_reference).hostname.lower()
        allowed_domains = _OFFICIAL_REFERENCE_DOMAINS_BY_STORAGE_TYPE.get(
            storage_type,
            (),
        )
        if not any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in allowed_domains
        ):
            vendor_label = "NetApp" if storage_type == "netapp" else "Dell PowerScale"
            raise ValueError(
                f"{vendor_label} 定义必须使用对应厂商的官方参考地址"
            )
    if review_status != "reviewed":
        return
    if association_type == "unknown":
        raise ValueError("已审核定义必须选择明确的关联类型")
    if not official_reference_url:
        raise ValueError("已审核定义必须提供官方 HTTPS 参考地址")
    _validate_reference_url(official_reference_url)
    if not version_scope:
        raise ValueError("已审核定义必须提供适用版本范围")
    if not recommended_solution_zh or not recommended_solution_zh.strip():
        raise ValueError("已审核定义必须填写推荐解决方案")


from schemas.base import UTCBaseModel as BaseModel


class VendorEventDefinitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    storage_type: StorageType
    event_code: str = Field(min_length=1, max_length=255)
    association_type: AssociationType
    title_zh: str = Field(min_length=1, max_length=255)
    description_zh: str = Field(min_length=1, max_length=2000)
    official_reference_url: str | None = Field(default=None, max_length=1000)
    default_severity: Severity | None = None
    version_scope: str | None = Field(default=None, max_length=255)
    review_status: ReviewStatus = "pending"
    recommended_solution_zh: str | None = Field(default=None, max_length=5000)
    is_active: StrictBool = True

    @field_validator("event_code")
    @classmethod
    def validate_event_code(cls, value: str) -> str:
        return _validate_event_code(value)

    @field_validator("official_reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return _validate_reference_url(value)

    @model_validator(mode="after")
    def require_reviewed_evidence(self):
        validate_reviewed_definition_values(
            storage_type=self.storage_type,
            review_status=self.review_status,
            association_type=self.association_type,
            official_reference_url=self.official_reference_url,
            version_scope=self.version_scope,
            recommended_solution_zh=self.recommended_solution_zh,
        )
        return self


class VendorEventDefinitionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    storage_type: StorageType | None = None
    event_code: str | None = Field(default=None, min_length=1, max_length=255)
    association_type: AssociationType | None = None
    title_zh: str | None = Field(default=None, min_length=1, max_length=255)
    description_zh: str | None = Field(default=None, min_length=1, max_length=2000)
    official_reference_url: str | None = Field(default=None, max_length=1000)
    default_severity: Severity | None = None
    version_scope: str | None = Field(default=None, max_length=255)
    review_status: ReviewStatus | None = None
    recommended_solution_zh: str | None = Field(default=None, max_length=5000)
    is_active: StrictBool | None = None

    @field_validator("event_code")
    @classmethod
    def validate_event_code(cls, value: str | None) -> str | None:
        return _validate_event_code(value)

    @field_validator("official_reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return _validate_reference_url(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个待更新字段")
        nullable_fields = {
            "official_reference_url",
            "default_severity",
            "version_scope",
            "recommended_solution_zh",
        }
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class VendorEventDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage_type: StorageType
    event_code: str
    association_type: AssociationType
    association_type_label: str
    title_zh: str
    description_zh: str
    official_reference_url: str | None = None
    default_severity: Severity | None = None
    version_scope: str | None = None
    review_status: ReviewStatus
    recommended_solution_zh: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VendorEventDefinitionPage(BaseModel):
    content: list[VendorEventDefinitionOut]
    total: int = Field(ge=0)


class VendorEventDiscoveryOut(BaseModel):
    created: int = Field(ge=0)
    existing: int = Field(ge=0)
    reconciled_incidents: int = Field(ge=0)
