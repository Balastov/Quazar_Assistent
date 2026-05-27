.PHONY: up down migrate seed api worker web install

up:
	cd infra && docker compose up -d

down:
	cd infra && docker compose down

migrate:
	cd apps/api && alembic upgrade head

seed:
	cd apps/api && python seed.py

api:
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A workers.celery_app.app worker --loglevel=info

web:
	cd apps/web && npm run dev

install:
	cd apps/api && pip install -r requirements.txt
	cd apps/web && npm install
