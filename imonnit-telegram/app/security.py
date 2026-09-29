import hmac
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer()

def require_admin(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not hmac.compare_digest(token.encode('utf-8'), settings.ADMIN_TOKEN.encode('utf-8')):
        raise HTTPException(status_code=403, detail="Forbidden")
    return token
