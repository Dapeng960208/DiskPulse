# -*- coding: utf-8 -*-
"""Configuration-scoped delivery for derived Incident notifications only."""

from collections.abc import Iterable
from datetime import timezone

from appConfig import base_config
from models import Project, ProjectMembership, User
from services.feishuNotificationService import FeishuNotificationService
from utils.mailTools.emailNotification import EmailNotification
from utils.datetime_utils import utc_now


def resolve_recipient_usernames(
    config: dict,
    *,
    administrators: Iterable[str],
    project_owner: str | None = None,
    project_members: Iterable[str] = (),
) -> tuple[str, ...]:
    """Resolve recipients without changing any raw storage-alert delivery list."""
    if not config.get("enabled"):
        return ()
    recipients: list[str] = []
    if config.get("notify_administrators", True):
        recipients.extend(str(item) for item in administrators if item)
    if config.get("notify_project_owner", False) and project_owner:
        recipients.append(project_owner)
    if config.get("notify_project_members", False):
        recipients.extend(str(item) for item in project_members if item)
    recipients.extend(str(item) for item in config.get("extra_usernames", ()) or () if item)
    return tuple(dict.fromkeys(recipients))


def incident_notification_config() -> dict:
    configured = base_config.get("incident_notifications", {}) or {}
    return {
        "enabled": bool(configured.get("enabled", False)),
        "notify_administrators": bool(configured.get("notify_administrators", True)),
        "notify_project_owner": bool(configured.get("notify_project_owner", False)),
        "notify_project_members": bool(configured.get("notify_project_members", False)),
        "extra_usernames": tuple(configured.get("extra_usernames", ()) or ()),
        "feishu_enabled": bool(configured.get("feishu_enabled", False)),
        "email_enabled": bool(configured.get("email_enabled", False)),
    }


def should_send_incident_notification(
    *, created: bool, reopened: bool, severity_escalated: bool
) -> bool:
    """Derived Incident delivery is limited to lifecycle changes worth paging."""
    return created or reopened or severity_escalated


def _project_recipients(db, project_id: int | None) -> tuple[str | None, tuple[str, ...]]:
    if project_id is None:
        return None, ()
    project = db.get(Project, project_id)
    if project is None:
        return None, ()
    owner = db.get(User, project.in_charge_user_id) if project.in_charge_user_id is not None else None
    members = (
        db.query(User.rd_username)
        .join(ProjectMembership, ProjectMembership.user_id == User.id)
        .filter(ProjectMembership.project_id == project_id, User.rd_username.is_not(None))
        .all()
    )
    return (owner.rd_username if owner else None), tuple(row[0] for row in members)


def _recipient_emails(db, usernames: Iterable[str]) -> tuple[str, ...]:
    names = tuple(dict.fromkeys(item for item in usernames if item))
    if not names:
        return ()
    emails = db.query(User.email).filter(
        User.rd_username.in_(names),
        User.email.is_not(None),
    ).all()
    return tuple(dict.fromkeys(str(row[0]) for row in emails if row[0]))


def _incident_is_currently_silenced(incident) -> bool:
    silenced_until = incident.silenced_until
    if silenced_until is None:
        return False
    if silenced_until.tzinfo is None:
        silenced_until = silenced_until.replace(tzinfo=timezone.utc)
    return silenced_until > utc_now()


def notify_incident(db, incident, *, event: str) -> tuple[str, ...]:
    """Best-effort derived notification; source alerts and vendor events are untouched."""
    config = incident_notification_config()
    if event not in {"created", "reopened", "severity_escalated"}:
        return ()
    if not config["enabled"] or _incident_is_currently_silenced(incident):
        return ()
    owner, members = _project_recipients(db, incident.project_id)
    recipients = resolve_recipient_usernames(
        config,
        administrators=base_config.get("super_admin_usernames", ()) or (),
        project_owner=owner,
        project_members=members,
    )
    if not recipients:
        return recipients
    if config["feishu_enabled"]:
        feishu = base_config.get("feishu_notification", {}) or {}
        if feishu.get("enabled"):
            FeishuNotificationService(feishu).send(
                usernames=recipients,
                title=f"Incident {event}",
                paragraphs=[[{"tag": "text", "text": f"{incident.display_name}：{incident.category} / {incident.severity}"}]],
            )
    if config["email_enabled"]:
        emails = _recipient_emails(db, recipients)
        if emails:
            EmailNotification(db=db, type="storage").send_email(
                subject=f"DiskPulse Incident {event}",
                content=(
                    f"事件 {incident.id}：{incident.display_name} / "
                    f"{incident.category} / {incident.severity}。"
                ),
                recipient=list(emails),
                cc_admin=False,
            )
    return recipients
