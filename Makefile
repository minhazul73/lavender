.PHONY: install dev-backend dev-frontend build test test-frontend clean

# Install all backend (uv) and frontend (bun) dependencies
install:
	uv sync --extra dev
	cd frontend && bun install

# Run backend only (FastAPI with auto-reload via uv)
dev-backend:
	uv run uvicorn server.main:app --reload --host 0.0.0.0 --port 8085

# Run frontend dev server only (Vite HMR proxying API to :8085)
dev-frontend:
	cd frontend && bun run dev

# Build production frontend bundle into server/dist/
build:
	cd frontend && bun run build

# Run all backend tests with uv
test:
	uv run pytest -v

# Run frontend tests with bun
test-frontend:
	cd frontend && bun run test

clean:
	rm -rf server/dist frontend/node_modules .venv uv.lock
