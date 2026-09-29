"""Remove the legacy JSON message type and its data.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM messages WHERE raw_type::text = 'JSON'")
    op.execute("ALTER TYPE rawtype RENAME TO rawtype_legacy")
    op.execute("CREATE TYPE rawtype AS ENUM ('EML')")
    op.execute(
        "ALTER TABLE messages ALTER COLUMN raw_type TYPE rawtype "
        "USING raw_type::text::rawtype"
    )
    op.execute("DROP TYPE rawtype_legacy")


def downgrade() -> None:
    op.execute("ALTER TYPE rawtype RENAME TO rawtype_legacy")
    op.execute("CREATE TYPE rawtype AS ENUM ('EML', 'JSON')")
    op.execute(
        "ALTER TABLE messages ALTER COLUMN raw_type TYPE rawtype "
        "USING raw_type::text::rawtype"
    )
    op.execute("DROP TYPE rawtype_legacy")
