# HubExtract Pro

HubExtract Pro is a production-ready Django REST API for asynchronous data extraction workflows.

## Features

- Django REST Framework API endpoints for scan lifecycle management
- UUID-backed extraction jobs
- Pagination, search, ordering, and status filtering for jobs
- Aggregate statistics for scan runs
- Celery-style background processing with inline fallback for local development
- OpenAPI schema and Swagger documentation

## Run locally

### Django app

```powershell
cd c:\Users\pjahe\hubextract-pro
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### Celery worker

```powershell
celery -A config worker -l info
```

### Docker compose

```powershell
docker compose up --build
```

## API docs

- Swagger UI: http://127.0.0.1:8000/api/v1/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/v1/schema/
