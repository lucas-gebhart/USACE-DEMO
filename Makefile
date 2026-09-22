.PHONY: up down logs oracle api web load test lint build fixtures

# Full stack: Oracle 23ai Free + FastAPI (migrates and loads fixtures on start) + React behind nginx.
up:
	docker compose up -d --build
	@echo "web  -> http://localhost:5173   api -> http://localhost:8000/docs"

down:
	docker compose down -v

logs:
	docker compose logs -f api

# Local development: Oracle in Docker, API and web on the host with hot reload.
oracle:
	docker compose up -d oracle
	@until docker compose exec -T oracle healthcheck.sh >/dev/null 2>&1; do echo "waiting for oracle..."; sleep 5; done

api:
	cd api && uv run uvicorn app.main:app --reload --port 8000

web:
	cd web && npm run dev

load:
	cd api && uv run python -m loaders

test:
	cd api && uv run pytest -q

lint:
	cd api && uv run ruff check . && uv run ruff format --check .
	cd web && npm run lint && npm run typecheck

build:
	cd web && npm run build

# Re-pull public sources (USAspending, FY25 J-sheets, NID, LPMS, NTNI). Network access required.
fixtures:
	python3 data/fetch.py
