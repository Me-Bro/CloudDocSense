.PHONY: up down migrate seed test lint eval build logs shell-api shell-db help

help:
	@echo "Available commands:"
	@echo "  up       - Start all services"
	@echo "  down     - Stop all services"
	@echo "  migrate  - Run database migrations"
	@echo "  seed     - Seed database with test data"
	@echo "  test     - Run all tests"
	@echo "  lint     - Run linters"
	@echo "  eval     - Run evaluation pipeline"
	@echo "  build    - Build all Docker images"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm migrate

seed:
	docker compose run --rm api python -m app.scripts.seed

test:
	docker compose run --rm api pytest tests/ -v
	cd apps/web && pnpm test

lint:
	cd apps/api && ruff check . && mypy app/
	cd apps/web && pnpm lint

eval:
	docker compose run --rm api python -m eval.runners.run_all

logs:
	docker compose logs -f

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U docsense -d docsense
