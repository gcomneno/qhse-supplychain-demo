.PHONY: run init worker demo reset kpi test test-db-up test-db-wait test-db-migrate

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

run:
	PYTHONPATH=$(PYTHONPATH) uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file $(ENV_FILE)

init:
	PYTHONPATH=$(PYTHONPATH) python scripts/init_db.py

worker:
	PYTHONPATH=$(PYTHONPATH) python -m app.worker

demo:
	./demo.sh

reset:
	./reset_demo.sh

kpi:
	curl -s http://127.0.0.1:8000/kpi && echo

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