import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional


# ==================== Request Models ====================

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


# ==================== Routes ====================

def register_routes(app: FastAPI):
    """Register user routes."""
    
    @app.post("/api/users/register")
    async def register_user(request: UserRegisterRequest):
        """Register a new user account."""
        from database import get_db_connection
        from utils import hash_password
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (request.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        password_hash = hash_password(request.password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, created_at)
            VALUES (?, ?, ?, ?)
        """, (request.email, password_hash, request.name or request.email.split("@")[0],
              datetime.now(timezone.utc).isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"user_id": user_id, "message": "Registration successful"}
    
    @app.post("/api/users/login")
    async def login_user(request: UserLoginRequest):
        """Login and get session token."""
        from database import get_db_connection
        from utils import verify_password
        from services import _create_user_session
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (request.email,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not verify_password(request.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = _create_user_session(row["id"])
        
        return {
            "token": token,
            "user_id": row["id"],
            "message": "Login successful",
        }
    
    @app.get("/api/users/me")
    async def get_current_user(authorization: Optional[str] = Header(None)):
        """Get current user info."""
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required")
        
        from services import _get_user_by_token
        
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        user = _get_user_by_token(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "user_id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
        }
    
    @app.post("/api/users/password-reset")
    async def request_password_reset(request: PasswordResetRequest):
        """Request password reset."""
        # In production, send email with reset link
        return {"message": "If email exists, reset instructions will be sent"}
