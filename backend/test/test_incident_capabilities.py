from types import SimpleNamespace


def test_incident_capabilities_only_offer_the_valid_assignment_action(monkeypatch):
    from services import forecastIncidentService as analytics

    monkeypatch.setattr(
        analytics.project_access_service,
        "incident_capabilities",
        lambda _db, _user, _project_id: {"edit": True, "create_maintenance_window": False},
    )
    monkeypatch.setattr(analytics, "is_super_admin", lambda user: user.id == 1)
    incident = SimpleNamespace(project_id=3, assigned_user_id=7)

    assignee_capabilities = analytics.incident_capabilities(
        None, current_user=SimpleNamespace(id=7), incident=incident
    )
    another_editor_capabilities = analytics.incident_capabilities(
        None, current_user=SimpleNamespace(id=8), incident=incident
    )
    super_admin_capabilities = analytics.incident_capabilities(
        None, current_user=SimpleNamespace(id=1), incident=incident
    )

    assert assignee_capabilities["claim"] is False
    assert assignee_capabilities["release"] is True
    assert another_editor_capabilities["claim"] is False
    assert another_editor_capabilities["release"] is False
    assert super_admin_capabilities["release"] is True
