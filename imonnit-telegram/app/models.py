from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, BigInteger, Boolean, Enum, UniqueConstraint, Index, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
import enum
import sqlalchemy as sa
from typing import Optional, Dict, Any

Base = declarative_base()

class MessageStatus(str, enum.Enum):
    DETECTED = "detectado"
    SENDING = "enviando"
    RETRY = "reintentar"
    SENT = "enviado"
    FAILED = "fallido"
    IGNORED = "ignorado"

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint('folder', 'uidvalidity', 'uid', name='uq_messages_folder_uidv_uid'),
        Index('ix_messages_status_next_attempt', 'status', 'next_attempt_at'),
        Index('ix_messages_message_id', 'message_id_header', postgresql_where=sa.text("message_id_header IS NOT NULL"), unique=True)
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    folder: Mapped[str] = mapped_column(String, index=True)
    uidvalidity: Mapped[int] = mapped_column(BigInteger)
    uid: Mapped[int] = mapped_column(BigInteger)
    
    message_id_header: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    raw: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True) 
    
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus), default=MessageStatus.DETECTED)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    delivery: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class MailboxState(Base):
    __tablename__ = "mailbox_state"
    folder: Mapped[str] = mapped_column(String, primary_key=True)
    uidvalidity: Mapped[int] = mapped_column(BigInteger)
    last_uid: Mapped[int] = mapped_column(BigInteger)
    last_idle_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
