"""FastAPI application entrypoint."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers import health

app = FastAPI(
    title="ToolkitRAG",
    description="AI Toolkit Learning Platform",
    version="0.1.0"
)

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(health.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Homepage."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ToolkitRAG"}
    )
