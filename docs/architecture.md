# Arquitectura y comunicación entre módulos

## Flujo de una alerta

1. El adaptador `sources/carbonio.py` recibe un correo IMAP y lo entrega a
   `Ingestor`.
2. `Ingestor` aplica filtros y crea un registro único por `(source, provider_id)`.
   Si el registro ya existe, termina sin duplicar trabajo.
3. El dispatcher reclama mensajes con `FOR UPDATE SKIP LOCKED`, cambia su estado
   a `SENDING` y libera la transacción antes de llamar a Telegram.
4. `delivery.py` registra cada parte enviada en `messages.delivery`. Esto permite
   retomar una entrega incompleta sin volver a enviar las partes ya confirmadas.
5. El resultado queda en `SENT`, `RETRY`, `FAILED` o `IGNORED`. El scheduler
   devuelve a la cola los mensajes abandonados durante una interrupción.

## Contratos

| Capa | Recibe | Produce |
| --- | --- | --- |
| Fuente | Carbonio IMAP | `source`, `provider_id`, `raw`, `RawType` |
| Ingesta | Entrada normalizada | Registro idempotente en `messages` |
| Worker | Identificador de mensaje reclamado | Estado y seguimiento de entrega |
| Procesamiento | JSON o EML | Texto y documentos seguros para Telegram |
| Transporte | Texto/documento | ID de mensaje de Telegram |

No se permiten dependencias inversas: los procesadores no conocen HTTP, los
adaptadores no entregan directamente a Telegram y la entrega no conoce el
proveedor que originó el mensaje.

## Operación segura

- Utiliza una cuenta de correo dedicada y de mínimo privilegio para Carbonio.
- Mantén `ADMIN_TOKEN` fuera del repositorio.
- Revisa periódicamente `/admin/messages?status=fallido` y los logs JSON.
- Para aumentar capacidad, inicia más instancias del worker: PostgreSQL impide
  que dos instancias reclamen el mismo registro.
