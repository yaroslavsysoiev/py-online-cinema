import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)
