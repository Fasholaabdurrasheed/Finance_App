# Finance App Backend (Stage 1 MVP)

Production-ready FastAPI backend for personal finance tracking and financial analytics.

## Stage 1 Features

- JWT authentication (register, login, protected endpoints)
- Transactions CRUD (income/expense)
- Transaction filtering (date range, category, transaction type)
- Categories (default and custom)
- Dashboard analytics (income, expenses, balance, monthly summary, category summary)
- Clean architecture with service layer and dependency injection

## Project Structure

```text
finance-app/
|- app/
|  |- main.py
|  |- core/
|  |  |- config.py
|  |  |- security.py
|  |  |- exceptions.py
|  |- database/
|  |  |- connection.py
|  |  |- session.py
|  |  |- init_db.py
|  |- models/
|  |  |- base.py
|  |  |- enums.py
|  |  |- user.py
|  |  |- category.py
|  |  |- transaction.py
|  |- schemas/
|  |  |- auth.py
|  |  |- category.py
|  |  |- transaction.py
|  |  |- dashboard.py
|  |- routes/
|  |  |- auth.py
|  |  |- categories.py
|  |  |- transactions.py
|  |  |- dashboard.py
|  |  |- health.py
|  |- services/
|  |  |- auth_service.py
|  |  |- category_service.py
|  |  |- transaction_service.py
|  |- analytics/
|  |  |- analytics_service.py
|  |- auth/
|  |  |- dependencies.py
|  |- middleware/
|  |  |- request_context.py
|  |- utils/
|     |- logger.py
|- tests/
|  |- test_health.py
|  |- test_security.py
|- requirements.txt
|- .env.example
|- alembic.ini
```

## Setup

1. Create and activate virtual environment:

```powershell
cd c:\Users\Abdul_Rasheed\Desktop\Finance_Analysis\finance-app
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create environment file:

```powershell
Copy-Item .env.example .env
```

4. Update .env values, especially:

- DATABASE_URL
- JWT_SECRET_KEY
- CORS_ORIGINS

PostgreSQL is the intended database for this backend. Make sure the database exists and the user credentials in DATABASE_URL are correct before starting the app.

5. Run API:

```powershell
uvicorn app.main:app --reload
```

6. Open API docs:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Environment Variables

- API_TITLE
- API_VERSION
- DEBUG
- DATABASE_URL
- JWT_SECRET_KEY
- JWT_ALGORITHM
- ACCESS_TOKEN_EXPIRE_MINUTES
- CORS_ORIGINS (comma-separated)
- AUTO_CREATE_TABLES

## API Endpoints (Stage 1)

### Health

- GET /health

### Authentication

- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me

### Categories

- GET /api/v1/categories
- POST /api/v1/categories

### Transactions

- GET /api/v1/transactions
	- Query: start_date, end_date, category_id, tx_type
- POST /api/v1/transactions
- PUT /api/v1/transactions/{transaction_id}
- DELETE /api/v1/transactions/{transaction_id}

### Dashboard

- GET /api/v1/dashboard/summary

## Engineering Decisions

- Layered architecture: routes -> services -> models keeps business logic testable and reusable.
- Dependency injection: DB sessions and auth user context are injected with FastAPI Depends.
- Security: password hashing via passlib bcrypt and JWT token auth.
- Typed schemas: Pydantic request/response models prevent malformed API contracts.
- Middleware and exception handlers: standardized request tracing and error responses.
- Startup lifecycle: optional auto table sync for MVP bootstrap; Alembic remains for future migrations.

## Why This Scales

- New domains can be added as independent modules (for example forecasting and notifications).
- Analytics logic is isolated in app/analytics and app/services, making ML integration straightforward.
- React Native integration is clean because APIs are versioned and strongly typed.
- Future BI or Plotly endpoints can reuse aggregated service methods without touching route layer.

## Run Tests

```powershell
pytest -q
```

## Next Stage Integrations

- Forecasting engines and ML model serving inside app/forecasting and app/analytics.
- Notification service module (email/push/in-app) with background workers.
- AI assistant endpoints that compose analytics and forecasting outputs.
