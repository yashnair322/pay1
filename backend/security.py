
from datetime import datetime, timedelta
import jwt
from cryptography.fernet import Fernet
import os
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
import time
from typing import Dict, Optional

# Generate encryption key if not exists
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# Rate limiting storage
LOGIN_ATTEMPTS: Dict[str, list] = {}
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = 3600  # 1 hour window
SESSION_DURATION = 21600  # 6 hours

# Session tracking
user_sessions: Dict[str, datetime] = {}

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def check_rate_limit(email: str) -> bool:
    """Check if user has exceeded login attempts"""
    now = time.time()
    if email not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[email] = []
    
    # Clean old attempts
    LOGIN_ATTEMPTS[email] = [attempt for attempt in LOGIN_ATTEMPTS[email] 
                           if now - attempt < ATTEMPT_WINDOW]
    
    if len(LOGIN_ATTEMPTS[email]) >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later."
        )
    
    LOGIN_ATTEMPTS[email].append(now)
    return True

def record_session(email: str):
    """Record new user session"""
    user_sessions[email] = datetime.utcnow()

def check_session_valid(email: str) -> bool:
    """Check if user session is still valid"""
    if email not in user_sessions:
        return False
    
    session_age = datetime.utcnow() - user_sessions[email]
    return session_age.total_seconds() < SESSION_DURATION

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials = await super(JWTBearer, self).__call__(request)
        
        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization token")
        
        try:
            payload = jwt.decode(
                credentials.credentials,
                os.getenv("SECRET_KEY"),
                algorithms=["HS256"]
            )
            if not check_session_valid(payload.get("sub")):
                raise HTTPException(
                    status_code=401,
                    detail="Session expired. Please login again."
                )
            return credentials.credentials
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            raise HTTPException(
                status_code=403,
                detail="Invalid token or expired token"
            )
