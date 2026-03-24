from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from app.schemas import (
    BidCreateRequest,
    CategoryCreateRequest,
    CollectionCreateRequest,
    CollectionUpdateRequest,
    CommentCreateRequest,
    ItemCreateRequest,
    ItemUpdateRequest,
    LikeCreateRequest,
    LoginRequest,
    LotCreateRequest,
    RegisterRequest,
    WishlistCreateRequest,
)
from app.services.vault_service import VaultService


class VaultController:
    def __init__(self, service: VaultService) -> None:
        self._service = service
        self.router = APIRouter()
        self._register_routes()

    def _extract_token(self, authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        return authorization.removeprefix("Bearer ").strip()

    def _get_current_user_id(self, authorization: str | None) -> int:
        token = self._extract_token(authorization)
        return self._service.get_user_id_from_token(token)

    def _register_routes(self) -> None:
        self.router.add_api_route("/register", self.register, methods=["POST"], tags=["auth"])
        self.router.add_api_route("/login", self.login, methods=["POST"], tags=["auth"])
        self.router.add_api_route("/auth/me", self.auth_me, methods=["GET"], tags=["auth"])
        self.router.add_api_route("/collections", self.get_collections, methods=["GET"], tags=["collections"])
        self.router.add_api_route("/collections", self.create_collection, methods=["POST"], tags=["collections"])
        self.router.add_api_route("/collections/{collection_id}", self.update_collection, methods=["PUT"], tags=["collections"])
        self.router.add_api_route("/collections/{collection_id}", self.delete_collection, methods=["DELETE"], tags=["collections"])
        self.router.add_api_route("/items", self.get_items, methods=["GET"], tags=["items"])
        self.router.add_api_route("/items", self.create_item, methods=["POST"], tags=["items"])
        self.router.add_api_route("/items/{item_id}", self.update_item, methods=["PUT"], tags=["items"])
        self.router.add_api_route("/items/{item_id}", self.delete_item, methods=["DELETE"], tags=["items"])
        self.router.add_api_route("/categories", self.get_categories, methods=["GET"], tags=["categories"])
        self.router.add_api_route("/categories", self.create_category, methods=["POST"], tags=["categories"])
        self.router.add_api_route("/wishlist", self.get_wishlist, methods=["GET"], tags=["wishlist"])
        self.router.add_api_route("/wishlist", self.create_wishlist, methods=["POST"], tags=["wishlist"])
        self.router.add_api_route("/wishlist/{wishlist_id}", self.delete_wishlist, methods=["DELETE"], tags=["wishlist"])
        self.router.add_api_route("/reports/collection", self.report_collection, methods=["GET"], tags=["reports"])
        self.router.add_api_route("/reports/item", self.report_item, methods=["GET"], tags=["reports"])
        self.router.add_api_route("/reports/category", self.report_category, methods=["GET"], tags=["reports"])
        self.router.add_api_route("/like", self.create_like, methods=["POST"], tags=["social"])
        self.router.add_api_route("/comment", self.create_comment, methods=["POST"], tags=["social"])
        self.router.add_api_route("/comments", self.get_comments, methods=["GET"], tags=["social"])
        self.router.add_api_route("/lot", self.create_lot, methods=["POST"], tags=["auction"])
        self.router.add_api_route("/lots", self.get_lots, methods=["GET"], tags=["auction"])
        self.router.add_api_route("/bid", self.create_bid, methods=["POST"], tags=["auction"])

    def register(self, payload: RegisterRequest) -> dict[str, Any]:
        return self._service.register(payload)

    def login(self, payload: LoginRequest) -> dict[str, str]:
        return self._service.login(payload)

    def auth_me(self, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.auth_me(user_id)

    def get_collections(self, authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user_id = self._get_current_user_id(authorization)
        return self._service.get_collections(user_id)

    def create_collection(self, payload: CollectionCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_collection(user_id, payload)

    def update_collection(
        self,
        collection_id: int,
        payload: CollectionUpdateRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.update_collection(user_id, collection_id, payload)

    def delete_collection(self, collection_id: int, authorization: str | None = Header(default=None)) -> dict[str, bool]:
        user_id = self._get_current_user_id(authorization)
        return self._service.delete_collection(user_id, collection_id)

    def get_items(self, authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user_id = self._get_current_user_id(authorization)
        return self._service.get_items(user_id)

    def create_item(self, payload: ItemCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_item(user_id, payload)

    def update_item(self, item_id: int, payload: ItemUpdateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.update_item(user_id, item_id, payload)

    def delete_item(self, item_id: int, authorization: str | None = Header(default=None)) -> dict[str, bool]:
        user_id = self._get_current_user_id(authorization)
        return self._service.delete_item(user_id, item_id)

    def get_categories(self, authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user_id = self._get_current_user_id(authorization)
        return self._service.get_categories(user_id)

    def create_category(self, payload: CategoryCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_category(user_id, payload.name)

    def get_wishlist(self, authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user_id = self._get_current_user_id(authorization)
        return self._service.get_wishlist(user_id)

    def create_wishlist(self, payload: WishlistCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.add_wishlist(user_id, payload)

    def delete_wishlist(self, wishlist_id: int, authorization: str | None = Header(default=None)) -> dict[str, bool]:
        user_id = self._get_current_user_id(authorization)
        return self._service.delete_wishlist(user_id, wishlist_id)

    def report_collection(
        self,
        collectionId: int,
        fromDate: datetime,
        toDate: datetime,
        authorization: str | None = Header(default=None),
    ) -> list[dict[str, Any]]:
        user_id = self._get_current_user_id(authorization)
        return self._service.report_collection(user_id, collectionId, fromDate, toDate)

    def report_item(self, itemId: int, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.report_item(user_id, itemId)

    def report_category(self, sort: str = "items_count", authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        user_id = self._get_current_user_id(authorization)
        return self._service.report_category(user_id, sort)

    def create_like(self, payload: LikeCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_like(user_id, payload.entity_type, payload.entity_id)

    def create_comment(self, payload: CommentCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_comment(user_id, payload)

    def get_comments(self, entity_type: str, entity_id: int) -> list[dict[str, Any]]:
        return self._service.get_comments(entity_type, entity_id)

    def create_lot(self, payload: LotCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_lot(user_id, payload)

    def get_lots(self) -> list[dict[str, Any]]:
        return self._service.get_lots()

    def create_bid(self, payload: BidCreateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user_id = self._get_current_user_id(authorization)
        return self._service.create_bid(user_id, payload)
