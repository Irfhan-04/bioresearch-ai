"""
User Management Endpoints
Profile, preferences, API keys, usage statistics
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.core.deps import get_current_active_user, get_db
from app.core.security import (generate_api_key, get_password_hash,
                               hash_api_key, verify_password)
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.token import APIKeyCreate, APIKeyList, APIKeyResponse
from app.schemas.user import (DeleteAccountRequest, PasswordChange, UserPreferences, UserProfile,
                              UserUpdate)

router = APIRouter()


# ============================================================================
# USER PROFILE
# ============================================================================


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get user profile",
    description="Get current user's complete profile",
)
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get current user profile

    Returns complete user information including preferences and usage stats
    """
    return current_user


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Update user profile",
    description="Update user profile information",
)
async def update_user_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user profile

    Can update:
    - full_name
    - email (requires re-verification)
    """

    # Update fields
    if updates.full_name is not None:
        current_user.full_name = updates.full_name

    if updates.email is not None and updates.email != current_user.email:
        # Check if new email already exists
        result = await db.execute(
            select(User).where(User.email == updates.email.lower())
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )

        # Update email and mark as unverified
        current_user.email = updates.email.lower()
        current_user.is_verified = False
        # TODO: Send verification email

    await db.commit()
    await db.refresh(current_user)

    # Clear cache
    cache_key = CacheKey.user_session(str(current_user.id))
    await Cache.delete(cache_key)

    return current_user


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================


@router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change user password",
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change user password

    Requires current password for verification
    """

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    # Clear all sessions (force re-login)
    cache_key = CacheKey.user_session(str(current_user.id))
    await Cache.delete(cache_key)

    return MessageResponse(message="Password changed successfully. Please login again.")


# ============================================================================
# USER PREFERENCES
# ============================================================================


@router.get(
    "/me/preferences",
    response_model=dict,
    summary="Get user preferences",
    description="Get user's preferences",
)
async def get_preferences(current_user: User = Depends(get_current_active_user)):
    """
    Get user preferences

    Returns all user preferences as a dictionary
    """
    return current_user.preferences or {}


@router.put(
    "/me/preferences",
    response_model=dict,
    summary="Update preferences",
    description="Update user preferences",
)
async def update_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user preferences

    Can update:
    - theme (light, dark, auto)
    - email_notifications
    - default_export_format
    - scoring_weights
    """

    # Get current preferences
    current_prefs = current_user.preferences or {}

    # Update with new values (only non-None)
    update_data = preferences.model_dump(exclude_none=True)
    current_prefs.update(update_data)

    # Save
    current_user.preferences = current_prefs
    await db.commit()

    return current_prefs


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================


@router.get(
    "/me/api-keys",
    response_model=List[APIKeyList],
    summary="List API keys",
    description="List all user API keys (without actual keys)",
)
async def list_api_keys(current_user: User = Depends(get_current_active_user)):
    """
    List API keys

    Returns list of API keys without the actual key values
    """

    api_keys = current_user.api_keys or []

    return [
        APIKeyList(
            id=key.get("id"),
            name=key.get("name"),
            prefix=key.get("prefix"),
            created_at=datetime.fromisoformat(key.get("created_at")),
            last_used_at=datetime.fromisoformat(key.get("last_used_at"))
            if key.get("last_used_at")
            else None,
        )
        for key in api_keys
    ]


@router.post(
    "/me/api-keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Generate new API key",
)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new API key

    ⚠️ **Important**: The actual key is only shown once!
    Save it securely, you won't be able to see it again.
    """

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    # Create key metadata
    import uuid

    key_id = str(uuid.uuid4())
    prefix = api_key.split("_")[0] + "_" + api_key.split("_")[1][:4]

    key_metadata = {
        "id": key_id,
        "name": key_data.name,
        "hash": key_hash,
        "prefix": prefix,
        "created_at": datetime.utcnow().isoformat(),
        "last_used_at": None,
    }

    # Add to user's API keys
    api_keys = current_user.api_keys or []
    api_keys.append(key_metadata)
    current_user.api_keys = api_keys

    await db.commit()

    # Return key (only time it's shown!)
    return APIKeyResponse(
        id=key_id,
        name=key_data.name,
        key=api_key,
        prefix=prefix,
        created_at=datetime.utcnow(),
    )


@router.delete(
    "/me/api-keys/{key_id}",
    response_model=MessageResponse,
    summary="Delete API key",
    description="Revoke an API key",
)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete (revoke) an API key

    The key will no longer work for authentication
    """

    # Find and remove key
    api_keys = current_user.api_keys or []

    updated_keys = [key for key in api_keys if key.get("id") != key_id]

    if len(updated_keys) == len(api_keys):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    current_user.api_keys = updated_keys
    await db.commit()

    # Clear cache for this API key
    # Note: Cache keys use the actual API key, not the ID
    # In production, you'd need to track this relationship

    return MessageResponse(message="API key deleted successfully")


# ============================================================================
# ACCOUNT DELETION
# ============================================================================


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
    description="Permanently delete user account",
)
async def delete_account(
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user account

    ⚠️ **Warning**: This action is permanent and cannot be undone.

    Deletes:
    - User account
    - All leads
    - All searches
    - All exports
    - All pipelines

    (Cascade delete handled by database relationships)
    """

    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password. Account deletion cancelled.",
        )

    # In production, you might want to:
    # 1. Require password confirmation
    # 2. Mark as deleted but keep data for X days
    # 3. Send confirmation email

    await db.delete(current_user)
    await db.commit()

    # Clear all caches
    cache_key = CacheKey.user_session(str(current_user.id))
    await Cache.delete(cache_key)

    return None
