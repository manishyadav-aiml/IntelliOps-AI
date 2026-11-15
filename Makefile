.PHONY: doctor smoke up down e2e train-demo sample-logs db-up db-down backend-install backend-run backend-test backend-lint migrate frontend-install frontend-dev frontend-test frontend-build

db-up:
	docker compose up -d db

db-down:
	docker compose down

backend-install:
	cd backend && pip install -r requirements-dev.txt

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && pytest -v

backend-lint:
	cd backend && ruff check . && ruff format --check .

migrate:
	cd backend && alembic upgrade head

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

up:
	docker compose up --build

down:
	docker compose down

e2e:
	cd frontend && npm run e2e

sample-logs:
	python scripts/generate_sample_logs.py

train-demo:
	python scripts/train_anomaly_model.py --logs data/sample_logs/normal_activity.log data/sample_logs/incident_payment_failure.log --window 60 --quantile 0.97

doctor:
	python scripts/doctor.py

smoke:
	python scripts/smoke_test.py http://localhost:8000
