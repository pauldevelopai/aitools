"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers import health, admin, rag, auth_routes, toolkit
from app.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with startup validation."""
    # Validate embedding configuration at startup
    try:
        settings.validate_embedding_config()
        logger.info(f"Embedding provider: {settings.EMBEDDING_PROVIDER}")
        if settings.EMBEDDING_PROVIDER == "openai":
            logger.info(f"Using OpenAI model: {settings.EMBEDDING_MODEL}")
        elif settings.EMBEDDING_PROVIDER == "local_stub":
            logger.info("Using local stub provider for testing")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    yield


app = FastAPI(
    title="ToolkitRAG",
    description="AI Toolkit Learning Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(rag.router)
app.include_router(auth_routes.router)
app.include_router(toolkit.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ToolkitRAG"}
    )
