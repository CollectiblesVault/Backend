from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from psycopg import IntegrityError

from app.core.security import SecurityManager
from app.db.repository import VaultRepository
from app.schemas import (
    BidCreateRequest,
    CollectionCreateRequest,
    CollectionUpdateRequest,
    CommentCreateRequest,
    ItemCreateRequest,
    ItemUpdateRequest,
    LoginRequest,
    LotCreateRequest,
    RegisterRequest,
    WishlistCreateRequest,
)

logger = logging.getLogger(__name__)


class VaultService:
    def __init__(self, repository: VaultRepository, security_manager: SecurityManager) -> None:
        self._repository = repository
        self._security_manager = security_manager

    def register(self, payload: RegisterRequest) -> dict[str, Any]:
        existing_user = self._repository.get_user_by_email(payload.email)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        try:
            hashed_password = self._security_manager.hash_password(payload.password)
            user = self._repository.create_user(payload.email, hashed_password)
            if not user or user.get("id") is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User creation failed",
                )
            uid = int(user["id"])
            self._repository.create_default_categories(uid)
            token = self._security_manager.create_access_token(str(uid))
            return {"user": user, "access_token": token, "token_type": "bearer"}
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists") from None
        except HTTPException:
            raise
        except Exception:
            logger.exception("register failed for %s", payload.email)
            raise

    def login(self, payload: LoginRequest) -> dict[str, Any]:
        user = self._repository.get_user_by_email(payload.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not self._security_manager.verify_password(payload.password, str(user["password_hash"])):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = self._security_manager.create_access_token(str(user["id"]))
        return {"access_token": token, "token_type": "bearer"}

    def get_user_id_from_token(self, token: str) -> int:
        payload = self._security_manager.decode_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return int(payload["sub"])

    def auth_me(self, user_id: int) -> dict[str, Any]:
        user = self._repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def get_collections(self, user_id: int) -> list[dict[str, Any]]:
        return self._repository.get_collections(user_id)

    def create_collection(self, user_id: int, payload: CollectionCreateRequest) -> dict[str, Any]:
        return self._repository.create_collection(user_id, payload.name, payload.description)

    def update_collection(self, user_id: int, collection_id: int, payload: CollectionUpdateRequest) -> dict[str, Any]:
        result = self._repository.update_collection(user_id, collection_id, payload.name, payload.description)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
        return result

    def delete_collection(self, user_id: int, collection_id: int) -> dict[str, bool]:
        is_deleted = self._repository.delete_collection(user_id, collection_id)
        if not is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
        return {"deleted": True}

    def get_items(self, user_id: int) -> list[dict[str, Any]]:
        return self._repository.get_items(user_id)

    def create_item(self, user_id: int, payload: ItemCreateRequest) -> dict[str, Any]:
        return self._repository.create_item(
            user_id,
            payload.collection_id,
            payload.category_id,
            payload.name,
            payload.description,
            payload.price,
            payload.image_url,
        )

    def update_item(self, user_id: int, item_id: int, payload: ItemUpdateRequest) -> dict[str, Any]:
        result = self._repository.update_item(
            user_id,
            item_id,
            payload.name,
            payload.description,
            payload.price,
            payload.image_url,
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return result

    def delete_item(self, user_id: int, item_id: int) -> dict[str, bool]:
        is_deleted = self._repository.delete_item(user_id, item_id)
        if not is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return {"deleted": True}

    def get_categories(self, user_id: int) -> list[dict[str, Any]]:
        return self._repository.get_categories(user_id)

    def create_category(self, user_id: int, name: str) -> dict[str, Any]:
        return self._repository.create_category(user_id, name)

    def get_wishlist(self, user_id: int) -> list[dict[str, Any]]:
        return self._repository.get_wishlist(user_id)

    def add_wishlist(self, user_id: int, payload: WishlistCreateRequest) -> dict[str, Any]:
        if not payload.item_name and not payload.item_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="item_name or item_id is required")
        return self._repository.add_wishlist(user_id, payload.item_name, payload.item_id)

    def delete_wishlist(self, user_id: int, wishlist_id: int) -> dict[str, bool]:
        is_deleted = self._repository.delete_wishlist(user_id, wishlist_id)
        if not is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist entry not found")
        return {"deleted": True}

    def create_like(self, user_id: int, entity_type: str, entity_id: int) -> dict[str, Any]:
        return self._repository.create_like(user_id, entity_type, entity_id)

    def create_comment(self, user_id: int, payload: CommentCreateRequest) -> dict[str, Any]:
        return self._repository.create_comment(user_id, payload.entity_type, payload.entity_id, payload.text)

    def get_comments(self, entity_type: str, entity_id: int) -> list[dict[str, Any]]:
        return self._repository.get_comments(entity_type, entity_id)

    def create_lot(self, user_id: int, payload: LotCreateRequest) -> dict[str, Any]:
        if payload.end_time <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be in future")
        return self._repository.create_lot(
            user_id,
            payload.name,
            payload.description,
            payload.start_price,
            payload.step,
            payload.end_time,
        )

    def get_lots(self) -> list[dict[str, Any]]:
        self._repository.close_expired_lots()
        return self._repository.get_lots()

    def create_bid(self, user_id: int, payload: BidCreateRequest) -> dict[str, Any]:
        lot = self._repository.get_lot(payload.lot_id)
        if not lot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found")
        if lot["status"] != "open":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lot is closed")

        top_bid = self._repository.get_top_bid(payload.lot_id)
        min_amount = top_bid["amount"] + lot["step"] if top_bid else lot["start_price"]
        if payload.amount < min_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid must be at least {min_amount}",
            )
        return self._repository.create_bid(payload.lot_id, user_id, payload.amount)

    def report_collection(self, user_id: int, collection_id: int, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        return self._repository.report_collection(user_id, collection_id, from_date, to_date)

    def report_item(self, user_id: int, item_id: int) -> dict[str, Any]:
        result = self._repository.report_item(user_id, item_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return result

    def report_category(self, user_id: int, sort_by: str) -> list[dict[str, Any]]:
        return self._repository.report_category(user_id, sort_by=sort_by)
