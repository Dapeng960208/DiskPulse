# -*- coding: utf-8 -*-
"""Transaction checkpoint helpers used by Router-owned HTTP write boundaries."""

from sqlalchemy.orm import Session


def commit_checkpoint(db: Session) -> None:
    """Persist a domain checkpoint through the active HTTP transaction boundary."""
    db.commit()


def rollback_checkpoint(db: Session) -> None:
    """Discard a domain checkpoint through the active HTTP transaction boundary."""
    db.rollback()
