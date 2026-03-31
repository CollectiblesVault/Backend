from __future__ import annotations

import logging
from csv import DictWriter
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any
from decimal import Decimal

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
    PasswordUpdateRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    VisibilityUpdateRequest,
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

        is_valid, upgraded_hash = self._security_manager.verify_password_and_upgrade_hash(
            payload.password,
            str(user.get("password_hash") or ""),
        )
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if upgraded_hash:
            self._repository.update_user_password(int(user["id"]), upgraded_hash)
        token = self._security_manager.create_access_token(str(user["id"]))
        return {"access_token": token, "token_type": "bearer"}

    def get_user_id_from_token(self, token: str) -> int:
        payload = self._security_manager.decode_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return int(payload["sub"])

    def auth_me(self, user_id: int) -> dict[str, Any]:
        return self._get_user_with_assets(user_id)

    def update_me(self, user_id: int, payload: ProfileUpdateRequest) -> dict[str, Any]:
        if payload.email:
            existing = self._repository.get_user_by_email(payload.email)
            if existing and int(existing["id"]) != user_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        try:
            updated = self._repository.update_user_profile(
                user_id=user_id,
                email=payload.email,
                display_name=payload.display_name,
                bio=payload.bio,
                avatar_url=payload.avatar_url,
            )
            if not updated:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return updated
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists") from None

    def change_password(self, user_id: int, payload: PasswordUpdateRequest) -> dict[str, bool]:
        user = self._repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        stored = self._repository.get_user_by_email(str(user["email"]))

        is_valid, upgraded_hash = self._security_manager.verify_password_and_upgrade_hash(
            payload.current_password,
            str((stored or {}).get("password_hash") or ""),
        )
        if not stored or not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is invalid")
        if upgraded_hash:
            self._repository.update_user_password(user_id, upgraded_hash)
        self._repository.update_user_password(user_id, self._security_manager.hash_password(payload.new_password))
        return {"updated": True}

    def deactivate_me(self, user_id: int) -> dict[str, Any]:
        result = self._repository.deactivate_user(user_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return result

    def get_public_users(self, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._repository.get_public_users(limit=limit, offset=offset)

    def get_public_user(self, user_id: int) -> dict[str, Any]:
        user = self._repository.get_public_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self._get_public_user_with_assets(user_id, base_user=user)

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

    def get_public_collections_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return self._repository.get_public_collections_by_user(user_id)

    def set_collection_visibility(self, user_id: int, collection_id: int, payload: VisibilityUpdateRequest) -> dict[str, Any]:
        result = self._repository.set_collection_visibility(user_id, collection_id, payload.is_public)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
        return result

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

    def get_public_items_by_collection(self, collection_id: int) -> list[dict[str, Any]]:
        return self._repository.get_public_items_by_collection(collection_id)

    def set_item_visibility(self, user_id: int, item_id: int, payload: VisibilityUpdateRequest) -> dict[str, Any]:
        result = self._repository.set_item_visibility(user_id, item_id, payload.is_public)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return result

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

    def create_item_like(self, user_id: int, item_id: int) -> dict[str, Any]:
        like = self._repository.create_item_like(user_id, item_id)
        if not like:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to like this item")
        return like

    def delete_item_like(self, user_id: int, item_id: int) -> dict[str, bool]:
        deleted = self._repository.delete_item_like(user_id, item_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")
        return {"deleted": True}

    def create_item_comment(self, user_id: int, item_id: int, text: str) -> dict[str, Any]:
        comment = self._repository.create_item_comment(user_id, item_id, text)
        if not comment:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to comment this item")
        return comment

    def get_item_comments(self, item_id: int) -> list[dict[str, Any]]:
        return self._repository.get_item_comments(item_id)

    def add_item_to_wishlist(self, user_id: int, item_id: int) -> dict[str, Any]:
        wishlist_item = self._repository.add_item_to_wishlist(user_id, item_id)
        if not wishlist_item:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to add item to wishlist")
        return wishlist_item

    def delete_item_from_wishlist(self, user_id: int, item_id: int) -> dict[str, bool]:
        deleted = self._repository.delete_item_from_wishlist(user_id, item_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist entry not found")
        return {"deleted": True}

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

    def report_summary(self, user_id: int, period: str) -> dict[str, Any]:
        from_date, to_date = self._period_bounds(period)
        summary = self._repository.report_summary(user_id, from_date, to_date)
        summary["period"] = period
        summary["from_date"] = from_date
        summary["to_date"] = to_date
        return summary

    def report_summary_csv(self, user_id: int, period: str) -> str:
        return self._rows_to_csv([self.report_summary(user_id, period)])

    def report_collections_csv(self, user_id: int, from_date: datetime, to_date: datetime) -> str:
        return self._rows_to_csv(self._repository.report_collections_period(user_id, from_date, to_date))

    def report_items_csv(self, user_id: int, from_date: datetime, to_date: datetime) -> str:
        return self._rows_to_csv(self._repository.report_items_period(user_id, from_date, to_date))

    def report_collections(self, user_id: int, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        return self._repository.report_collections_period(user_id, from_date, to_date)

    def report_items(self, user_id: int, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        return self._repository.report_items_period(user_id, from_date, to_date)

    def report_activity(self, user_id: int, period: str) -> dict[str, Any]:
        from_date, to_date = self._period_bounds(period)
        bucket = self._granularity_for_period(period)
        timeseries = self._repository.report_activity(user_id, from_date, to_date, bucket)
        distribution = {
            "collections": sum(int(r.get("collections_count", 0) or 0) for r in timeseries),
            "items": sum(int(r.get("items_count", 0) or 0) for r in timeseries),
            "likes": sum(int(r.get("likes_count", 0) or 0) for r in timeseries),
            "comments": sum(int(r.get("comments_count", 0) or 0) for r in timeseries),
            "wishlist": sum(int(r.get("wishlist_count", 0) or 0) for r in timeseries),
        }
        return {
            "period": period,
            "from_date": from_date,
            "to_date": to_date,
            "bucket": bucket,
            "timeseries": timeseries,
            "distribution": distribution,
        }

    @staticmethod
    def _granularity_for_period(period: str) -> str:
        if period == "week":
            return "day"
        if period == "month":
            return "week"
        if period == "year":
            return "month"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period must be week, month or year")

    def _period_bounds(self, period: str) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        days = {"week": 7, "month": 30, "year": 365}.get(period)
        if not days:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period must be week, month or year")
        return now.replace(microsecond=0) - timedelta(days=days), now.replace(microsecond=0)

    @staticmethod
    def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return ""
        output = StringIO()
        writer = DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    # Aggregation helpers
    def _get_user_with_assets(self, user_id: int, base_user: dict[str, Any] | None = None) -> dict[str, Any]:
        user = base_user or self._repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        collections = self._repository.get_collections(user_id)
        items = self._repository.get_items(user_id)
        total = Decimal("0")
        for item in items:
            price = item.get("price")
            if price is None:
                continue
            total += Decimal(str(price))
        enriched = dict(user)
        enriched["collections"] = collections
        enriched["items"] = items
        enriched["dollars"] = float(total)
        return enriched

    def _get_public_user_with_assets(self, user_id: int, base_user: dict[str, Any] | None = None) -> dict[str, Any]:
        user = base_user or self._repository.get_public_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        collections = self._repository.get_public_collections_by_user(user_id)
        items: list[dict[str, Any]] = []
        for col in collections:
            cid = int(col["id"])
            items.extend(self._repository.get_public_items_by_collection(cid))
        total = Decimal("0")
        for item in items:
            price = item.get("price")
            if price is None:
                continue
            total += Decimal(str(price))
        enriched = dict(user)
        enriched["collections"] = collections
        enriched["items"] = items
        enriched["dollars"] = float(total)
        return enriched
