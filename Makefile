.DEFAULT_GOAL := up

# copies .env.example -> .env only if .env does not already exist
.env:
	cp .env.example .env

.PHONY: up down clean build logs test lint fix format import migrate

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
	bash scripts/run_tests.sh

lint: .env
	docker compose run --rm --no-deps api ruff check .

fix: .env
	docker compose run --rm --no-deps api ruff check . --fix
	docker compose run --rm --no-deps api ruff format .

format: .env
	$(MAKE) fix

migrate: .env
	docker compose run --rm api alembic upgrade head

import: .env
	docker compose run --rm api python -m app.scripts.import_nyc_data $(ARGS)

bootstrap: migrate import  ## first-time setup: run migrations then seed all data from Socrata

refresh: import
