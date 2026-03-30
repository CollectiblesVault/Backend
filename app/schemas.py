from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class ProfileUpdateRequest(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)
    avatar_url: str | None = Field(default=None, max_length=500)


class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class VisibilityUpdateRequest(BaseModel):
    is_public: bool


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)


class CollectionUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)


class ItemCreateRequest(BaseModel):
    collection_id: int
    category_id: int
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0)
    image_url: str | None = Field(default=None, max_length=500)


class ItemUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0)
    image_url: str | None = Field(default=None, max_length=500)


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WishlistCreateRequest(BaseModel):
    item_name: str | None = Field(default=None, max_length=150)
    item_id: int | None = None


class LikeCreateRequest(BaseModel):
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: int


class CommentCreateRequest(BaseModel):
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: int
    text: str = Field(min_length=1, max_length=2000)


class ItemCommentCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class LotCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    start_price: Decimal = Field(gt=0)
    step: Decimal = Field(gt=0)
    end_time: datetime


class BidCreateRequest(BaseModel):
    lot_id: int
    amount: Decimal = Field(gt=0)
