from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.database import db_dependency
import hmac
import hashlib
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-jwt-key-change-this")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """Hash password using HMAC-SHA256."""
    return hmac.new(
        SECRET_KEY.encode(),
        password.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password using HMAC-SHA256."""
    expected = hash_password(plain)
    return hmac.compare_digest(expected, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=EXPIRE_MIN))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn=Depends(db_dependency)
):
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (int(user_id),))
        user = cur.fetchone()

    if not user:
        raise cred_exc
    return user


def require_role(*roles):
    def checker(current_user=Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker