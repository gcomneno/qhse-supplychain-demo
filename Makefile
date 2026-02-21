SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

.PHONY: help run init migrate worker demo reset kpi test \
        up down ps logs smoke reset-db \
        test-db-up test-db-wait test-db-migrate \
		smoke-clean smoke-wipe

ENV_FILE ?= .env
PYTHONPATH ?= .

COMPOSE ?= docker compose
DB_SERVICE ?= db

DB_USER ?= qhse
DB_PASS ?= qhse
DB_HOST ?= 127.0.0.1
DB_PORT ?= 5432
DB_NAME ?= qhse

DATABASE_URL ?= postgresql+psycopg://$(DB_USER):$(DB_PASS)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)

help:
	@echo "Targets:"
	@echo "  make run        - Run API locally (uvicorn --reload)"
	@echo "  make worker     - Run worker locally"
	@echo "  make test       - Run pytest (compose db + alembic)"
	@echo "  make up         - Start stack (db api worker prometheus)"
	@echo "  make down       - Stop stack"
	@echo "  make ps         - Show compose ps"
	@echo "  make logs       - Tail logs (all services)"
	@echo "  make smoke      - Run smoke test (compose network)"
	@echo "  make reset-db   - Drop volumes (DANGER: wipes DB)"
	@echo "  make migrate    - Apply alembic migrations to local DB (compose db)"

run:
	PYTHONPATH=$(PYTHONPATH) uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file $(ENV_FILE)

# Deprecated: keep for backward compatibility, but steer to Alembic.
init:
	@echo "Deprecated: use 'make migrate' (Alembic) instead."
	@$(MAKE) migrate

worker:
	PYTHONPATH=$(PYTHONPATH) python -m app.worker

demo:
	./demo.sh

reset:
	./reset_demo.sh

kpi:
	curl -s http://127.0.0.1:8000/kpi && echo

# --- Stack management (dev/integration) ---
up:
	$(COMPOSE) up -d db api worker prometheus

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

smoke:
	./scripts/smoke.sh

reset-db:
	@echo "⚠️  This will delete volumes (DB data). Ctrl+C to abort."
	@sleep 2
	$(COMPOSE) down -v

# Apply migrations against the local compose DB (db up + ready + alembic upgrade head)
migrate: test-db-migrate

# --- Test DB lifecycle (used by make test) ---
test-db-up:
	$(COMPOSE) up -d $(DB_SERVICE)

test-db-wait: test-db-up
	@echo "Waiting for Postgres ($(DB_SERVICE))..."
	@for i in $$(seq 1 40); do \
		$(COMPOSE) exec -T $(DB_SERVICE) pg_isready -U $(DB_USER) -d $(DB_NAME) >/dev/null 2>&1 && exit 0; \
		sleep 1; \
	done; \
	echo "Postgres non è pronto (timeout)."; \
	exit 1

test-db-migrate: test-db-wait
	@echo "Applying Alembic migrations to $(DB_NAME)"
	@DATABASE_URL="$(DATABASE_URL)" PYTHONPATH=$(PYTHONPATH) alembic upgrade head

test: test-db-migrate
	@echo "Running tests with DATABASE_URL=$(DATABASE_URL)"
	env -u TEST_DATABASE_URL -u ENABLE_TRACING -u TRACE_SAMPLING \
		DATABASE_URL="$(DATABASE_URL)" ENABLE_TRACING=0 TRACE_SAMPLING=0 \
		PYTHONPATH=$(PYTHONPATH) python -m pytest -q

smoke-clean:
	SMOKE_CLEANUP=down ./scripts/smoke.sh

smoke-wipe:
	SMOKE_CLEANUP=down-v ./scripts/smoke.sh