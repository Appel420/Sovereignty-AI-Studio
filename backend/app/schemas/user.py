from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class UserStatus(str, Enum):
    online = "online"
    offline = "offline"


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserStatusUpdate(BaseModel):
    status: UserStatus


class UserStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    status: str
    last_seen: Optional[datetime] = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_verified: bool
    status: str = "offline"
    last_seen: Optional[datetime] = None
    subscription_plan: str
    subscription_expires_at: Optional[datetime]
    total_generations: int
    monthly_generations: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class User(UserInDB):
    pass


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
