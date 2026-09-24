.PHONY: install dev-backend dev-frontend build test test-frontend clean

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	cd frontend && bun install

# Run backend only (serves compiled dist/ or API)
dev-backend:
	. .venv/bin/activate && uvicorn server.main:app --reload --port 8080

# Run frontend dev server only (Vite with HMR proxying API to :8080)
dev-frontend:
	cd frontend && bun run dev

# Build production frontend bundle into server/dist/
build:
	cd frontend && bun run build

# Run all backend tests
test:
	. .venv/bin/activate && pytest -v

# Run frontend tests
test-frontend:
	cd frontend && bun test

clean:
	rm -rf server/dist frontend/node_modules .venv
