# -*- coding: utf-8 -*-
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from appConfig import base_config


PREFIX = "fernet::"


def _secret() -> str:
    value = str(base_config.get("ai.config_secret_key", "")).strip()
    if len(value) < 16 or value.lower().startswith(("change-me", "replace-with")):
        raise RuntimeError("ai.config_secret_key must be an independent non-placeholder secret")
    return value


def _fernet() -> Fernet:
    digest = hashlib.sha256(_secret().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return f"{PREFIX}{_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')}"


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    if not ciphertext.startswith(PREFIX):
        return ""
    try:
        return _fernet().decrypt(ciphertext[len(PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    if len(plaintext) <= 8:
        return "****"
    return f"{plaintext[:4]}****{plaintext[-4:]}"
