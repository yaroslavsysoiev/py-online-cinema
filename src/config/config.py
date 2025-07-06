import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
ACTIVATION_TOKEN_EXPIRE_HOURS = 24
