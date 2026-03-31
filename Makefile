PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
FRONTEND_DIR := frontend/stock-ui

.PHONY: install-backend install-frontend run-backend run-frontend test lint lint-backend lint-frontend docker-up docker-down docker-build cloudrun-deploy

install-backend:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

install-frontend:
	cd $(FRONTEND_DIR) && npm ci

run-backend:
	$(PY) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd $(FRONTEND_DIR) && npm run dev

test:
	$(PY) -m unittest discover -s tests -v

lint: lint-backend lint-frontend

lint-backend:
	$(PY) -m ruff check backend tests

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-build:
	docker build -t stock-intelligence-copilot:local .

cloudrun-deploy:
	@test -n "$(PROJECT_ID)" || (echo "Set PROJECT_ID=<your-gcp-project-id>" && exit 1)
	@test -n "$(REGION)" || (echo "Set REGION=<your-gcp-region>" && exit 1)
	@test -n "$(SERVICE)" || (echo "Set SERVICE=<your-cloud-run-service-name>" && exit 1)
	gcloud builds submit --tag gcr.io/$(PROJECT_ID)/$(SERVICE)
	gcloud run deploy $(SERVICE) \
		--image gcr.io/$(PROJECT_ID)/$(SERVICE) \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated
