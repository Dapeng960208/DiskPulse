# -*- coding: utf-8 -*-
import json


def test_audit_redaction_removes_windows_forward_slash_paths_without_sensitive_keys():
    from services.audit_service import redact_audit_payload

    redacted = redact_audit_payload({"location": "C:/diskpulse/private/alice"})

    assert "C:/diskpulse/private/alice" not in json.dumps(redacted)
    assert redacted == {"location": "[REDACTED]"}
