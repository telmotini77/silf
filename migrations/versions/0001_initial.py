"""Init

Revision ID: 0001
Revises: 
Create Date: 2026-09-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=False),
        sa.Column('message_id_header', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('sender', sa.String(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw', sa.LargeBinary(), nullable=True),
        sa.Column('raw_type', sa.Enum('EML', name='rawtype'), nullable=False),
        sa.Column('status', sa.Enum('RECEIVED', 'SENDING', 'RETRY', 'SENT', 'FAILED', 'IGNORED', name='messagestatus'), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('delivery', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'provider_id', name='uq_messages_source_provider')
    )
    op.create_index('ix_messages_id', 'messages', ['id'], unique=False)
    op.create_index('ix_messages_source', 'messages', ['source'], unique=False)
    op.create_index('ix_messages_provider_id', 'messages', ['provider_id'], unique=False)
    op.create_index('ix_messages_status_next_attempt', 'messages', ['status', 'next_attempt_at'], unique=False)

    op.create_table(
        'subscription_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('cursor', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_subscription_state_id', 'subscription_state', ['id'], unique=False)
    op.create_index('ix_subscription_state_provider', 'subscription_state', ['provider'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_subscription_state_provider', table_name='subscription_state')
    op.drop_index('ix_subscription_state_id', table_name='subscription_state')
    op.drop_table('subscription_state')
    
    op.drop_index('ix_messages_status_next_attempt', table_name='messages')
    op.drop_index('ix_messages_provider_id', table_name='messages')
    op.drop_index('ix_messages_source', table_name='messages')
    op.drop_index('ix_messages_id', table_name='messages')
    op.drop_table('messages')
