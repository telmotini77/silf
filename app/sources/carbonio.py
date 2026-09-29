"""Adaptador IMAP para Carbonio.

Cada mensaje se identifica con carpeta, UIDVALIDITY y UID. Así un reinicio o un
cambio de UIDVALIDITY no puede crear una entrega duplicada.
"""

import asyncio
import logging
import re
import ssl
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Iterable, Optional

from aioimaplib import aioimaplib
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ingest import Ingestor
from app.models import RawType, SubscriptionState
from app.sources.base import MailSource

logger = logging.getLogger(__name__)


class CarbonioSource(MailSource):
    provider_name = "carbonio"

    async def maintain(self, db: AsyncSession) -> None:
        """Carbonio no requiere renovación de una suscripción remota."""

    async def _connect(self) -> aioimaplib.IMAP4_SSL:
        context = ssl.create_default_context()
        if settings.CARBONIO_CA_FILE:
            context.load_verify_locations(cafile=settings.CARBONIO_CA_FILE)

        client = aioimaplib.IMAP4_SSL(
            host=settings.CARBONIO_IMAP_SERVER,
            port=settings.CARBONIO_IMAP_PORT,
            ssl_context=context,
            timeout=30.0,
        )
        await client.wait_hello_from_server()
        response = await client.login(settings.CARBONIO_EMAIL, settings.CARBONIO_PASSWORD)
        if response.result != "OK":
            raise RuntimeError("Carbonio rejected the IMAP credentials")
        return client

    async def _select_folder(self, client: aioimaplib.IMAP4_SSL) -> tuple[int, int]:
        # aioimaplib no actualiza su estado interno a SELECTED al usar EXAMINE.
        # SELECT no modifica mensajes por sí mismo y permite las operaciones UID
        # posteriores; la cuenta IMAP sigue pudiendo ser de solo lectura.
        response = await client.select(f'"{settings.CARBONIO_FOLDER}"')
        if response.result != "OK":
            raise RuntimeError(f"Unable to open folder {settings.CARBONIO_FOLDER!r}")

        uid_validity: Optional[int] = None
        uid_next: Optional[int] = None
        for line in response.lines:
            value = line.decode(errors="replace").upper()
            validity_match = re.search(r"UIDVALIDITY\s+(\d+)", value)
            next_match = re.search(r"UIDNEXT\s+(\d+)", value)
            if validity_match:
                uid_validity = int(validity_match.group(1))
            if next_match:
                uid_next = int(next_match.group(1))
        if uid_validity is None or uid_next is None:
            raise RuntimeError("Carbonio did not return UIDVALIDITY and UIDNEXT")
        return uid_validity, uid_next

    @staticmethod
    def _uids(lines: Iterable[bytes]) -> list[int]:
        values: list[int] = []
        for line in lines:
            for part in line.decode(errors="ignore").split():
                if part.isdigit():
                    values.append(int(part))
        return values

    @staticmethod
    def _uids_from_fetch(lines: Iterable[bytes]) -> list[int]:
        """Obtiene los UID devueltos por una respuesta FETCH de IMAP."""
        values: list[int] = []
        for line in lines:
            match = re.search(rb"\bUID\s+(\d+)", line)
            if match:
                values.append(int(match.group(1)))
        return values

    async def _find_new_uids(
        self, client: aioimaplib.IMAP4_SSL, last_uid: int, use_backfill: bool
    ) -> list[int]:
        """Devuelve UID, nunca números de secuencia IMAP.

        aioimaplib no implementa ``UID SEARCH``. Para el flujo normal, un
        ``UID FETCH ... (UID)`` conserva la identidad estable de cada correo.
        """
        if use_backfill:
            since = (datetime.now() - timedelta(days=settings.BACKFILL_DAYS)).strftime("%d-%b-%Y")
            response = await client.search(f"SINCE {since}")
            if response.result != "OK":
                raise RuntimeError("Carbonio could not search the requested backfill")
            sequence_numbers = self._uids(response.lines)
            if not sequence_numbers:
                return []
            response = await client.fetch(",".join(map(str, sequence_numbers)), "(UID)")
        else:
            response = await client.uid("FETCH", f"{last_uid + 1}:*", "(UID)")

        if response.result != "OK":
            raise RuntimeError("Carbonio could not search for new messages")
        return sorted({uid for uid in self._uids_from_fetch(response.lines) if uid > last_uid})

    async def _fetch_raw(self, client: aioimaplib.IMAP4_SSL, uid: int) -> Optional[bytes]:
        response = await client.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if response.result != "OK":
            logger.warning("Carbonio could not fetch UID %s", uid)
            return None
        # aioimaplib representa el literal del correo como ``bytearray``. La
        # respuesta también incluye líneas IMAP cortas de control; el EML es
        # siempre el bloque de mayor tamaño y se convierte a ``bytes`` antes
        # de guardarlo.
        literals = [
            bytes(line)
            for line in response.lines
            if isinstance(line, (bytes, bytearray))
            and line.strip() != b")"
            and not line.strip().endswith(b"FETCH completed")
        ]
        if literals:
            return max(literals, key=len)
        logger.warning("Carbonio returned no EML content for UID %s", uid)
        return None

    async def sync(self, db: AsyncSession) -> None:
        if self.provider_name not in settings.ACTIVE_SOURCES:
            return

        client = None
        try:
            client = await self._connect()
            uid_validity, uid_next = await self._select_folder(client)
            state = await self._get_state(db, self.provider_name)
            previous_validity = int(state.external_id) if state.external_id else None
            last_uid = int(state.cursor or 0)

            # La primera sincronización comienza en el siguiente UID para no
            # reenviar el historial por sorpresa. BACKFILL_DAYS puede habilitarlo.
            use_backfill = previous_validity != uid_validity and settings.BACKFILL_DAYS > 0
            if previous_validity != uid_validity:
                last_uid = 0 if use_backfill else max(0, uid_next - 1)
                state.external_id = str(uid_validity)

            new_uids = await self._find_new_uids(client, last_uid, use_backfill)
            for uid in new_uids:
                raw = await self._fetch_raw(client, uid)
                if raw is None:
                    continue
                provider_id = f"{settings.CARBONIO_FOLDER}:{uid_validity}:{uid}"
                if not await Ingestor.exists(db, self.provider_name, provider_id):
                    await Ingestor.ingest(db, self.provider_name, provider_id, raw, RawType.EML)

            if new_uids:
                state.cursor = str(max(new_uids))
            else:
                state.cursor = str(last_uid)
            await self._update_state(db, state)
        finally:
            if client is not None:
                with suppress(Exception):
                    await client.logout()

    async def run(self) -> None:
        """Mantiene una latencia acotada sin mezclar IMAP con el scheduler HTTP."""
        backoff = 1
        while True:
            try:
                from app.db import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    await self.sync(db)
                backoff = 1
                await asyncio.sleep(settings.CARBONIO_POLL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Carbonio synchronization failed; retrying in %ss", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)
