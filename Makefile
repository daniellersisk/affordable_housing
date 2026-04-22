.DEFAULT_GOAL := up

# copies .env.example -> .env only if .env does not already exist
.env:
	cp .env.example .env

.PHONY: up down clean build logs test lint import migrate

up: .env
	docker compose up

build: .env
	docker compose up --build

down:
	docker compose down

clean:
	docker compose down -v

logs:
	docker compose logs -f

test: .env
	docker compose run --rm api pytest -q

lint: .env
	docker compose run --rm --no-deps api ruff check .

migrate: .env
	docker compose run --rm api alembic upgrade head

import: .env
	docker compose run --rm api python -m app.scripts.import_nyc_data
