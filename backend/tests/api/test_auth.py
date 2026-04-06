"""
Authentication API Tests
Test user registration, login, password reset, etc.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User

# ============================================================================
# REGISTRATION TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestUserRegistration:
    """Test user registration endpoint"""

    async def test_register_valid_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "ValidPass123!",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "user_id" in data["data"]

        # Verify user created in database
        result = await db_session.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.full_name == "New User"
        assert user.is_verified is False

    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with existing email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "ValidPass123!",
                "full_name": "Duplicate User",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"].lower()

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "ValidPass123!",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422


# ============================================================================
# LOGIN TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestUserLogin:
    """Test user login endpoint"""

    async def test_login_valid_credentials(self, client: AsyncClient, test_user: User):
        """Test successful login"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "TestPass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with incorrect password"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "WrongPassword123!"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "TestPass123!"},
        )

        assert response.status_code == 401

    async def test_login_inactive_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test login with inactive user"""
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            password_hash=verify_password("TestPass123!", "$2b$12$abcdef"),
            full_name="Inactive User",
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "TestPass123!"},
        )

        assert response.status_code == 403


# ============================================================================
# TOKEN REFRESH TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestTokenRefresh:
    """Test token refresh endpoint"""

    async def test_refresh_valid_token(self, client: AsyncClient, test_user: User):
        """Test refreshing with valid refresh token"""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "TestPass123!"},
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refreshing with invalid token"""
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401


# ============================================================================
# LOGOUT TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestLogout:
    """Test logout endpoint"""

    async def test_logout_authenticated(self, client: AsyncClient, auth_headers: dict):
        """Test logout with valid authentication"""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()

    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Test logout without authentication"""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401


# ============================================================================
# GET CURRENT USER TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestGetCurrentUser:
    """Test get current user endpoint"""

    async def test_get_me_authenticated(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test getting current user with valid token"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["subscription_tier"] == test_user.subscription_tier.value

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """Test getting current user without authentication"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


# ============================================================================
# PASSWORD RESET TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestPasswordReset:
    """Test password reset flow"""

    async def test_request_password_reset(self, client: AsyncClient, test_user: User):
        """Test requesting password reset"""
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": test_user.email}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sent" in data["message"].lower()

    async def test_request_password_reset_nonexistent(self, client: AsyncClient):
        """Test requesting password reset for non-existent user"""
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "nonexistent@example.com"}
        )

        # Should still return success (security)
        assert response.status_code == 200


# ============================================================================
# EMAIL VERIFICATION TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.api
class TestEmailVerification:
    """Test email verification flow"""

    async def test_resend_verification(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test resending verification email"""
        # Mark user as unverified
        test_user.is_verified = False
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/resend-verification", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "sent" in data["message"].lower()

    async def test_resend_verification_already_verified(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test resending verification when already verified"""
        response = await client.post(
            "/api/v1/auth/resend-verification", headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "already verified" in data["detail"].lower()
