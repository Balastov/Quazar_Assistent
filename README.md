# Quazar Assistent

Корпоративный AI-ассистент для закрытого контура: анализ файлов и Confluence, чат с несколькими LLM (GPT, DeepSeek, GigaChat), проекты с иерархией папок.

## Возможности

- Чат в стиле QwenChat со streaming-ответами и цитатами
- Проекты с бесконечной вложенностью папок
- Загрузка файлов (PDF, DOCX, TXT, HTML) и RAG-поиск
- Интеграция с Confluence (синхронизация spaces)
- Выбор источника: файлы / Confluence / оба
- Несколько LLM-провайдеров через единый API
- Учёт токенов и audit log
- Готовность к multi-tenant (RLS, `organization_id`)

## Быстрый старт

```bash
# 1. Инфраструктура
cp .env.example .env
cd infra && docker compose up -d

# 2. API
cd ../apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 8000

# 3. Worker (в отдельном терминале)
cd ../..
celery -A workers.celery_app.app worker --loglevel=info

# 4. Web UI
cd apps/web
npm install
npm run dev
```

Откройте http://localhost:3000

**Демо-аккаунт:** `admin@quazar.local` / `admin12345`

## Структура

```
apps/api/          FastAPI backend
apps/web/          Next.js frontend
packages/          Shared Python packages
workers/           Celery background tasks
infra/             Docker Compose, Nginx
docs/              Documentation
```

## API

Документация: http://localhost:8000/docs

## Лицензия

MIT
