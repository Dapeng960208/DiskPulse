# -*- coding: utf-8 -*-
import pytest


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
