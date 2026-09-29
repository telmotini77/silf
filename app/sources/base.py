from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import SubscriptionState
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class MailSource(ABC):
    @abstractmethod
    async def maintain(self, db: AsyncSession):
        """Renueva la suscripción si es necesario."""
        pass

    @abstractmethod
    async def sync(self, db: AsyncSession):
        """Sincroniza mensajes nuevos basándose en el estado o de forma periódica."""
        pass

    async def _get_state(self, db: AsyncSession, provider: str) -> SubscriptionState:
        stmt = select(SubscriptionState).where(SubscriptionState.provider == provider)
        res = await db.execute(stmt)
        state = res.scalars().first()
        if not state:
            state = SubscriptionState(provider=provider)
            db.add(state)
            await db.commit()
            await db.refresh(state)
        return state

    async def _update_state(self, db: AsyncSession, state: SubscriptionState):
        db.add(state)
        await db.commit()
