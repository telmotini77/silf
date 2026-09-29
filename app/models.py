from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Enum, UniqueConstraint, Index, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
import enum
from typing import Optional, Dict, Any

Base = declarative_base()

class MessageStatus(str, enum.Enum):
    RECEIVED = "recibido"
    SENDING = "enviando"
    RETRY = "reintentar"
    SENT = "enviado"
    FAILED = "fallido"
    IGNORED = "ignorado"

class RawType(str, enum.Enum):
    EML = "eml"

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint('source', 'provider_id', name='uq_messages_source_provider'),
        Index('ix_messages_status_next_attempt', 'status', 'next_attempt_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String, index=True)  # carbonio
    provider_id: Mapped[str] = mapped_column(String, index=True)
    message_id_header: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    raw: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True) 
    raw_type: Mapped[RawType] = mapped_column(Enum(RawType))
    
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus), default=MessageStatus.RECEIVED)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # JSONB for tracking delivery steps (e.g. {"text:0": 1234, "eml": 1235})
    delivery: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SubscriptionState(Base):
    __tablename__ = "subscription_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String, index=True, unique=True)
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cursor: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # último UID de Carbonio
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
