"""
Authentication Endpoints
User registration, login, logout, password reset
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.core.config import settings
from app.core.deps import get_current_active_user, get_current_user, get_db
from app.core.security import (create_access_token,
                               create_email_verification_token,
                               create_password_reset_token,
                               create_refresh_token, get_password_hash,
                               verify_email_verification_token,
                               verify_password, verify_password_reset_token,
                               verify_token)
from app.models.user import User
from app.schemas.base import MessageResponse, SuccessResponse
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import (PasswordReset, PasswordResetRequest, UserLogin,
                              UserProfile, UserRegister)
from app.services.email_service import get_email_service

router = APIRouter()


# ============================================================================
# USER REGISTRATION
# ============================================================================


@router.post(
    "/register",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password",
)
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account

    - **email**: Valid email address (will be lowercased)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **full_name**: User's full name

    Returns:
    - Success message with user ID
    - Sends verification email in background
    """

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    new_user = User(
        email=user_data.email.lower(),
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False,  # Requires email verification
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send welcome email (non-blocking — never prevents registration)
    try:
        email_service = get_email_service()
        await email_service.send_welcome_email(
            to_email=new_user.email,
            user_name=new_user.full_name or new_user.email.split("@")[0],
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Welcome email failed for {new_user.email}: {e}")

    # Generate verification token
    verification_token = create_email_verification_token(new_user.email)

    # Send verification email (background task)
    background_tasks.add_task(
        send_verification_email,
        email=new_user.email,
        token=verification_token,
        name=new_user.full_name,
    )

    return SuccessResponse(
        message="User registered successfully. Please check your email to verify your account.",
        data={"user_id": str(new_user.id)},
    )


# ============================================================================
# USER LOGIN
# ============================================================================


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticate user and return JWT tokens",
)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return access & refresh tokens

    - **email**: User's email address
    - **password**: User's password

    Returns:
    - **access_token**: JWT token for API requests (24h expiration)
    - **refresh_token**: Token to get new access token (7d expiration)
    - **token_type**: Always "bearer"
    - **expires_in**: Seconds until access token expires
    """

    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email.lower())
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )

    # Update last login time
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Cache user session
    cache_key = CacheKey.user_session(str(user.id))
    await Cache.set(
        cache_key,
        {
            "email": user.email,
            "subscription_tier": user.subscription_tier.value,
            "logged_in_at": datetime.utcnow().isoformat(),
        },
        ttl=settings.REDIS_SESSION_TTL,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================================================
# REFRESH TOKEN
# ============================================================================


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """
    Get new access token using refresh token

    - **refresh_token**: Valid refresh token from login

    Returns:
    - New access token with same expiration time
    - Same refresh token (can be used multiple times)
    """

    # Verify refresh token
    token_data = verify_token(request.refresh_token, token_type="refresh")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user_id = token_data.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================================================
# LOGOUT
# ============================================================================


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
    description="Logout user and invalidate session",
)
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout current user

    Clears user session from cache.
    Note: JWTs are stateless, so tokens remain valid until expiration.
    For true token revocation, implement token blacklist.
    """

    # Clear session cache
    cache_key = CacheKey.user_session(str(current_user.id))
    await Cache.delete(cache_key)

    return MessageResponse(message="Logged out successfully")


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================


@router.get(
    "/verify-email/{token}",
    response_model=MessageResponse,
    summary="Verify email address",
    description="Verify user email with token from email",
)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify user email address

    - **token**: Verification token from email

    Users receive this link via email after registration.
    """

    # Verify token and extract email
    email = verify_email_verification_token(token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Find user
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.is_verified:
        return MessageResponse(message="Email already verified")

    # Mark as verified
    user.is_verified = True
    await db.commit()

    return MessageResponse(
        message="Email verified successfully! You can now access all features."
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    description="Send new verification email to user",
)
async def resend_verification(
    background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)
):
    """
    Resend email verification link

    For users who didn't receive or lost their verification email.
    """

    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified"
        )

    # Generate new token
    verification_token = create_email_verification_token(current_user.email)

    # Send email
    background_tasks.add_task(
        send_verification_email,
        email=current_user.email,
        token=verification_token,
        name=current_user.full_name,
    )

    return MessageResponse(message="Verification email sent. Please check your inbox.")


# ============================================================================
# PASSWORD RESET
# ============================================================================


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset email to user",
)
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset email

    - **email**: User's email address

    Sends password reset link to email if account exists.
    Always returns success to prevent email enumeration.
    """

    # Find user (but don't reveal if they exist)
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Generate reset token
        reset_token = create_password_reset_token(user.email)

        # Send reset email
        background_tasks.add_task(
            send_password_reset_email,
            email=user.email,
            token=reset_token,
            name=user.full_name,
        )

    # Always return success (security: don't reveal if email exists)
    return MessageResponse(
        message="If an account exists with that email, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
    description="Reset user password using token from email",
)
async def reset_password(request: PasswordReset, db: AsyncSession = Depends(get_db)):
    """
    Reset password with token from email

    - **token**: Reset token from email
    - **new_password**: New password (must meet strength requirements)
    """

    # Verify token
    email = verify_password_reset_token(request.token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Find user
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update password
    user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    # Clear all sessions (force re-login)
    cache_key = CacheKey.user_session(str(user.id))
    await Cache.delete(cache_key)

    return MessageResponse(
        message="Password reset successfully. Please login with your new password."
    )


# ============================================================================
# GET CURRENT USER PROFILE
# ============================================================================


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description="Get authenticated user's profile information",
)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user's profile

    Requires authentication via Bearer token or API key.
    """
    return current_user


# ============================================================================
# BACKGROUND TASKS (Email Sending)
# ============================================================================


async def send_verification_email(email: str, token: str, name: str):
    """
    Send email verification email

    In production, use actual email service (Resend, SendGrid, etc.)
    """
    # TODO: Implement actual email sending
    # For now, just log the token
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    print(f"\n{'='*60}")
    print(f"EMAIL VERIFICATION")
    print(f"{'='*60}")
    print(f"To: {email}")
    print(f"Subject: Verify your email address")
    print(f"\nHi {name},")
    print(f"\nPlease verify your email by clicking this link:")
    print(f"{verification_url}")
    print(f"\nThis link expires in 24 hours.")
    print(f"{'='*60}\n")


async def send_password_reset_email(email: str, token: str, name: str):
    """
    Send password reset email

    In production, use actual email service
    """
    # TODO: Implement actual email sending
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    print(f"\n{'='*60}")
    print(f"PASSWORD RESET")
    print(f"{'='*60}")
    print(f"To: {email}")
    print(f"Subject: Reset your password")
    print(f"\nHi {name},")
    print(f"\nReset your password by clicking this link:")
    print(f"{reset_url}")
    print(f"\nThis link expires in 1 hour.")
    print(f"\nIf you didn't request this, please ignore this email.")
    print(f"{'='*60}\n")
