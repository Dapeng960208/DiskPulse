"""Keep the published vendor event data revision in the migration chain.

Vendor event definitions are initialized by
``backend/scripts/initialize_vendor_event_definitions.py``. This revision remains
as a compatibility marker for databases that already applied ``000000000018``.

Revision ID: 000000000018
Revises: 000000000017
"""


revision = "000000000018"
down_revision = "000000000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
