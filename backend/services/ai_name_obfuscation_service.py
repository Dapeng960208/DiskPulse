# -*- coding: utf-8 -*-
import re
import secrets
import string
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from crud import aiCrud
from crud.aiNameObfuscationCrud import list_authorized_name_candidates
from models import AIConversation, AIConversationNameAlias, User
from services.ai_security import decrypt_secret, encrypt_secret
from services.project_access_service import accessible_project_ids


_MAX_ALIASES_PER_CONTEXT = 2_000
_ALIAS_SUFFIX_ALPHABET = string.ascii_uppercase + string.digits
_ALIAS_SUFFIX_LENGTH = 8
_AMBIGUOUS_KIND = "资源"


class NameObfuscationError(RuntimeError):
    """Raised when name privacy cannot be guaranteed before a provider call."""


@dataclass(frozen=True)
class _AliasEntry:
    alias: str
    entity_kind: str


class AliasStreamRestorer:
    """Buffers only a possible alias prefix so SSE never leaks a partial alias."""

    def __init__(self, obfuscator: "ConversationNameObfuscator"):
        self._obfuscator = obfuscator
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        hold_length = self._possible_alias_prefix_length()
        safe_text = self._buffer[:-hold_length] if hold_length else self._buffer
        self._buffer = self._buffer[-hold_length:] if hold_length else ""
        return self._obfuscator.restore_text(safe_text)

    def flush(self) -> str:
        text, self._buffer = self._buffer, ""
        return self._obfuscator.restore_text(text)

    def _possible_alias_prefix_length(self) -> int:
        if not self._buffer:
            return 0
        maximum = min(
            max((len(alias) - 1 for alias in self._obfuscator.aliases), default=0),
            len(self._buffer),
        )
        for length in range(maximum, 0, -1):
            suffix = self._buffer[-length:]
            if any(alias.startswith(suffix) for alias in self._obfuscator.aliases):
                return length
        return 0


class ConversationNameObfuscator:
    def __init__(
        self,
        db: Session,
        *,
        conversation_id: int,
        epoch: int,
        candidates: dict[str, set[str]],
        aliases_by_value: dict[str, _AliasEntry],
    ):
        self._db = db
        self._conversation_id = conversation_id
        self._epoch = epoch
        self._candidates = candidates
        self._aliases_by_value = aliases_by_value
        self._values_by_alias = {
            entry.alias: value for value, entry in aliases_by_value.items()
        }

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(self._values_by_alias)

    def obfuscate_messages(self, messages: list[dict]) -> list[dict]:
        return [self.obfuscate_value(item) for item in messages]

    def obfuscate_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.obfuscate_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.obfuscate_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.obfuscate_value(item) for item in value)
        if isinstance(value, str):
            return self.obfuscate_text(value)
        return value

    def restore_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self.restore_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.restore_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.restore_value(item) for item in value)
        if isinstance(value, str):
            return self.restore_text(value)
        return value

    def obfuscate_text(self, text: str) -> str:
        values = set(self._candidates) | set(self._aliases_by_value)
        protected_values = sorted((value for value in values if value), key=len, reverse=True)
        if not protected_values:
            return text
        pattern = re.compile("|".join(re.escape(value) for value in protected_values))
        return pattern.sub(lambda match: self._alias_for(match.group(0)), text)

    def restore_text(self, text: str) -> str:
        result = text
        for alias, value in sorted(self._values_by_alias.items(), key=lambda item: len(item[0]), reverse=True):
            result = result.replace(alias, value)
        return result

    def stream_restorer(self) -> AliasStreamRestorer:
        return AliasStreamRestorer(self)

    def persist(self) -> None:
        try:
            self._db.commit()
        except Exception as error:
            self._db.rollback()
            raise NameObfuscationError("名称混淆映射无法保存") from error

    def _alias_for(self, value: str) -> str:
        existing = self._aliases_by_value.get(value)
        if existing is not None:
            return existing.alias
        if len(self._aliases_by_value) >= _MAX_ALIASES_PER_CONTEXT:
            raise NameObfuscationError("名称混淆映射数量超出安全上限")
        kinds = self._candidates.get(value, set())
        entity_kind = next(iter(kinds)) if len(kinds) == 1 else _AMBIGUOUS_KIND
        alias = self._new_alias(entity_kind)
        encrypted = encrypt_secret(value)
        if not encrypted:
            raise NameObfuscationError("名称混淆映射无法加密")
        aiCrud.add_conversation_name_alias(
            self._db,
            AIConversationNameAlias(
                conversation_id=self._conversation_id,
                epoch=self._epoch,
                alias=alias,
                entity_kind=entity_kind,
                original_value_encrypted=encrypted,
            ),
        )
        entry = _AliasEntry(alias=alias, entity_kind=entity_kind)
        self._aliases_by_value[value] = entry
        self._values_by_alias[alias] = value
        return alias

    def _new_alias(self, entity_kind: str) -> str:
        while True:
            suffix = "".join(secrets.choice(_ALIAS_SUFFIX_ALPHABET) for _ in range(_ALIAS_SUFFIX_LENGTH))
            alias = f"{entity_kind}-{suffix}"
            if alias not in self._values_by_alias:
                return alias


def prepare_name_obfuscator(
    db: Session,
    *,
    conversation: AIConversation,
    current_user: User,
    current_message_id: int,
    epoch: int,
) -> ConversationNameObfuscator:
    if conversation.name_obfuscation_epoch != epoch:
        conversation.name_obfuscation_epoch = epoch
        conversation.name_obfuscation_from_message_id = current_message_id
        self_context_changed = True
    else:
        self_context_changed = False
    if conversation.name_obfuscation_from_message_id is None:
        conversation.name_obfuscation_from_message_id = current_message_id
        self_context_changed = True
    if self_context_changed:
        try:
            db.flush()
        except Exception as error:
            raise NameObfuscationError("名称混淆上下文无法初始化") from error

    aliases_by_value: dict[str, _AliasEntry] = {}
    for stored in aiCrud.list_conversation_name_aliases(
        db,
        conversation_id=conversation.id,
        epoch=epoch,
    ):
        value = decrypt_secret(stored.original_value_encrypted)
        if not value:
            raise NameObfuscationError("名称混淆映射无法解密")
        aliases_by_value[value] = _AliasEntry(alias=stored.alias, entity_kind=stored.entity_kind)
    try:
        candidates = list_authorized_name_candidates(
            db,
            current_user=current_user,
            project_ids=accessible_project_ids(db, current_user),
        )
    except Exception as error:
        raise NameObfuscationError("名称混淆资源范围无法加载") from error
    return ConversationNameObfuscator(
        db,
        conversation_id=conversation.id,
        epoch=epoch,
        candidates=candidates,
        aliases_by_value=aliases_by_value,
    )
