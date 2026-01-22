"""Admin routes."""
import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.ingestion import ingest_document
from app.models.toolkit import ToolkitDocument

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

# Simple admin password check (for Milestone 2)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def check_admin_password(password: str = Form(...)):
    """Simple password check for admin access."""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return True


@router.get("/ingest", response_class=HTMLResponse)
async def ingest_page(request: Request):
    """Admin ingestion page."""
    return templates.TemplateResponse(
        "admin/ingest.html",
        {"request": request, "title": "Ingest Document"}
    )


@router.post("/ingest")
async def upload_and_ingest(
    file: UploadFile = File(...),
    version_tag: str = Form(...),
    admin_password: str = Form(...),
    create_embeddings: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest a DOCX file.

    Requires:
    - file: DOCX file
    - version_tag: Unique version identifier
    - admin_password: Admin password from env
    - create_embeddings: Whether to create embeddings (default True)
    """
    # Check admin password
    if admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="File must be a .docx file")

    # Save uploaded file
    upload_dir = "/data/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # Create unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Ingest document
        doc = ingest_document(
            db=db,
            file_path=file_path,
            version_tag=version_tag,
            source_filename=file.filename,
            create_embeddings=create_embeddings
        )

        return {
            "status": "success",
            "message": f"Document ingested successfully",
            "document_id": str(doc.id),
            "version_tag": doc.version_tag,
            "chunk_count": doc.chunk_count
        }

    except ValueError as e:
        # Clean up file if ingestion fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Clean up file if ingestion fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/documents", response_class=HTMLResponse)
async def list_documents(
    request: Request,
    db: Session = Depends(get_db)
):
    """List all ingested documents."""
    documents = db.query(ToolkitDocument).order_by(
        ToolkitDocument.upload_date.desc()
    ).all()

    return templates.TemplateResponse(
        "admin/documents.html",
        {"request": request, "title": "Documents", "documents": documents}
    )
