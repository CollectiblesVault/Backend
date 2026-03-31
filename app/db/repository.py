from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.db.database import Database


class VaultRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @staticmethod
    def _map_rows(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description or []]
                return self._map_rows(columns, cursor.fetchall())

    def _fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [col[0] for col in cursor.description or []]
                return dict(zip(columns, row, strict=False))

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

    def create_user(self, email: str, hashed_password: str) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
            RETURNING id, email, created_at
            """,
            (email, hashed_password),
        ) or {}

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT id, email, password_hash, display_name, bio, avatar_url, is_public, is_active, created_at, updated_at
            FROM users
            WHERE email = %s
            """,
            (email,),
        )

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT id, email, display_name, bio, avatar_url, is_public, is_active, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )

    def update_user_profile(
        self,
        user_id: int,
        email: str | None,
        display_name: str | None,
        bio: str | None,
        avatar_url: str | None,
    ) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            UPDATE users
            SET
                email = COALESCE(%s, email),
                display_name = COALESCE(%s, display_name),
                bio = COALESCE(%s, bio),
                avatar_url = COALESCE(%s, avatar_url),
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, email, display_name, bio, avatar_url, is_public, is_active, created_at, updated_at
            """,
            (email, display_name, bio, avatar_url, user_id),
        )

    def update_user_password(self, user_id: int, hashed_password: str) -> None:
        self._execute(
            """
            UPDATE users
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (hashed_password, user_id),
        )

    def deactivate_user(self, user_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            UPDATE users
            SET is_active = FALSE, deactivated_at = NOW(), updated_at = NOW()
            WHERE id = %s
            RETURNING id, email, is_active, deactivated_at
            """,
            (user_id,),
        )

    def get_public_users(self, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT id, email, display_name, bio, avatar_url, created_at
            FROM users
            WHERE is_active = TRUE AND is_public = TRUE
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

    def get_public_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT id, email, display_name, bio, avatar_url, created_at
            FROM users
            WHERE id = %s AND is_active = TRUE AND is_public = TRUE
            """,
            (user_id,),
        )

    def create_default_categories(self, user_id: int) -> None:
        default_names = ["Coins", "Stamps", "Cards", "Figures", "Antiques"]
        for category_name in default_names:
            self._execute(
                "INSERT INTO categories (user_id, name) VALUES (%s, %s)",
                (user_id, category_name),
            )

    def get_categories(self, user_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            "SELECT id, user_id, name, created_at FROM categories WHERE user_id = %s ORDER BY id",
            (user_id,),
        )

    def create_category(self, user_id: int, name: str) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO categories (user_id, name)
            VALUES (%s, %s)
            RETURNING id, user_id, name, created_at
            """,
            (user_id, name),
        ) or {}

    def get_collections(self, user_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            "SELECT id, user_id, name, description, is_public, updated_at, created_at FROM collections WHERE user_id = %s ORDER BY id",
            (user_id,),
        )

    def get_public_collections_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT c.id, c.user_id, c.name, c.description, c.is_public, c.updated_at, c.created_at
            FROM collections c
            JOIN users u ON u.id = c.user_id
            WHERE c.user_id = %s AND c.is_public = TRUE AND u.is_active = TRUE AND u.is_public = TRUE
            ORDER BY c.id
            """,
            (user_id,),
        )

    def create_collection(self, user_id: int, name: str, description: str | None) -> dict[str, Any]:
        result = self._fetch_one(
            """
            INSERT INTO collections (user_id, name, description)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, name, description, is_public, updated_at, created_at
            """,
            (user_id, name, description),
        ) or {}
        self.create_change_event(user_id, "collection", int(result["id"]), "create", None, str(result))
        return result

    def update_collection(self, user_id: int, collection_id: int, name: str, description: str | None) -> dict[str, Any] | None:
        old_row = self._fetch_one("SELECT * FROM collections WHERE id = %s AND user_id = %s", (collection_id, user_id))
        if not old_row:
            return None
        updated_row = self._fetch_one(
            """
            UPDATE collections
            SET name = %s, description = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, name, description, is_public, updated_at, created_at
            """,
            (name, description, collection_id, user_id),
        )
        self.create_change_event(user_id, "collection", collection_id, "update", str(old_row), str(updated_row))
        return updated_row

    def delete_collection(self, user_id: int, collection_id: int) -> bool:
        old_row = self._fetch_one("SELECT * FROM collections WHERE id = %s AND user_id = %s", (collection_id, user_id))
        if not old_row:
            return False
        self._execute("DELETE FROM collections WHERE id = %s AND user_id = %s", (collection_id, user_id))
        self.create_change_event(user_id, "collection", collection_id, "delete", str(old_row), None)
        return True

    def set_collection_visibility(self, user_id: int, collection_id: int, is_public: bool) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            UPDATE collections
            SET is_public = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, name, description, is_public, updated_at, created_at
            """,
            (is_public, collection_id, user_id),
        )

    def get_items(self, user_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT i.id, i.collection_id, i.category_id, i.name, i.description, i.price, i.image_url, i.created_at
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            WHERE c.user_id = %s
            ORDER BY i.id
            """,
            (user_id,),
        )

    def get_public_items_by_collection(self, collection_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT i.id, i.collection_id, i.category_id, i.name, i.description, i.price, i.image_url, i.is_public, i.created_at
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            JOIN users u ON u.id = c.user_id
            WHERE i.collection_id = %s
              AND c.is_public = TRUE
              AND u.is_active = TRUE
              AND u.is_public = TRUE
            ORDER BY i.id
            """,
            (collection_id,),
        )

    def create_item(
        self,
        user_id: int,
        collection_id: int,
        category_id: int,
        name: str,
        description: str | None,
        price: Decimal,
        image_url: str | None,
    ) -> dict[str, Any]:
        result = self._fetch_one(
            """
            INSERT INTO items (collection_id, category_id, name, description, price, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, collection_id, category_id, name, description, price, image_url, created_at
            """,
            (collection_id, category_id, name, description, price, image_url),
        ) or {}
        self.create_change_event(user_id, "item", int(result["id"]), "create", None, str(result))
        return result

    def update_item(
        self,
        user_id: int,
        item_id: int,
        name: str,
        description: str | None,
        price: Decimal,
        image_url: str | None,
    ) -> dict[str, Any] | None:
        old_row = self._fetch_one(
            """
            SELECT i.* FROM items i
            JOIN collections c ON c.id = i.collection_id
            WHERE i.id = %s AND c.user_id = %s
            """,
            (item_id, user_id),
        )
        if not old_row:
            return None
        updated_row = self._fetch_one(
            """
            UPDATE items
            SET name = %s, description = %s, price = %s, image_url = %s
            WHERE id = %s
            RETURNING id, collection_id, category_id, name, description, price, image_url, is_public, created_at
            """,
            (name, description, price, image_url, item_id),
        )
        self.create_change_event(user_id, "item", item_id, "update", str(old_row), str(updated_row))
        return updated_row

    def delete_item(self, user_id: int, item_id: int) -> bool:
        old_row = self._fetch_one(
            """
            SELECT i.* FROM items i
            JOIN collections c ON c.id = i.collection_id
            WHERE i.id = %s AND c.user_id = %s
            """,
            (item_id, user_id),
        )
        if not old_row:
            return False
        self._execute("DELETE FROM items WHERE id = %s", (item_id,))
        self.create_change_event(user_id, "item", item_id, "delete", str(old_row), None)
        return True

    def set_item_visibility(self, user_id: int, item_id: int, is_public: bool) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            UPDATE items i
            SET is_public = %s
            FROM collections c
            WHERE i.id = %s AND c.id = i.collection_id AND c.user_id = %s
            RETURNING i.id, i.collection_id, i.category_id, i.name, i.description, i.price, i.image_url, i.is_public, i.created_at
            """,
            (is_public, item_id, user_id),
        )

    def get_wishlist(self, user_id: int) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT id, user_id, item_name, item_id, created_at FROM wishlists WHERE user_id = %s", (user_id,))

    def add_wishlist(self, user_id: int, item_name: str | None, item_id: int | None) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO wishlists (user_id, item_name, item_id)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, item_name, item_id, created_at
            """,
            (user_id, item_name, item_id),
        ) or {}

    def add_item_to_wishlist(self, user_id: int, item_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            INSERT INTO wishlists (user_id, item_name, item_id)
            SELECT %s, i.name, i.id
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            JOIN users u ON u.id = c.user_id
            WHERE i.id = %s AND c.is_public = TRUE AND u.is_active = TRUE AND u.is_public = TRUE
            ON CONFLICT DO NOTHING
            RETURNING id, user_id, item_name, item_id, created_at
            """,
            (user_id, item_id),
        )

    def delete_wishlist(self, user_id: int, wishlist_id: int) -> bool:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM wishlists WHERE id = %s AND user_id = %s", (wishlist_id, user_id))
                return cursor.rowcount > 0

    def delete_item_from_wishlist(self, user_id: int, item_id: int) -> bool:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM wishlists WHERE user_id = %s AND item_id = %s", (user_id, item_id))
                return cursor.rowcount > 0

    def create_like(self, user_id: int, entity_type: str, entity_id: int) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO likes (user_id, entity_type, entity_id)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, entity_type, entity_id, created_at
            """,
            (user_id, entity_type, entity_id),
        ) or {}

    def create_item_like(self, user_id: int, item_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            INSERT INTO likes (user_id, entity_type, entity_id)
            SELECT %s, 'item', i.id
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            JOIN users u ON u.id = c.user_id
            WHERE i.id = %s AND c.is_public = TRUE AND u.is_active = TRUE AND u.is_public = TRUE
            ON CONFLICT DO NOTHING
            RETURNING id, user_id, entity_type, entity_id, created_at
            """,
            (user_id, item_id),
        )

    def delete_item_like(self, user_id: int, item_id: int) -> bool:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM likes WHERE user_id = %s AND entity_type = 'item' AND entity_id = %s",
                    (user_id, item_id),
                )
                return cursor.rowcount > 0

    def create_comment(self, user_id: int, entity_type: str, entity_id: int, text: str) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO comments (user_id, entity_type, entity_id, text)
            VALUES (%s, %s, %s, %s)
            RETURNING id, user_id, entity_type, entity_id, text, created_at
            """,
            (user_id, entity_type, entity_id, text),
        ) or {}

    def get_comments(self, entity_type: str, entity_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT id, user_id, entity_type, entity_id, text, created_at
            FROM comments
            WHERE entity_type = %s AND entity_id = %s
            ORDER BY created_at DESC
            """,
            (entity_type, entity_id),
        )

    def create_item_comment(self, user_id: int, item_id: int, text: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            INSERT INTO comments (user_id, entity_type, entity_id, text)
            SELECT %s, 'item', i.id, %s
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            JOIN users u ON u.id = c.user_id
            WHERE i.id = %s AND c.is_public = TRUE AND u.is_active = TRUE AND u.is_public = TRUE
            RETURNING id, user_id, entity_type, entity_id, text, created_at
            """,
            (user_id, text, item_id),
        )

    def get_item_comments(self, item_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT id, user_id, entity_type, entity_id, text, created_at
            FROM comments
            WHERE entity_type = 'item' AND entity_id = %s
            ORDER BY created_at DESC
            """,
            (item_id,),
        )

    def create_lot(
        self,
        seller_id: int,
        name: str,
        description: str | None,
        start_price: Decimal,
        step: Decimal,
        end_time: datetime,
    ) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO auction_lots (seller_id, name, description, start_price, step, end_time, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'open')
            RETURNING id, seller_id, name, description, start_price, step, end_time, status, created_at
            """,
            (seller_id, name, description, start_price, step, end_time),
        ) or {}

    def get_lots(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            "SELECT id, seller_id, name, description, start_price, step, end_time, status, created_at FROM auction_lots ORDER BY id DESC"
        )

    def get_lot(self, lot_id: int) -> dict[str, Any] | None:
        return self._fetch_one("SELECT * FROM auction_lots WHERE id = %s", (lot_id,))

    def get_top_bid(self, lot_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT id, lot_id, user_id, amount, created_at
            FROM bids
            WHERE lot_id = %s
            ORDER BY amount DESC, created_at ASC
            LIMIT 1
            """,
            (lot_id,),
        )

    def create_bid(self, lot_id: int, user_id: int, amount: Decimal) -> dict[str, Any]:
        return self._fetch_one(
            """
            INSERT INTO bids (lot_id, user_id, amount)
            VALUES (%s, %s, %s)
            RETURNING id, lot_id, user_id, amount, created_at
            """,
            (lot_id, user_id, amount),
        ) or {}

    def close_expired_lots(self) -> int:
        with self._database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auction_lots
                    SET status = 'closed'
                    WHERE status = 'open' AND end_time <= NOW()
                    """
                )
                return cursor.rowcount

    def create_change_event(
        self,
        user_id: int,
        entity_type: str,
        entity_id: int,
        action: str,
        old_value: str | None,
        new_value: str | None,
    ) -> None:
        self._execute(
            """
            INSERT INTO change_events (user_id, entity_type, entity_id, action, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, entity_type, entity_id, action, old_value, new_value),
        )

    def report_collection(self, user_id: int, collection_id: int, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT id, name, price, created_at
            FROM items
            WHERE collection_id = %s
              AND created_at BETWEEN %s AND %s
              AND collection_id IN (SELECT id FROM collections WHERE user_id = %s)
            ORDER BY created_at
            """,
            (collection_id, from_date, to_date, user_id),
        )

    def report_item(self, user_id: int, item_id: int) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT i.id, i.name, i.price, i.created_at, c.name AS collection_name, cat.name AS category_name
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            JOIN categories cat ON cat.id = i.category_id
            WHERE i.id = %s AND c.user_id = %s
            """,
            (item_id, user_id),
        )

    def report_category(self, user_id: int, sort_by: str = "items_count") -> list[dict[str, Any]]:
        allowed_sort = {"items_count": "items_count DESC", "name": "category_name ASC"}
        order_clause = allowed_sort.get(sort_by, "items_count DESC")
        query = f"""
            SELECT cat.id AS category_id, cat.name AS category_name, COUNT(i.id) AS items_count
            FROM categories cat
            LEFT JOIN items i ON i.category_id = cat.id
            WHERE cat.user_id = %s
            GROUP BY cat.id, cat.name
            ORDER BY {order_clause}
        """
        return self._fetch_all(query, (user_id,))

    def report_summary(self, user_id: int, from_date: datetime, to_date: datetime) -> dict[str, Any]:
        return self._fetch_one(
            """
            SELECT
                COUNT(DISTINCT c.id) AS collections_count,
                COUNT(i.id) AS items_count,
                COALESCE(SUM(i.price), 0) AS total_items_price,
                (
                    SELECT COUNT(*)
                    FROM wishlists w
                    WHERE w.user_id = %s AND w.created_at BETWEEN %s AND %s
                ) AS wishlist_count
            FROM collections c
            LEFT JOIN items i ON i.collection_id = c.id AND i.created_at BETWEEN %s AND %s
            WHERE c.user_id = %s
            """,
            (user_id, from_date, to_date, from_date, to_date, user_id),
        ) or {}

    def report_collections_period(self, user_id: int, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT c.id AS collection_id, c.name AS collection_name, COUNT(i.id) AS items_count, COALESCE(SUM(i.price), 0) AS total_price
            FROM collections c
            LEFT JOIN items i ON i.collection_id = c.id AND i.created_at BETWEEN %s AND %s
            WHERE c.user_id = %s
            GROUP BY c.id, c.name
            ORDER BY c.id
            """,
            (from_date, to_date, user_id),
        )

    def report_items_period(self, user_id: int, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT i.id, i.name, i.price, i.created_at, c.id AS collection_id, c.name AS collection_name
            FROM items i
            JOIN collections c ON c.id = i.collection_id
            WHERE c.user_id = %s AND i.created_at BETWEEN %s AND %s
            ORDER BY i.created_at
            """,
            (user_id, from_date, to_date),
        )

    def report_activity(self, user_id: int, from_date: datetime, to_date: datetime, bucket: str) -> list[dict[str, Any]]:
        """
        bucket: 'day' | 'week' | 'month' - controls date_trunc and generate_series step
        """
        step = {"day": "1 day", "week": "1 week", "month": "1 month"}.get(bucket, "1 day")
        return self._fetch_all(
            f"""
            WITH buckets AS (
                SELECT generate_series(
                    date_trunc(%s, %s::timestamp),
                    date_trunc(%s, %s::timestamp),
                    %s::interval
                ) AS bucket_start
            ),
            user_collections AS (
                SELECT id, user_id, created_at FROM collections WHERE user_id = %s
            ),
            user_items AS (
                SELECT i.id, i.collection_id, i.price, i.created_at
                FROM items i
                JOIN user_collections c ON c.id = i.collection_id
            ),
            bucket_items AS (
                SELECT date_trunc(%s, created_at) AS bucket_start,
                       COUNT(*) AS items_count,
                       COALESCE(SUM(price), 0) AS items_total_price
                FROM user_items
                WHERE created_at BETWEEN %s AND %s
                GROUP BY 1
            ),
            bucket_collections AS (
                SELECT date_trunc(%s, created_at) AS bucket_start,
                       COUNT(*) AS collections_count
                FROM user_collections
                WHERE created_at BETWEEN %s AND %s
                GROUP BY 1
            ),
            bucket_likes AS (
                SELECT date_trunc(%s, created_at) AS bucket_start,
                       COUNT(*) AS likes_count
                FROM likes
                WHERE user_id = %s AND created_at BETWEEN %s AND %s
                GROUP BY 1
            ),
            bucket_comments AS (
                SELECT date_trunc(%s, created_at) AS bucket_start,
                       COUNT(*) AS comments_count
                FROM comments
                WHERE user_id = %s AND created_at BETWEEN %s AND %s
                GROUP BY 1
            ),
            bucket_wishlist AS (
                SELECT date_trunc(%s, created_at) AS bucket_start,
                       COUNT(*) AS wishlist_count
                FROM wishlists
                WHERE user_id = %s AND created_at BETWEEN %s AND %s
                GROUP BY 1
            )
            SELECT
                b.bucket_start,
                COALESCE(i.items_count, 0) AS items_count,
                COALESCE(i.items_total_price, 0) AS items_total_price,
                COALESCE(c.collections_count, 0) AS collections_count,
                COALESCE(l.likes_count, 0) AS likes_count,
                COALESCE(cm.comments_count, 0) AS comments_count,
                COALESCE(w.wishlist_count, 0) AS wishlist_count
            FROM buckets b
            LEFT JOIN bucket_items i ON i.bucket_start = b.bucket_start
            LEFT JOIN bucket_collections c ON c.bucket_start = b.bucket_start
            LEFT JOIN bucket_likes l ON l.bucket_start = b.bucket_start
            LEFT JOIN bucket_comments cm ON cm.bucket_start = b.bucket_start
            LEFT JOIN bucket_wishlist w ON w.bucket_start = b.bucket_start
            ORDER BY b.bucket_start
            """,
            (
                bucket,
                from_date,
                bucket,
                to_date,
                step,
                user_id,
                bucket,
                from_date,
                to_date,
                bucket,
                from_date,
                to_date,
                bucket,
                user_id,
                from_date,
                to_date,
                bucket,
                user_id,
                from_date,
                to_date,
                bucket,
                user_id,
                from_date,
                to_date,
            ),
        )
