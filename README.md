# Carbonio → Telegram

Servicio que lee todos los correos nuevos de un buzón Carbonio mediante IMAPS,
los guarda primero en PostgreSQL y los reenvía a Telegram. La cola persistente
protege las alertas ante reinicios, fallos de red y reintentos.

## Estructura

```
Carbonio IMAP → sources/carbonio → ingest → PostgreSQL/messages
                                                ↓
worker/dispatcher → worker/delivery → telegram/client → Telegram
```

- `sources/`: conexión incremental y segura al buzón Carbonio.
- `ingest.py`: deduplicación por UID y activación del worker.
- `worker/`: cola, reintentos y entrega sin bloquear la base de datos.
- `processing/`: parseo y limpieza segura de mensajes EML.
- `telegram/`: único adaptador de salida.

## Configuración

Los valores reales se guardan únicamente en `.env`. Para iniciar se requieren:

```env
ACTIVE_SOURCES=["carbonio"]
CARBONIO_IMAP_SERVER=...
CARBONIO_IMAP_PORT=993
CARBONIO_EMAIL=...
CARBONIO_PASSWORD=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
DATABASE_URL=...
```

`ALLOWED_SENDERS=[]` y `SUBJECT_KEYWORDS=[]` reenvían todos los correos. La
primera conexión solo procesa mensajes nuevos; usa `BACKFILL_DAYS` si necesitas
incorporar una ventana del historial.

## Ejecución

```bash
pip install -e ".[dev]"
pytest
docker compose up -d --build
```

`GET /health/` confirma que el proceso está vivo y `GET /health/ready` confirma
la conexión con PostgreSQL. La administración requiere `X-Admin-Token`.
