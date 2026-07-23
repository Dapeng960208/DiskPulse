# -*- coding: utf-8 -*-
import pytest
from fastapi import HTTPException


def test_agent_assessment_rejects_status_skips_and_accepts_a_single_next_step():
    from services.incidentAiAgentService import IncidentAiAssessment, validate_agent_assessment

    accepted = validate_agent_assessment(
        IncidentAiAssessment(
            classification="normal_fluctuation",
            urgency="low",
            summary="低负载 IOPS 短时波动，暂无服务影响证据。",
            investigation_steps=["继续观察下一采集周期"],
            resolution_steps=["无需设备写操作"],
            proposed_next_status="acknowledged",
            transition_reason="已完成初步研判。",
        ),
        current_status="open",
    )

    assert accepted.proposed_next_status == "acknowledged"
    with pytest.raises(ValueError, match="相邻"):
        validate_agent_assessment(
            accepted.model_copy(update={"proposed_next_status": "resolved"}),
            current_status="open",
        )


def test_incident_ai_settings_accept_enabled_models_in_explicit_priority_order(db_session):
    import models
    from services.incidentAiAgentService import update_settings

    db_session.add_all([
        models.AIConfig(id=1, name="disabled", provider="openai", model="disabled", enabled=False, enable_chat=False),
        models.AIConfig(id=2, name="fallback", provider="openai", model="fallback", enabled=True, enable_chat=False),
        models.AIConfig(id=3, name="primary", provider="openai", model="primary", enabled=True, enable_chat=True),
    ])
    db_session.commit()

    settings = update_settings(
        db_session,
        actor_id=None,
        enabled=True,
        model_ids=[3, 2],
        iops_absolute_floor=10.0,
        iops_baseline_ratio=0.05,
    )

    assert settings.enabled is True
    assert [binding.ai_model_id for binding in settings.model_bindings] == [3, 2]
    with pytest.raises(HTTPException, match="已启用"):
        update_settings(
            db_session,
            actor_id=None,
            enabled=True,
            model_ids=[1],
            iops_absolute_floor=10.0,
            iops_baseline_ratio=0.05,
        )
