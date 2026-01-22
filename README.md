# ToolkitRAG

AI Toolkit Learning Platform - A production-ready web application built with FastAPI and PostgreSQL.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- `.env` file (copy from `.env.example`)

### Run Locally

```bash
# Start the application
docker compose up --build

# Access the application
open http://localhost:8000
```

### Health Checks

- **Health**: http://localhost:8000/health
- **Ready**: http://localhost:8000/ready (checks DB connectivity)

### Stop the Application

```bash
docker compose down
```

## Project Structure

```
aitools/
├── app/
│   ├── main.py           # FastAPI application
│   ├── settings.py       # Configuration
│   ├── db.py             # Database session
│   ├── models/           # SQLAlchemy models
│   ├── routers/          # API routes
│   ├── services/         # Business logic
│   └── templates/        # Jinja2 templates
├── docker/
│   ├── Dockerfile        # Application container
│   └── entrypoint.sh     # Startup script
├── alembic/              # Database migrations
├── tests/                # Test suite
└── docker-compose.yml    # Docker orchestration
```

## Development

### Run Migrations

```bash
# Create a new migration
docker compose run --rm app alembic revision --autogenerate -m "description"

# Apply migrations
docker compose run --rm app alembic upgrade head
```

### Run Tests

```bash
docker compose run --rm app pytest
```

## Tech Stack

- **Backend**: FastAPI 0.109+
- **Database**: PostgreSQL with pgvector
- **Migrations**: Alembic
- **Templates**: Jinja2
- **Container**: Docker & Docker Compose
