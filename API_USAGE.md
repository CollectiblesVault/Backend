# API Usage (new endpoints)

## Base

- Base URL: `http://127.0.0.1:8000/api`
- Auth header: `Authorization: Bearer <TOKEN>`

```bash
export BASE_URL="http://127.0.0.1:8000/api"
export TOKEN="<JWT_TOKEN>"
```

## Auth / Profile

### Update profile

```bash
curl -X PATCH "$BASE_URL/auth/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "display_name": "Vasilij",
    "bio": "Collector",
    "avatar_url": "https://example.com/avatar.png"
  }'
```

### Change password

```bash
curl -X POST "$BASE_URL/auth/me/password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "current_password": "old_pass_123",
    "new_password": "new_pass_123"
  }'
```

### Deactivate profile

```bash
curl -X PATCH "$BASE_URL/auth/me/deactivate" \
  -H "Authorization: Bearer $TOKEN"
```

## Public users and collections

### List public users

```bash
curl "$BASE_URL/users?limit=20&offset=0"
```

### Get public user

```bash
curl "$BASE_URL/users/1"
```

### Get public collections of user

```bash
curl "$BASE_URL/users/1/collections"
```

### Get public items by collection

```bash
curl "$BASE_URL/collections/1/items"
```

## Visibility

### Set collection visibility

```bash
curl -X PATCH "$BASE_URL/collections/1/visibility" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_public": true}'
```

### Set item visibility

```bash
curl -X PATCH "$BASE_URL/items/1/visibility" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_public": true}'
```

## Item social actions

### Like item

```bash
curl -X POST "$BASE_URL/items/1/like" \
  -H "Authorization: Bearer $TOKEN"
```

### Remove item like

```bash
curl -X DELETE "$BASE_URL/items/1/like" \
  -H "Authorization: Bearer $TOKEN"
```

### Create item comment

```bash
curl -X POST "$BASE_URL/items/1/comments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"Great item!"}'
```

### Get item comments

```bash
curl "$BASE_URL/items/1/comments"
```

## Wishlist by item

### Add item to wishlist

```bash
curl -X POST "$BASE_URL/items/1/wishlist" \
  -H "Authorization: Bearer $TOKEN"
```

### Remove item from wishlist

```bash
curl -X DELETE "$BASE_URL/items/1/wishlist" \
  -H "Authorization: Bearer $TOKEN"
```

## Reports

### JSON summary (`week|month|year`)

```bash
curl "$BASE_URL/reports/summary?period=week" \
  -H "Authorization: Bearer $TOKEN"
```

### CSV summary

```bash
curl "$BASE_URL/reports/summary.csv?period=month" \
  -H "Authorization: Bearer $TOKEN"
```

### CSV collections for custom range

```bash
curl "$BASE_URL/reports/collections.csv?fromDate=2026-01-01T00:00:00Z&toDate=2026-03-01T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

### CSV items for custom range

```bash
curl "$BASE_URL/reports/items.csv?fromDate=2026-01-01T00:00:00Z&toDate=2026-03-01T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

## Notes

- Before using new API, apply DB schema:

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

- CSV endpoints return `text/csv`.
