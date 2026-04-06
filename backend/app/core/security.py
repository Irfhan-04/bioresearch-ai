"""
Security utilities - JWT, password hashing, API keys
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ============================================================================
# PASSWORD HASHING
# ============================================================================

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against hashed password

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password for storing

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements

    Requirements:
    - At least 8 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains digit
    - Contains special character

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    return True, ""


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in token (usually {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token

    Args:
        data: Data to encode in token (usually {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token data or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Verify token is valid and of correct type

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token data or None if invalid
    """
    payload = decode_token(token)

    if payload is None:
        return None

    # Check token type
    if payload.get("type") != token_type:
        return None

    # Check expiration
    exp = payload.get("exp")
    if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
        return None

    return payload


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user_id from token

    Args:
        token: JWT token string

    Returns:
        User ID or None if invalid
    """
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================


def generate_api_key(prefix: str = "btlg", length: int = 32) -> str:
    """
    Generate a secure API key

    Args:
        prefix: Key prefix (default: "btlg" for Biotech Lead Generator)
        length: Length of random part

    Returns:
        API key string (format: prefix_randomstring)
    """
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage
    Same as password hashing
    """
    return get_password_hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify API key against hashed version
    """
    return verify_password(plain_key, hashed_key)


# ============================================================================
# EMAIL VERIFICATION TOKENS
# ============================================================================


def create_email_verification_token(email: str) -> str:
    """
    Create token for email verification

    Args:
        email: User email address

    Returns:
        Verification token
    """
    data = {"sub": email, "purpose": "email_verification"}
    expires = timedelta(hours=24)  # Token valid for 24 hours

    to_encode = data.copy()
    expire = datetime.utcnow() + expires

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_email_verification_token(token: str) -> Optional[str]:
    """
    Verify email verification token

    Returns:
        Email address or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        if payload.get("purpose") != "email_verification":
            return None

        email = payload.get("sub")
        return email
    except JWTError:
        return None


# ============================================================================
# PASSWORD RESET TOKENS
# ============================================================================


def create_password_reset_token(email: str) -> str:
    """
    Create token for password reset

    Args:
        email: User email address

    Returns:
        Password reset token
    """
    data = {"sub": email, "purpose": "password_reset"}
    expires = timedelta(hours=1)  # Token valid for 1 hour

    to_encode = data.copy()
    expire = datetime.utcnow() + expires

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token

    Returns:
        Email address or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        if payload.get("purpose") != "password_reset":
            return None

        email = payload.get("sub")
        return email
    except JWTError:
        return None


# ============================================================================
# SECURE RANDOM GENERATORS
# ============================================================================


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate cryptographically secure random string

    Args:
        length: Length of string

    Returns:
        Random string
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_verification_code(length: int = 6) -> str:
    """
    Generate numeric verification code

    Args:
        length: Length of code

    Returns:
        Numeric code string
    """
    return "".join(secrets.choice(string.digits) for _ in range(length))


# ============================================================================
# OAUTH STATE TOKENS
# ============================================================================


def create_oauth_state_token() -> str:
    """
    Create state token for OAuth flows
    Prevents CSRF attacks
    """
    return secrets.token_urlsafe(32)


# ============================================================================
# WEBHOOK SIGNATURE VERIFICATION
# ============================================================================

import hashlib
import hmac


def generate_webhook_signature(payload: str, secret: str) -> str:
    """
    Generate HMAC signature for webhook payload

    Args:
        payload: Webhook payload (usually JSON string)
        secret: Webhook secret key

    Returns:
        Hex signature string
    """
    signature = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature

    Args:
        payload: Webhook payload
        signature: Provided signature
        secret: Webhook secret key

    Returns:
        True if signature is valid
    """
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


# Export all
__all__ = [
    # Password
    "verify_password",
    "get_password_hash",
    "validate_password_strength",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    "get_user_id_from_token",
    # API Keys
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    # Email & Password Reset
    "create_email_verification_token",
    "verify_email_verification_token",
    "create_password_reset_token",
    "verify_password_reset_token",
    # Random
    "generate_secure_random_string",
    "generate_verification_code",
    "create_oauth_state_token",
    # Webhooks
    "generate_webhook_signature",
    "verify_webhook_signature",
]
