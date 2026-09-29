# iMonnit Telegram Bridge (IMAP IDLE)

Este servicio se conecta mediante IMAPS (puerto 993) a un buzón Carbonio utilizando el comando IDLE. Escucha alertas de iMonnit y las reenvía a Telegram sin exponer ningún webhook al internet.

## Pasos para configuración inicial

### 1. Credencial IMAP en Carbonio
Debes crear una cuenta de correo en tu servidor Carbonio exclusivamente para este servicio (ej. `alertas-imonnit@tuempresa.com`). 
1. Accede a la consola de administración de Carbonio.
2. Crea el buzón y establécele una contraseña segura.
3. Asegúrate de que el protocolo IMAP esté habilitado para esta cuenta.
4. **Mínimo Privilegio:** Evita dar permisos de envío (SMTP) o acceso a otros buzones; solo necesita acceder a su propio INBOX.

### 2. Archivo de Configuración (.env)
Copia el archivo `.env.example` a `.env`:
```bash
cp .env.example .env
```
Luego, genera un token seguro de administración y pégalo allí junto con tus claves de Carbonio y Telegram:
```bash
python scripts/gen_secrets.py
```

Si Carbonio usa un certificado autofirmado, copia tu archivo CA (ej. `ca.crt`) al servidor y define su ruta en `CARBONIO_CA_FILE=/app/ca.crt` montándolo como volumen en docker.

### 3. Prueba de Conexión y Capacidades
Antes de arrancar todo, verifica que tu buzón permita IDLE y que las credenciales funcionen:
```bash
# Requiere las variables de entorno configuradas
python scripts/test_carbonio.py
```

### 4. Arrancar con Docker Compose
```bash
docker-compose up -d --build
```
La aplicación aplicará automáticamente la migración `alembic upgrade head` sobre PostgreSQL y se conectará al IMAP.

### 5. Ejecutar Pruebas Locales (Opcional)
```bash
pip install -e ".[dev]"
pytest -v
```

## Limitaciones (No verificado sin un servidor real)
Dado que el código ha sido escrito sin interactuar con tu servidor Carbonio real en vivo, ten en cuenta:
1. **Certificados TLS**: Si el CA proporcionado es inválido o el hostname no coincide exactamente con el certificado del servidor, Python rechazará la conexión.
2. **UIDNEXT vs Comportamiento Real**: El estándar IMAP dice que `SEARCH UID N:*` puede devolver `N` si no hay correos nuevos. El código ignora los UIDs `<= last_uid`, pero en algunos servidores privativos el comportamiento de IDLE puede ser peculiar y requerir *polling* en lugar de *push*.
3. **Pausas Largas**: El `IDLE_RENEW_MINUTES` está en 25 minutos. Algunos balanceadores de carga cortan sockets TCP inactivos en 5 o 10 minutos. Si notas desconexiones constantes, baja ese valor.
