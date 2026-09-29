"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2023-10-17 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Crear el ENUM de estado
    op.execute("CREATE TYPE messagestatus AS ENUM ('detectado', 'enviando', 'reintentar', 'enviado', 'fallido', 'ignorado')")
    
    # 2. Crear tabla mailbox_state
    op.create_table('mailbox_state',
        sa.Column('folder', sa.String(), nullable=False),
        sa.Column('uidvalidity', sa.BigInteger(), nullable=False),
        sa.Column('last_uid', sa.BigInteger(), nullable=False),
        sa.Column('last_idle_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('connected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('folder')
    )
    
    # 3. Crear tabla messages
    op.create_table('messages',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('folder', sa.String(), nullable=False),
        sa.Column('uidvalidity', sa.BigInteger(), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('message_id_header', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('sender', sa.String(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw', sa.LargeBinary(), nullable=True),
        sa.Column('status', postgresql.ENUM('detectado', 'enviando', 'reintentar', 'enviado', 'fallido', 'ignorado', name='messagestatus', create_type=False), nullable=False, server_default='detectado'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('delivery', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('folder', 'uidvalidity', 'uid', name='uq_messages_folder_uidv_uid')
    )
    
    op.create_index(op.f('ix_messages_folder'), 'messages', ['folder'], unique=False)
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    
    # Índice único parcial (Idempotencia en UIDVALIDITY regenerado)
    op.create_index('ix_messages_message_id', 'messages', ['message_id_header'], unique=True, postgresql_where=sa.text('message_id_header IS NOT NULL'))
    op.create_index('ix_messages_status_next_attempt', 'messages', ['status', 'next_attempt_at'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_messages_status_next_attempt', table_name='messages')
    op.drop_index('ix_messages_message_id', table_name='messages', postgresql_where=sa.text('message_id_header IS NOT NULL'))
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_folder'), table_name='messages')
    op.drop_table('messages')
    op.drop_table('mailbox_state')
    op.execute("DROP TYPE messagestatus")
