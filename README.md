# CollectiblesVault — Backend API

REST API для учёта коллекций, wishlist, отчётов, социальных действий и аукционов. Стек: **FastAPI**, **PostgreSQL**, **psycopg**, **JWT**.

## Документация API

После запуска сервиса:

Домен (используй его, если API доступно по HTTPS):

`https://CollectiblesVault.ru/api/docs`

Все маршруты API и документация идут с префиксом **`/api`** (можно переопределить переменной `API_PREFIX`).

| Ресурс | URL |
|--------|-----|
| Swagger UI | `https://CollectiblesVault.ru/api/docs` |
| ReDoc | `https://CollectiblesVault.ru/api/redoc` |
| OpenAPI JSON | `https://CollectiblesVault.ru/api/openapi.json` |
| Проверка живости | `GET https://CollectiblesVault.ru/api/health` |
| Проверка БД | `GET https://CollectiblesVault.ru/api/db-health` |

Авторизация для защищённых методов: заголовок `Authorization: Bearer <access_token>` (токен выдаётся после `POST /api/register` или `POST /api/login`).

## Локальный запуск (без Docker)

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

Переменные окружения (пример в `.env` или экспорт в shell):

| Переменная | Назначение |
|------------|------------|
| `DATABASE_URL` | Строка подключения PostgreSQL, например `postgresql://user:pass@localhost:5432/collectibles_vault` |
| `JWT_SECRET` | Секрет для подписи JWT (в проде — длинная случайная строка) |
| `JWT_ALGORITHM` | По умолчанию `HS256` |
| `JWT_EXP_MINUTES` | Время жизни токена в минутах |
| `API_PREFIX` | Префикс путей API, по умолчанию `/api` |

Запуск:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Docker

Сборка образа приложения и запуск вместе с PostgreSQL (`api` использует переменную `IMAGE_TAG`):

**bash:**

```bash
docker build -t collectibles-vault-api:local .
export IMAGE_TAG=collectibles-vault-api:local
docker compose up -d
```

**PowerShell:**

```powershell
docker build -t collectibles-vault-api:local .
$env:IMAGE_TAG="collectibles-vault-api:local"
docker compose up -d
```

Для прод-деплоя образ собирается в **GitHub Actions** и публикуется в **GHCR**; на сервере выполняется `docker compose pull` и `docker compose up -d` (см. `.github/workflows/deploy.yml`).

На сервере в каталоге деплоя должен лежать `docker-compose.yml` (workflow может копировать его по SCP). Открой порт **8000** в фаерволе VPS и в панели облака, если нужен доступ из интернета.

## GitHub Actions — секреты и переменные

**Secrets:**

- `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY` — SSH на сервер деплоя
- `GHCR_USERNAME`, `GHCR_TOKEN` — pull приватного образа с GHCR на сервере

**Variables** (рекомендуется для не секретных данных):

- `SERVER_PROJECT_DIR` — путь на сервере, например `/home/user/Backend`

## Структура проекта (кратко)

```
app/
  api/           # HTTP-контроллеры (роуты)
  core/          # настройки, JWT/пароли
  db/            # пул подключений, репозиторий
  services/      # бизнес-логика
  schemas.py     # Pydantic-модели запросов
main.py          # точка входа FastAPI
Dockerfile
docker-compose.yml
```

## Основные эндпоинты

- **Auth:** `POST /api/register`, `POST /api/login`, `GET /api/auth/me`
- **Коллекции и предметы:** `/api/collections`, `/api/items`
- **Категории, wishlist:** `/api/categories`, `/api/wishlist`
- **Отчёты:** `/api/reports/...`
- **Соцсеть:** `/api/like`, `/api/comment`, `GET /api/comments`
- **Аукцион:** `POST /api/lot`, `GET /api/lots`, `POST /api/bid`

Подробные схемы тел запросов — в Swagger (`/api/docs`).

## Связанные документы

- [USECASE.md](USECASE.md) — сценарии использования (use case).
- [API_USAGE.md](API_USAGE.md) — примеры запросов `curl` для новых endpoint-ов.