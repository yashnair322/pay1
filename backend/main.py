
from fastapi import FastAPI, HTTPException, Request, Depends, WebSocket
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from jose import JWTError, jwt
import psycopg2
import os
import secrets
import random
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from fastapi.responses import HTMLResponse

# Importing modules from backend
from backend import main2
from backend.main2 import router
from backend.auth import get_current_user, login_user, create_access_token, get_password_hash, verify_password

# Load environment variables
load_dotenv()

# FastAPI App
app = FastAPI()
app.include_router(router)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    return response

# Store verification codes temporarily
verification_codes = {}

# Security and JWT setup
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Use connection pooling
from backend.db import DatabasePool

def get_db():
    conn = DatabasePool.get_connection()
    try:
        yield conn
    finally:
        DatabasePool.return_connection(conn)

# Ensure required tables exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(200) NOT NULL,
        is_verified BOOLEAN DEFAULT FALSE,
        subscription_status BOOLEAN DEFAULT FALSE,
        subscription_plan VARCHAR(20) DEFAULT 'free'
    );
    """
)
conn.commit()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS bots (
        id SERIAL PRIMARY KEY,
        bot_name VARCHAR(100) NOT NULL,
        exchange VARCHAR(50) NOT NULL,
        symbol VARCHAR(50) NOT NULL,
        quantity FLOAT NOT NULL,
        email VARCHAR(100) NOT NULL,
        email_password VARCHAR(200) NOT NULL,
        imap_server VARCHAR(100) NOT NULL,
        email_subject VARCHAR(200) NOT NULL,
        api_key VARCHAR(200),
        api_secret VARCHAR(200),
        account_id VARCHAR(100),
        user_email VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paused BOOLEAN DEFAULT FALSE,
        UNIQUE(bot_name, user_email)
    );
    """
)
conn.commit()

# Utility Functions
def send_reset_email(email: str, reset_link: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg.set_content(f"Click the link to reset your password: {reset_link}\n\nThis link will expire in 15 minutes.")
    msg["Subject"] = "Password Reset Request"
    msg["From"] = smtp_user
    msg["To"] = email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    "free": {
        "bot_limit": 1,
        "trade_limit": 4
    },
    "basic": {
        "bot_limit": 5,
        "trade_limit": -1  # unlimited
    },
    "premium": {
        "bot_limit": 6,
        "trade_limit": -1  # unlimited
    }
}

# Pydantic Models
class User(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str = Field(..., min_length=8, pattern=r"^[A-Za-z\d@$!%*?&]+$")

class VerifyCode(BaseModel):
    email: str
    code: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

# Email Verification
def send_verification_email(email: str, code: str):
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        msg = EmailMessage()
        msg.set_content(f"Your verification code is: {code}\n\nThis code will expire in 10 minutes.")
        msg["Subject"] = "Email Verification Code"
        msg["From"] = smtp_user
        msg["To"] = email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send verification email.")

# Serve Static Files and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
def signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/create-bot", response_class=HTMLResponse)
def create_bot(request: Request):
    return templates.TemplateResponse("create_bot.html", {"request": request})

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})

@app.get("/subscription", response_class=HTMLResponse)
def subscription_page(request: Request):
    return templates.TemplateResponse("subscription.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

from fastapi.responses import JSONResponse
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def get_cached_user_profile(email: str, timestamp: int):
    conn = DatabasePool.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT first_name, last_name, email, subscription_status, subscription_plan,
               (SELECT end_date FROM subscriptions WHERE user_email = users.email ORDER BY end_date DESC LIMIT 1) as subscription_end_date
        FROM users WHERE email = %s
    """, (current_user["email"],))
    user_data = cursor.fetchone()
    
    return {
        "first_name": user_data[0],
        "last_name": user_data[1],
        "email": user_data[2],
        "subscription_status": user_data[3],
        "subscription_plan": user_data[4],
        "subscription_end_date": user_data[5]
    }

@app.post("/api/2fa/setup")
async def setup_2fa(current_user: dict = Depends(get_current_user)):
    # Generate 2FA secret and QR code
    import pyotp
    import qrcode
    import base64
    from io import BytesIO
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(current_user["email"], issuer_name="TradeBot")
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert QR code to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code = base64.b64encode(buffered.getvalue()).decode()
    
    # Store secret temporarily (you should implement proper storage)
    return {"qr_code": f"data:image/png;base64,{qr_code}", "secret": secret}

@app.get("/check-subscription-status")
async def check_subscription_status(current_user: dict = Depends(get_current_user)):
    # For now, returning mock data. You'll need to implement actual subscription check logic
    cursor.execute("SELECT subscription_status FROM users WHERE email = %s", (current_user["email"],))
    result = cursor.fetchone()
    return {"active": result[0] if result else False}

@app.get("/create-subscription-payment/{plan_id}")
def create_subscription_payment(plan_id: str):
    from backend.payment import create_payment_intent, SUBSCRIPTION_PLANS
    return create_payment_intent(plan_id)

@app.post("/verify-payment")
async def verify_payment(payment_data: dict, current_user: dict = Depends(get_current_user)):
    try:
        # Insert subscription record
        cursor.execute("""
            INSERT INTO subscriptions (user_email, plan_id, status, end_date, payment_id, amount)
            VALUES (%s, %s, %s, NOW() + INTERVAL '30 days', %s, %s)
        """, (
            current_user["email"],
            payment_data["plan_id"],
            'active',
            payment_data["payment_id"],
            payment_data["amount"]
        ))
        
        # Update user's subscription status
        cursor.execute("""
            UPDATE users 
            SET subscription_status = TRUE, 
                subscription_plan = %s 
            WHERE email = %s
        """, (payment_data["plan_id"], current_user["email"]))
        
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-payment")
def verify_payment(payment_data: dict):
    # Implement payment verification logic here
    return {"success": True}

@app.get("/activate-free-plan")
async def activate_free_plan(current_user: dict = Depends(get_current_user)):
    try:
        cursor.execute(
            "UPDATE users SET subscription_status = TRUE, subscription_plan = 'free' WHERE email = %s",
            (current_user["email"],)
        )
        conn.commit()
        return {"success": True, "message": "Free plan activated successfully!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.post("/signup")
def signup(user: User):
    cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
    existing_user = cursor.fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists.")
    
    verification_code = str(random.randint(100000, 999999))
    verification_codes[user.email] = {
        "code": verification_code,
        "user_data": user.dict()
    }
    send_verification_email(user.email, verification_code)
    return {"message": "Verification code sent to your email."}

@app.post("/verify-email")
def verify_email(data: VerifyCode):
    if data.email in verification_codes:
        stored_data = verification_codes[data.email]
        if stored_data["code"] == data.code:
            user_data = stored_data["user_data"]
            hashed_password = get_password_hash(user_data['password'])

            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password, is_verified) VALUES (%s, %s, %s, %s, %s)",
                (user_data['first_name'], user_data['last_name'], user_data['email'], hashed_password, True)
            )
            conn.commit()
            del verification_codes[data.email]
            return {"message": "Email verified successfully."}
        else:
            raise HTTPException(status_code=400, detail="Invalid verification code.")
    raise HTTPException(status_code=400, detail="Verification code not found or expired.")

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return login_user(form_data)

@app.post("/forgot-password")
def forgot_password(request: Request, data: VerifyCode):
    cursor.execute("SELECT id, email FROM users WHERE email = %s", (data.email,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    reset_token = create_access_token(data={"sub": data.email}, expires_delta=timedelta(minutes=15))
    reset_link = f"{request.url.scheme}://{request.headers.get('host')}/reset-password?token={reset_token}"
    send_reset_email(data.email, reset_link)
    return {"message": "Password reset link sent."}

@app.post("/reset-password")
def reset_password(data: VerifyCode):
    try:
        payload = jwt.decode(data.code, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid reset token")
        
        hashed_password = get_password_hash(data.code)
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()
        return {"message": "Password reset successful."}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

# Start the FastAPI application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4,
        limit_concurrency=100,
        timeout_keep_alive=30
    )
