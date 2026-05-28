# Quazar Assistent

Корпоративный AI-ассистент для закрытого контура: анализ файлов и Confluence, чат с несколькими LLM (GPT, DeepSeek, GigaChat), проекты с иерархией папок.

## Возможности

- Чат в стиле QwenChat со streaming-ответами и цитатами
- Проекты с бесконечной вложенностью папок
- Загрузка файлов (PDF, DOCX, TXT, HTML, **XLSX**, **изображения**, **MS Project**) и RAG-поиск
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

## Поддерживаемые форматы файлов

| Формат | Расширения | Способ извлечения |
|--------|------------|-------------------|
| Excel | `.xlsx`, `.xlsm` | openpyxl → markdown-таблицы |
| Изображения | `.jpg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff` | Tesseract OCR; при пустом OCR — GPT-4o vision (если задан `OPENAI_API_KEY`) |
| MS Project | `.mpp` | MPXJ (Java) |
| MS Project | `.mpx`, `.xml` | Нативный парсер MPX / MSPDI XML |
| Документы | `.pdf`, `.docx`, `.txt`, `.html` | как ранее |

Для OCR локально: `brew install tesseract tesseract-lang` (macOS) или пакеты `tesseract-ocr` в Linux.

## Деплой на ВМ

Автодеплой при push в `main`: см. [docs/deploy.md](docs/deploy.md).

Кратко: настройте секреты `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `DEPLOY_PATH` в GitHub Actions.

## API

Документация: http://localhost:8000/docs

## Лицензия

MIT
