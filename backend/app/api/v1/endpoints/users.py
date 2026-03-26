from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_database, get_current_active_user
from app.services.user_service import get_user_by_id, update_user, update_user_status
from app.schemas.user import User, UserUpdate, UserStatusUpdate, UserStatusResponse
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/me", response_model=User)
async def get_current_user(
    current_user: UserModel = Depends(get_current_active_user),
):
    """Retrieve the currently authenticated user's profile.

    Endpoint to get the complete profile information of the currently
    logged-in user.

    Args:
        current_user (UserModel): Automatically injected authenticated user
            from the get_current_active_user dependency

    Returns:
        User: Pydantic model containing the user's profile information

    Raises:
        HTTPException: 401 if not authenticated (handled by dependency)

    Note:
        - Requires authentication
        - Returns full user profile
        - Uses Pydantic model for response serialization

    Example Response:
        {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "is_active": true
        }
    """
    return current_user


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_database),
):
    """Update the currently authenticated user's profile information.

    Allows users to modify their profile details such as full name,
    bio, or avatar URL.

    Args:
        user_update (UserUpdate): Pydantic model containing the fields to update
        current_user (UserModel): Automatically injected authenticated user
        db (Session): SQLAlchemy database session

    Returns:
        User: Updated user profile information

    Raises:
        HTTPException:
            - 401 if not authenticated (handled by dependency)
            - 400 if update operation fails

    Note:
        - Requires authentication
        - Only allows updating permitted fields
        - Automatically updates 'updated_at' timestamp
        - Returns complete updated profile

    Example Request:
        PUT /api/v1/users/me
        {
            "full_name": "John Smith",
            "bio": "Python developer"
        }
    """
    updated_user = update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update user"
        )
    return updated_user


@router.get("/me/stats")
async def get_user_stats(
    current_user: UserModel = Depends(get_current_active_user),
):
    """Retrieve usage statistics and subscription information for the current user.

    Provides detailed information about the user's platform usage,
    including generation counts, subscription status, and account history.

    Args:
        current_user (UserModel): Automatically injected authenticated user

    Returns:
        dict: Dictionary containing various usage statistics and account information

    Raises:
        HTTPException: 401 if not authenticated (handled by dependency)
    """
    return {
        "total_generations": current_user.total_generations,
        "monthly_generations": current_user.monthly_generations,
        "subscription_plan": current_user.subscription_plan,
        "subscription_expires_at": current_user.subscription_expires_at,
        "account_created": current_user.created_at,
        "last_login": current_user.last_login,
    }


@router.put("/me/status", response_model=UserStatusResponse)
async def update_my_status(
    status_update: UserStatusUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_database),
):
    """Update the current user's online/offline status.

    Args:
        status_update (UserStatusUpdate): The new status (online or offline)
        current_user (UserModel): Automatically injected authenticated user
        db (Session): SQLAlchemy database session

    Returns:
        UserStatusResponse: Updated status information

    Raises:
        HTTPException: 400 if the status update fails
    """
    updated = update_user_status(db, current_user.id, status_update.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update status",
        )
    return UserStatusResponse(
        user_id=updated.id,
        username=updated.username,
        status=updated.status,
        last_seen=updated.last_seen,
    )


@router.get("/me/status", response_model=UserStatusResponse)
async def get_my_status(
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get the current user's online/offline status.

    Returns:
        UserStatusResponse: Current status information
    """
    return UserStatusResponse(
        user_id=current_user.id,
        username=current_user.username,
        status=current_user.status or "offline",
        last_seen=current_user.last_seen,
    )


@router.get("/{user_id}", response_model=User)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_database),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Retrieve a user's public profile information by their ID.

    Args:
        user_id (int): The ID of the user to retrieve
        db (Session): SQLAlchemy database session
        current_user (UserModel): Authenticated user making the request

    Returns:
        User: Public profile information of the requested user

    Raises:
        HTTPException: 404 if requested user not found
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/{user_id}/status", response_model=UserStatusResponse)
async def get_user_status(
    user_id: int,
    db: Session = Depends(get_database),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get a specific user's online/offline status by their ID.

    Args:
        user_id (int): The ID of the user to check
        db (Session): SQLAlchemy database session
        current_user (UserModel): Authenticated user making the request

    Returns:
        UserStatusResponse: The user's current status information

    Raises:
        HTTPException: 404 if the user is not found
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserStatusResponse(
        user_id=user.id,
        username=user.username,
        status=user.status or "offline",
        last_seen=user.last_seen,
    )
