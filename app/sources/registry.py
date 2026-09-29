"""Composición de los conectores externos habilitados."""

import asyncio

from app.config import settings


def continuous_source_tasks() -> list[asyncio.Task]:
    if "carbonio" not in settings.ACTIVE_SOURCES:
        return []
    from app.sources.carbonio import CarbonioSource
    return [asyncio.create_task(CarbonioSource().run(), name="carbonio-receiver")]
