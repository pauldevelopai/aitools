"""Add robustness columns/indexes to open_source_apps, add lesson cross-reference
columns, seed 10 open-source AI apps, 3 new lesson modules, and 12 new lessons.

Revision ID: 048
Revises: 047
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------ #
    # 1. ALTER open_source_apps - add columns                            #
    # ------------------------------------------------------------------ #
    op.add_column("open_source_apps", sa.Column("github_stars", sa.Integer(), nullable=True))
    op.add_column("open_source_apps", sa.Column("community_rating", sa.Float(), nullable=True))
    op.add_column("open_source_apps", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))

    # 2. CHECK constraint on community_rating
    op.create_check_constraint(
        "ck_open_source_apps_community_rating",
        "open_source_apps",
        "community_rating IS NULL OR (community_rating >= 0 AND community_rating <= 5)",
    )

    # 3. Indexes on open_source_apps
    op.create_index("ix_open_source_apps_created_by", "open_source_apps", ["created_by"])
    op.create_index("ix_open_source_apps_is_featured", "open_source_apps", ["is_featured"])
    op.create_index("ix_open_source_apps_difficulty", "open_source_apps", ["difficulty"])
    op.create_index("ix_open_source_apps_status_featured", "open_source_apps", ["status", "is_featured"])
    op.execute("CREATE INDEX ix_open_source_apps_platforms_gin ON open_source_apps USING gin (platforms)")

    # ------------------------------------------------------------------ #
    # 4. ALTER lesson_modules - add prerequisites                        #
    # ------------------------------------------------------------------ #
    op.add_column("lesson_modules", sa.Column("prerequisites", postgresql.JSONB(), nullable=True, server_default="[]"))

    # ------------------------------------------------------------------ #
    # 5. ALTER lessons - add cross-reference columns                     #
    # ------------------------------------------------------------------ #
    op.add_column("lessons", sa.Column("related_app_slugs", postgresql.JSONB(), nullable=True, server_default="[]"))
    op.add_column("lessons", sa.Column("related_tool_slugs", postgresql.JSONB(), nullable=True, server_default="[]"))
    op.add_column("lessons", sa.Column("recommended_level", sa.String(), nullable=True))
    op.add_column("lessons", sa.Column("sector_relevance", postgresql.JSONB(), nullable=True, server_default="[]"))

    # 6. CHECK constraint on recommended_level
    op.create_check_constraint(
        "ck_lesson_recommended_level",
        "lessons",
        "recommended_level IS NULL OR recommended_level IN ('beginner', 'intermediate', 'advanced')",
    )

    # ------------------------------------------------------------------ #
    # 7. Update existing module prerequisites                            #
    # ------------------------------------------------------------------ #
    op.execute("UPDATE lesson_modules SET prerequisites = '[]'::jsonb WHERE slug = 'ai-foundations'")
    op.execute("UPDATE lesson_modules SET prerequisites = '[\"ai-foundations\"]'::jsonb WHERE slug = 'responsible-ai-use'")

    # ------------------------------------------------------------------ #
    # 8. Seed 10 open-source AI apps                                     #
    # ------------------------------------------------------------------ #
    apps_tbl = sa.table(
        "open_source_apps",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("github_url", sa.String),
        sa.column("website_url", sa.String),
        sa.column("docs_url", sa.String),
        sa.column("categories", postgresql.JSONB),
        sa.column("tags", postgresql.JSONB),
        sa.column("sectors", postgresql.JSONB),
        sa.column("license_type", sa.String),
        sa.column("deployment_type", sa.String),
        sa.column("installation_guide", sa.Text),
        sa.column("system_requirements", sa.Text),
        sa.column("platforms", postgresql.JSONB),
        sa.column("difficulty", sa.String),
        sa.column("pricing_model", sa.String),
        sa.column("is_featured", sa.Boolean),
        sa.column("status", sa.String),
        sa.column("github_stars", sa.Integer),
        sa.column("community_rating", sa.Float),
    )

    # Remove any test app entries that might conflict with seed data
    op.execute("DELETE FROM open_source_apps WHERE slug IN ('whisper','ollama','open-webui','privategpt','docling','label-studio','haystack','comfyui','briefer','stirling-pdf')")

    op.bulk_insert(apps_tbl, [
        # ---- 1. Whisper ----
        {
            "slug": "whisper",
            "name": "Whisper",
            "description": "Automatic speech recognition model from OpenAI that runs locally. Transcribe audio in dozens of languages with a single command.",
            "github_url": "https://github.com/openai/whisper",
            "website_url": None,
            "docs_url": "https://github.com/openai/whisper#readme",
            "categories": ["speech-to-text", "transcription"],
            "tags": ["ai", "speech", "transcription", "openai", "python"],
            "sectors": ["newsroom", "academic", "business", "ngo"],
            "license_type": "MIT",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Quick Start\n\n"
                "```bash\n"
                "pip install -U openai-whisper\n"
                "```\n\n"
                "## Basic Usage\n\n"
                "```bash\n"
                "whisper audio.mp3 --model base\n"
                "```\n\n"
                "## Python API\n\n"
                "```python\n"
                "import whisper\n\n"
                "model = whisper.load_model(\"base\")\n"
                "result = model.transcribe(\"audio.mp3\")\n"
                "print(result[\"text\"])\n"
                "```\n\n"
                "## Model Sizes\n\n"
                "| Model | Parameters | VRAM | Speed |\n"
                "|-------|-----------|------|-------|\n"
                "| tiny | 39M | ~1 GB | ~32x |\n"
                "| base | 74M | ~1 GB | ~16x |\n"
                "| small | 244M | ~2 GB | ~6x |\n"
                "| medium | 769M | ~5 GB | ~2x |\n"
                "| large | 1550M | ~10 GB | 1x |\n\n"
                "Start with `base` for a good speed/accuracy balance."
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Python 3.8+\n"
                "- FFmpeg installed (`brew install ffmpeg` on macOS)\n"
                "- 2GB+ RAM (base model), 10GB+ for large model\n"
                "- GPU recommended but not required"
            ),
            "platforms": ["linux", "macos", "windows", "docker"],
            "difficulty": "beginner",
            "pricing_model": "free",
            "is_featured": True,
            "status": "published",
            "github_stars": 75000,
            "community_rating": 4.8,
        },
        # ---- 2. Ollama ----
        {
            "slug": "ollama",
            "name": "Ollama",
            "description": "Run large language models locally with a single command. Supports Llama, Mistral, Code Llama, and dozens more.",
            "github_url": "https://github.com/ollama/ollama",
            "website_url": "https://ollama.com",
            "docs_url": "https://github.com/ollama/ollama/blob/main/docs/README.md",
            "categories": ["llm", "local-ai", "inference"],
            "tags": ["ai", "llm", "local", "privacy", "self-hosted"],
            "sectors": ["newsroom", "ngo", "business", "academic"],
            "license_type": "MIT",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Install\n\n"
                "**macOS / Linux:**\n"
                "```bash\n"
                "curl -fsSL https://ollama.com/install.sh | sh\n"
                "```\n\n"
                "**Windows:** Download from [ollama.com/download](https://ollama.com/download)\n\n"
                "## Run Your First Model\n\n"
                "```bash\n"
                "ollama run llama3.2\n"
                "```\n\n"
                "This downloads and runs Meta's Llama 3.2 model locally. "
                "Your data never leaves your machine.\n\n"
                "## Popular Models\n\n"
                "| Model | Size | Use Case |\n"
                "|-------|------|----------|\n"
                "| llama3.2 | 3B | General purpose, fast |\n"
                "| mistral | 7B | Strong reasoning |\n"
                "| codellama | 7B | Code generation |\n"
                "| llava | 7B | Vision + text |\n\n"
                "## API Access\n\n"
                "Ollama exposes a local API at `http://localhost:11434`:\n\n"
                "```bash\n"
                "curl http://localhost:11434/api/generate -d '{\n"
                "  \"model\": \"llama3.2\",\n"
                "  \"prompt\": \"Explain AI in one paragraph\"\n"
                "}'\n"
                "```"
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- 8GB RAM minimum (16GB recommended)\n"
                "- 4GB+ free disk space per model\n"
                "- macOS 11+, Linux, or Windows 10+\n"
                "- GPU optional but significantly faster"
            ),
            "platforms": ["linux", "macos", "windows", "docker"],
            "difficulty": "intermediate",
            "pricing_model": "free",
            "is_featured": True,
            "status": "published",
            "github_stars": 130000,
            "community_rating": 4.7,
        },
        # ---- 3. Open WebUI ----
        {
            "slug": "open-webui",
            "name": "Open WebUI",
            "description": "A ChatGPT-like web interface for local AI models. Connect to Ollama and chat privately through a polished UI.",
            "github_url": "https://github.com/open-webui/open-webui",
            "website_url": "https://openwebui.com",
            "docs_url": "https://docs.openwebui.com",
            "categories": ["chat-ui", "llm-frontend", "ai-interface"],
            "tags": ["ai", "chat", "ui", "ollama", "self-hosted"],
            "sectors": ["newsroom", "ngo", "business"],
            "license_type": "MIT",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Quick Start with Docker\n\n"
                "```bash\n"
                "docker run -d -p 3000:8080 \\\n"
                "  --add-host=host.docker.internal:host-gateway \\\n"
                "  -v open-webui:/app/backend/data \\\n"
                "  --name open-webui \\\n"
                "  ghcr.io/open-webui/open-webui:main\n"
                "```\n\n"
                "Then visit `http://localhost:3000` in your browser.\n\n"
                "## Connect to Ollama\n\n"
                "1. Make sure Ollama is running (`ollama serve`)\n"
                "2. Open WebUI auto-detects Ollama at `http://localhost:11434`\n"
                "3. Select a model from the dropdown and start chatting\n\n"
                "## Features\n\n"
                "- ChatGPT-like interface for local models\n"
                "- Multi-model support (switch between models)\n"
                "- Conversation history and search\n"
                "- Document upload and RAG\n"
                "- User management and access control"
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Docker installed\n"
                "- Ollama running locally (or compatible API)\n"
                "- 4GB RAM for the UI\n"
                "- Modern web browser"
            ),
            "platforms": ["linux", "macos", "docker"],
            "difficulty": "intermediate",
            "pricing_model": "free",
            "is_featured": True,
            "status": "published",
            "github_stars": 65000,
            "community_rating": 4.6,
        },
        # ---- 4. PrivateGPT ----
        {
            "slug": "privategpt",
            "name": "PrivateGPT",
            "description": "Ask questions about your documents using AI, 100% privately. No data leaves your machine.",
            "github_url": "https://github.com/zylon-ai/private-gpt",
            "website_url": "https://privategpt.dev",
            "docs_url": "https://docs.privategpt.dev",
            "categories": ["rag", "document-qa", "private-ai"],
            "tags": ["ai", "rag", "documents", "privacy", "self-hosted"],
            "sectors": ["ngo", "business", "academic"],
            "license_type": "Apache-2.0",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Install\n\n"
                "```bash\n"
                "git clone https://github.com/zylon-ai/private-gpt\n"
                "cd private-gpt\n"
                "poetry install --extras \"ui llms-llama-cpp embeddings-huggingface vector-stores-qdrant\"\n"
                "```\n\n"
                "## Run\n\n"
                "```bash\n"
                "PGPT_PROFILES=local make run\n"
                "```\n\n"
                "Visit `http://localhost:8001` to access the UI.\n\n"
                "## Ingest Documents\n\n"
                "Upload PDFs, Word docs, or text files through the UI. PrivateGPT will:\n"
                "1. Parse and chunk the documents\n"
                "2. Create embeddings and store in a vector database\n"
                "3. Answer questions using only your documents as context\n\n"
                "All processing happens locally \u2014 no data leaves your machine."
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Python 3.11+\n"
                "- Poetry package manager\n"
                "- 16GB RAM minimum\n"
                "- GPU recommended for faster inference\n"
                "- 10GB+ free disk space"
            ),
            "platforms": ["linux", "macos", "docker"],
            "difficulty": "advanced",
            "pricing_model": "free",
            "is_featured": False,
            "status": "published",
            "github_stars": 55000,
            "community_rating": 4.3,
        },
        # ---- 5. Docling ----
        {
            "slug": "docling",
            "name": "Docling",
            "description": "AI-powered document parsing from IBM Research. Convert PDFs, Word docs, and images into structured data.",
            "github_url": "https://github.com/DS4SD/docling",
            "website_url": None,
            "docs_url": "https://ds4sd.github.io/docling/",
            "categories": ["document-parsing", "pdf", "data-extraction"],
            "tags": ["ai", "documents", "pdf", "parsing", "ibm"],
            "sectors": ["newsroom", "academic", "business", "ngo"],
            "license_type": "MIT",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Install\n\n"
                "```bash\n"
                "pip install docling\n"
                "```\n\n"
                "## Basic Usage\n\n"
                "```python\n"
                "from docling.document_converter import DocumentConverter\n\n"
                "converter = DocumentConverter()\n"
                "result = converter.convert(\"document.pdf\")\n"
                "print(result.document.export_to_markdown())\n"
                "```\n\n"
                "## Supported Formats\n\n"
                "- PDF (with OCR support)\n"
                "- Word (.docx)\n"
                "- PowerPoint (.pptx)\n"
                "- HTML\n"
                "- Images (with OCR)\n\n"
                "## Export Options\n\n"
                "- Markdown\n"
                "- JSON (structured)\n"
                "- Doctags (custom format)"
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Python 3.10+\n"
                "- 4GB RAM minimum\n"
                "- Optional: GPU for faster OCR"
            ),
            "platforms": ["linux", "macos", "windows"],
            "difficulty": "intermediate",
            "pricing_model": "free",
            "is_featured": False,
            "status": "published",
            "github_stars": 18000,
            "community_rating": 4.4,
        },
        # ---- 6. Label Studio ----
        {
            "slug": "label-studio",
            "name": "Label Studio",
            "description": "The most flexible open-source data labeling tool. Annotate text, images, audio, video, and more.",
            "github_url": "https://github.com/HumanSignal/label-studio",
            "website_url": "https://labelstud.io",
            "docs_url": "https://labelstud.io/guide/",
            "categories": ["data-annotation", "labeling", "ml-ops"],
            "tags": ["ai", "annotation", "labeling", "data", "machine-learning"],
            "sectors": ["academic", "business"],
            "license_type": "Apache-2.0",
            "deployment_type": "hybrid",
            "installation_guide": (
                "## Install\n\n"
                "```bash\n"
                "pip install label-studio\n"
                "```\n\n"
                "## Run\n\n"
                "```bash\n"
                "label-studio start\n"
                "```\n\n"
                "Visit `http://localhost:8080` to access the interface.\n\n"
                "## What You Can Label\n\n"
                "- Text (classification, NER, sentiment)\n"
                "- Images (bounding boxes, segmentation)\n"
                "- Audio (transcription, classification)\n"
                "- Video (object tracking)\n"
                "- HTML and time series data\n\n"
                "## Getting Started\n\n"
                "1. Create a project\n"
                "2. Choose a labeling template (or customise)\n"
                "3. Import your data\n"
                "4. Start labeling \u2014 or connect an ML backend for pre-annotations"
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Python 3.8+\n"
                "- 4GB RAM\n"
                "- Modern web browser\n"
                "- PostgreSQL recommended for production"
            ),
            "platforms": ["linux", "macos", "docker"],
            "difficulty": "intermediate",
            "pricing_model": "open_core",
            "is_featured": False,
            "status": "published",
            "github_stars": 20000,
            "community_rating": 4.2,
        },
        # ---- 7. Haystack ----
        {
            "slug": "haystack",
            "name": "Haystack",
            "description": "Build production-ready RAG pipelines, search systems, and AI applications with composable components.",
            "github_url": "https://github.com/deepset-ai/haystack",
            "website_url": "https://haystack.deepset.ai",
            "docs_url": "https://docs.haystack.deepset.ai",
            "categories": ["rag", "pipelines", "search", "llm-framework"],
            "tags": ["ai", "rag", "search", "pipelines", "nlp"],
            "sectors": ["newsroom", "business", "academic"],
            "license_type": "Apache-2.0",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Install\n\n"
                "```bash\n"
                "pip install haystack-ai\n"
                "```\n\n"
                "## Build a Simple RAG Pipeline\n\n"
                "```python\n"
                "from haystack import Pipeline\n"
                "from haystack.components.converters import TextFileToDocument\n"
                "from haystack.components.preprocessors import DocumentSplitter\n"
                "from haystack.components.writers import DocumentWriter\n"
                "from haystack.document_stores.in_memory import InMemoryDocumentStore\n\n"
                "# Index documents\n"
                "doc_store = InMemoryDocumentStore()\n"
                "indexing = Pipeline()\n"
                "indexing.add_component(\"converter\", TextFileToDocument())\n"
                "indexing.add_component(\"splitter\", DocumentSplitter(split_by=\"sentence\", split_length=3))\n"
                "indexing.add_component(\"writer\", DocumentWriter(doc_store))\n"
                "indexing.connect(\"converter\", \"splitter\")\n"
                "indexing.connect(\"splitter\", \"writer\")\n\n"
                "indexing.run({\"converter\": {\"sources\": [\"doc1.txt\", \"doc2.txt\"]}})\n"
                "```\n\n"
                "Haystack supports multiple LLM providers, vector databases, and retrieval strategies."
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Python 3.9+\n"
                "- 8GB RAM minimum\n"
                "- Vector database for production (Qdrant, Weaviate, or Pinecone)\n"
                "- LLM API key or local model"
            ),
            "platforms": ["linux", "macos", "docker"],
            "difficulty": "advanced",
            "pricing_model": "free",
            "is_featured": False,
            "status": "published",
            "github_stars": 18000,
            "community_rating": 4.5,
        },
        # ---- 8. ComfyUI ----
        {
            "slug": "comfyui",
            "name": "ComfyUI",
            "description": "A node-based interface for Stable Diffusion image generation. Build complex creative AI workflows visually.",
            "github_url": "https://github.com/comfyanonymous/ComfyUI",
            "website_url": None,
            "docs_url": "https://github.com/comfyanonymous/ComfyUI#readme",
            "categories": ["image-generation", "diffusion", "creative-ai"],
            "tags": ["ai", "images", "stable-diffusion", "creative", "workflow"],
            "sectors": ["newsroom", "business"],
            "license_type": "GPL-3.0",
            "deployment_type": "desktop",
            "installation_guide": (
                "## Install\n\n"
                "```bash\n"
                "git clone https://github.com/comfyanonymous/ComfyUI\n"
                "cd ComfyUI\n"
                "pip install -r requirements.txt\n"
                "```\n\n"
                "## Run\n\n"
                "```bash\n"
                "python main.py\n"
                "```\n\n"
                "Visit `http://127.0.0.1:8188` in your browser.\n\n"
                "## How It Works\n\n"
                "ComfyUI uses a node-based workflow editor for image generation:\n\n"
                "1. **Load a model** \u2014 drag a checkpoint loader node\n"
                "2. **Write a prompt** \u2014 add text encoding nodes\n"
                "3. **Generate** \u2014 connect to a sampler and run\n"
                "4. **Refine** \u2014 add upscaling, inpainting, or ControlNet nodes\n\n"
                "Workflows can be saved and shared as JSON files."
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- NVIDIA GPU with 4GB+ VRAM (strongly recommended)\n"
                "- Python 3.10+\n"
                "- 16GB RAM\n"
                "- 10GB+ disk space for models"
            ),
            "platforms": ["linux", "macos", "windows"],
            "difficulty": "advanced",
            "pricing_model": "free",
            "is_featured": False,
            "status": "published",
            "github_stars": 70000,
            "community_rating": 4.4,
        },
        # ---- 9. Briefer ----
        {
            "slug": "briefer",
            "name": "Briefer",
            "description": "AI-powered data notebooks with dashboards. Combine SQL, Python, and AI in one collaborative workspace.",
            "github_url": "https://github.com/briefercloud/briefer",
            "website_url": "https://briefer.cloud",
            "docs_url": "https://docs.briefer.cloud",
            "categories": ["notebooks", "data-dashboards", "analytics"],
            "tags": ["ai", "data", "notebooks", "dashboards", "analytics"],
            "sectors": ["business", "academic", "ngo"],
            "license_type": "Apache-2.0",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Quick Start with Docker\n\n"
                "```bash\n"
                "docker run -d -p 3000:3000 \\\n"
                "  -v briefer_data:/app/data \\\n"
                "  --name briefer \\\n"
                "  briefercloud/briefer\n"
                "```\n\n"
                "Visit `http://localhost:3000` to get started.\n\n"
                "## Features\n\n"
                "- AI-powered notebook interface\n"
                "- SQL and Python in one place\n"
                "- Auto-generated visualisations\n"
                "- Shareable dashboards\n"
                "- Scheduled reports"
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Docker installed\n"
                "- 4GB RAM minimum\n"
                "- Modern web browser"
            ),
            "platforms": ["linux", "docker"],
            "difficulty": "intermediate",
            "pricing_model": "open_core",
            "is_featured": False,
            "status": "published",
            "github_stars": 8000,
            "community_rating": 4.1,
        },
        # ---- 10. Stirling PDF ----
        {
            "slug": "stirling-pdf",
            "name": "Stirling PDF",
            "description": "A self-hosted PDF toolkit that handles everything \u2014 merge, split, OCR, convert, compress \u2014 all locally.",
            "github_url": "https://github.com/Stirling-Tools/Stirling-PDF",
            "website_url": "https://stirlingpdf.io",
            "docs_url": "https://docs.stirlingpdf.com",
            "categories": ["pdf", "document-tools", "utilities"],
            "tags": ["pdf", "documents", "tools", "self-hosted", "privacy"],
            "sectors": ["newsroom", "ngo", "business", "academic"],
            "license_type": "MIT",
            "deployment_type": "self_hosted",
            "installation_guide": (
                "## Quick Start with Docker\n\n"
                "```bash\n"
                "docker run -d -p 8080:8080 \\\n"
                "  -v ./data:/usr/share/tessdata \\\n"
                "  --name stirling-pdf \\\n"
                "  frooodle/s-pdf:latest\n"
                "```\n\n"
                "Visit `http://localhost:8080` for the web interface.\n\n"
                "## Features\n\n"
                "- Merge, split, rotate, and reorder PDF pages\n"
                "- Convert to/from PDF (images, Word, Excel, HTML)\n"
                "- OCR \u2014 make scanned PDFs searchable\n"
                "- Add or remove passwords\n"
                "- Compress PDFs to reduce file size\n"
                "- Add watermarks, page numbers, and signatures\n\n"
                "All processing happens locally \u2014 your documents never leave your server."
            ),
            "system_requirements": (
                "## Requirements\n\n"
                "- Docker installed (recommended)\n"
                "- Java 17+ for non-Docker install\n"
                "- 2GB RAM\n"
                "- Modern web browser"
            ),
            "platforms": ["linux", "macos", "windows", "docker"],
            "difficulty": "beginner",
            "pricing_model": "free",
            "is_featured": True,
            "status": "published",
            "github_stars": 55000,
            "community_rating": 4.6,
        },
    ])

    # ------------------------------------------------------------------ #
    # 9. Seed 3 new lesson modules                                       #
    # ------------------------------------------------------------------ #
    modules_tbl = sa.table(
        "lesson_modules",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("sector", sa.String),
        sa.column("difficulty", sa.String),
        sa.column("order", sa.Integer),
        sa.column("icon", sa.String),
        sa.column("prerequisites", postgresql.JSONB),
    )

    op.bulk_insert(modules_tbl, [
        {
            "slug": "hands-on-ai-tools",
            "name": "Hands-On AI Tools",
            "description": "Install and use real open-source AI tools from the Grounded App Directory. Move from theory to practice.",
            "sector": None,
            "difficulty": "intermediate",
            "order": 3,
            "icon": "command-line",
            "prerequisites": ["ai-foundations"],
        },
        {
            "slug": "ai-for-your-org",
            "name": "AI for Your Organisation",
            "description": "Apply AI tools to real organisational needs \u2014 find the right tool, build a proof of concept, and measure impact.",
            "sector": None,
            "difficulty": "intermediate",
            "order": 4,
            "icon": "building-office",
            "prerequisites": ["responsible-ai-use"],
        },
        {
            "slug": "advanced-ai-workflows",
            "name": "Advanced AI Workflows",
            "description": "Build multi-tool AI pipelines, self-host responsibly, and iterate on real-world workflows.",
            "sector": None,
            "difficulty": "advanced",
            "order": 5,
            "icon": "cog-6-tooth",
            "prerequisites": ["hands-on-ai-tools", "ai-for-your-org"],
        },
    ])

    # ------------------------------------------------------------------ #
    # 10. Seed 12 new lessons                                            #
    # ------------------------------------------------------------------ #
    conn = op.get_bind()
    mod3_id = conn.execute(sa.text("SELECT id FROM lesson_modules WHERE slug = 'hands-on-ai-tools'")).scalar()
    mod4_id = conn.execute(sa.text("SELECT id FROM lesson_modules WHERE slug = 'ai-for-your-org'")).scalar()
    mod5_id = conn.execute(sa.text("SELECT id FROM lesson_modules WHERE slug = 'advanced-ai-workflows'")).scalar()

    lessons_tbl = sa.table(
        "lessons",
        sa.column("module_id", postgresql.UUID),
        sa.column("slug", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("content_markdown", sa.Text),
        sa.column("learning_objectives", postgresql.JSONB),
        sa.column("task_type", sa.String),
        sa.column("task_prompt", sa.Text),
        sa.column("task_hints", postgresql.JSONB),
        sa.column("verification_type", sa.String),
        sa.column("token_reward", sa.Integer),
        sa.column("order", sa.Integer),
        sa.column("estimated_minutes", sa.Integer),
        sa.column("status", sa.String),
        sa.column("related_app_slugs", postgresql.JSONB),
        sa.column("related_tool_slugs", postgresql.JSONB),
        sa.column("recommended_level", sa.String),
        sa.column("sector_relevance", postgresql.JSONB),
    )

    op.bulk_insert(lessons_tbl, [
        # ================================================================ #
        # MODULE 3: Hands-On AI Tools                                      #
        # ================================================================ #

        # ---- Lesson 1: Run Your First Local LLM ----
        {
            "module_id": mod3_id,
            "slug": "hands-on-run-local-llm",
            "title": "Run Your First Local LLM",
            "description": "Download, install, and use a large language model that runs entirely on your own machine.",
            "content_markdown": (
                "## Run Your First Local LLM\n\n"
                "Most people experience AI through cloud services \u2014 ChatGPT, Claude, Gemini. "
                "You type a prompt, it travels to a data centre, a model processes it, and the "
                "response comes back over the internet. This works well, but it means your data "
                "leaves your machine and your organisation's control. For many teams, especially "
                "those handling sensitive information, that is a deal-breaker.\n\n"
                "Local large language models (LLMs) change this equation entirely. When you run "
                "a model locally, every part of the conversation stays on your hardware. No API "
                "calls, no data leaving your network, no subscription fees. The trade-off is that "
                "local models are typically smaller and less capable than the largest cloud models, "
                "but for many practical tasks \u2014 drafting, summarisation, brainstorming, code "
                "assistance \u2014 they are more than sufficient.\n\n"
                "### Why local matters\n\n"
                "There are three main reasons to run AI locally:\n\n"
                "1. **Privacy** \u2014 Sensitive documents, client data, and internal communications "
                "never leave your machine. This is critical for journalists protecting sources, "
                "NGOs handling vulnerable populations, and businesses with confidentiality obligations.\n"
                "2. **Cost** \u2014 After the initial setup, running a local model costs nothing per query. "
                "For high-volume use, this can be significantly cheaper than API-based services.\n"
                "3. **Control** \u2014 You choose the model, you control the updates, and you are not "
                "dependent on a third party's pricing changes or service availability.\n\n"
                "### What is Ollama?\n\n"
                "[Ollama](/apps/ollama) is a tool that makes running local LLMs as simple as "
                "running a single command. It handles downloading models, managing GPU memory, "
                "and exposing a local API \u2014 all without requiring you to understand the "
                "underlying machine learning infrastructure. Think of it as Docker for AI models.\n\n"
                "### How it works\n\n"
                "When you run `ollama run llama3.2`, Ollama downloads the model weights (a few "
                "gigabytes), loads them into memory, and starts an interactive chat session. The "
                "model runs on your CPU or GPU, and responses are generated locally. You can also "
                "use Ollama's API to integrate local AI into scripts, applications, or other tools."
            ),
            "learning_objectives": [
                "Install and run a local LLM using Ollama",
                "Compare local vs cloud AI capabilities",
                "Evaluate when local AI is preferable to cloud AI",
            ],
            "task_type": "action",
            "task_prompt": (
                "Download and install [Ollama](/apps/ollama) from the App Directory. "
                "Run a model (try `ollama run llama3.2`). Ask it a question related to your "
                "work. Then report: which model did you choose and why? What did you ask? "
                "How did the response compare to a cloud-based chatbot like ChatGPT?"
            ),
            "task_hints": [
                "Start with a smaller model like llama3.2 (3B) if your machine has limited RAM",
                "Compare the same question in ChatGPT or Claude to see the differences",
            ],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 1,
            "estimated_minutes": 20,
            "status": "published",
            "related_app_slugs": ["ollama"],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },

        # ---- Lesson 2: Transcribe Audio with AI ----
        {
            "module_id": mod3_id,
            "slug": "hands-on-transcribe-audio",
            "title": "Transcribe Audio with AI",
            "description": "Use open-source speech recognition to convert audio to text \u2014 no cloud required.",
            "content_markdown": (
                "## Transcribe Audio with AI\n\n"
                "Speech-to-text technology has improved dramatically in recent years. What once "
                "required expensive commercial software or tedious manual work can now be done "
                "with a single open-source command. For journalists transcribing interviews, "
                "researchers processing recorded sessions, or any professional who works with "
                "audio, AI transcription is one of the most immediately useful AI capabilities "
                "available today.\n\n"
                "### How AI transcription works\n\n"
                "Modern speech recognition models like Whisper are trained on hundreds of "
                "thousands of hours of audio paired with their transcriptions. The model learns "
                "patterns in speech \u2014 how words sound in different accents, how to handle "
                "background noise, and how to punctuate naturally. When you feed it new audio, "
                "it applies these learned patterns to produce a text transcript.\n\n"
                "### Why local transcription matters\n\n"
                "Cloud transcription services are convenient, but they require you to upload "
                "your audio to someone else's servers. For sensitive recordings \u2014 confidential "
                "interviews, legal depositions, medical consultations \u2014 this may not be "
                "acceptable. [Whisper](/apps/whisper) runs entirely on your own machine, so "
                "your audio never leaves your control.\n\n"
                "### Choosing a model size\n\n"
                "Whisper comes in five sizes, from `tiny` (fastest, least accurate) to `large` "
                "(slowest, most accurate). The `base` model offers a good starting balance \u2014 "
                "it runs quickly on most modern laptops and produces usable transcriptions for "
                "clear audio. If you are working with accented speech, background noise, or "
                "multiple speakers, you may want to step up to `medium` or `large`.\n\n"
                "### Practical tips\n\n"
                "- **File format**: Whisper accepts most audio formats (MP3, WAV, M4A, etc.) "
                "but works best with clear, mono audio.\n"
                "- **Language**: Whisper auto-detects language, but you can force a specific "
                "language with the `--language` flag for better accuracy.\n"
                "- **Output formats**: By default Whisper produces plain text, but it can also "
                "output SRT subtitles, VTT, and timestamped JSON."
            ),
            "learning_objectives": [
                "Install and use Whisper for speech-to-text",
                "Evaluate transcription accuracy against manual methods",
                "Identify practical use cases for AI transcription in your work",
            ],
            "task_type": "action",
            "task_prompt": (
                "Install [Whisper](/apps/whisper) using the guide in the App Directory. "
                "Transcribe a short audio file \u2014 an interview, meeting recording, or podcast "
                "clip. Report: how accurate was the transcription? What errors did you notice? "
                "How long did it take compared to manual transcription? Would you use this in "
                "your workflow?"
            ),
            "task_hints": [
                "Use the `base` model for speed or `medium` for better accuracy",
                "Try a file with background noise or multiple speakers to test robustness",
            ],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 2,
            "estimated_minutes": 25,
            "status": "published",
            "related_app_slugs": ["whisper"],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "academic", "ngo"],
        },

        # ---- Lesson 3: Build a Private Chat Interface ----
        {
            "module_id": mod3_id,
            "slug": "hands-on-private-chat",
            "title": "Build a Private Chat Interface",
            "description": "Set up a ChatGPT-like interface for local AI models that keeps all data on your machine.",
            "content_markdown": (
                "## Build a Private Chat Interface\n\n"
                "Running a local LLM through the command line works, but it is not the most "
                "user-friendly experience \u2014 especially if you want colleagues to use it too. "
                "What most teams actually need is a familiar, ChatGPT-like web interface that "
                "connects to local models instead of cloud APIs. That is exactly what "
                "[Open WebUI](/apps/open-webui) provides.\n\n"
                "### Why organisations need private AI interfaces\n\n"
                "Many organisations want the convenience of ChatGPT but cannot accept the data "
                "privacy implications. Legal teams worry about client privilege, HR teams handle "
                "employee data, and research teams work with pre-publication findings. A private "
                "chat interface solves this by keeping the familiar user experience while routing "
                "all processing through local models.\n\n"
                "### What Open WebUI provides\n\n"
                "Open WebUI is a full-featured chat interface that connects to "
                "[Ollama](/apps/ollama) running on your machine or network. It provides "
                "conversation history, the ability to switch between different models, document "
                "upload for basic RAG (retrieval-augmented generation), and even user management "
                "if you want to share it with a small team. The interface is polished and "
                "responsive \u2014 most users cannot tell the difference from a commercial product.\n\n"
                "### The architecture\n\n"
                "The setup is simple: Ollama runs in the background serving your chosen models, "
                "and Open WebUI provides the web frontend. Open WebUI talks to Ollama through "
                "its local API (port 11434 by default). Both run on the same machine, so data "
                "never touches the internet. If you use the Docker installation, everything is "
                "contained and easy to start or stop.\n\n"
                "### When this makes sense\n\n"
                "This setup is ideal for small teams who want to experiment with AI privately, "
                "organisations with strict data handling policies, and anyone who wants to "
                "prototype AI workflows before committing to a commercial service. The main "
                "limitation is performance \u2014 local models on typical hardware are slower than "
                "cloud services, and the models themselves are smaller. But for many tasks, "
                "the trade-off is well worth it."
            ),
            "learning_objectives": [
                "Deploy a private chat interface using Open WebUI",
                "Compare self-hosted AI tools to commercial alternatives",
                "Assess the trade-offs of self-hosting vs cloud AI",
            ],
            "task_type": "action",
            "task_prompt": (
                "Set up [Open WebUI](/apps/open-webui) connected to [Ollama](/apps/ollama). "
                "Have a conversation about a real work task \u2014 something you would normally "
                "use ChatGPT for. Describe: what was the setup experience like? How does the "
                "interface compare to commercial tools? What features would you want that are "
                "missing?"
            ),
            "task_hints": [
                "Open WebUI's Docker one-liner is the fastest setup path",
                "Make sure Ollama is running first with at least one model downloaded",
            ],
            "verification_type": "ai_review",
            "token_reward": 3,
            "order": 3,
            "estimated_minutes": 30,
            "status": "published",
            "related_app_slugs": ["open-webui", "ollama"],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "ngo", "business"],
        },

        # ---- Lesson 4: Process Documents with AI ----
        {
            "module_id": mod3_id,
            "slug": "hands-on-process-documents",
            "title": "Process Documents with AI",
            "description": "Use AI-powered tools to parse, convert, and extract information from real documents.",
            "content_markdown": (
                "## Process Documents with AI\n\n"
                "Every organisation runs on documents \u2014 reports, contracts, research papers, "
                "invoices, policies. Working with these documents often involves tedious manual "
                "tasks: extracting data from PDFs, converting between formats, merging files, "
                "or making scanned documents searchable. AI-powered document tools can automate "
                "much of this work.\n\n"
                "### The document processing landscape\n\n"
                "Document processing tools fall into two broad categories. First, there are "
                "**AI parsing tools** like [Docling](/apps/docling) that use machine learning to "
                "understand document structure \u2014 they can identify headings, tables, lists, and "
                "paragraphs, then export them as structured data. This is powerful for extracting "
                "information from complex PDFs or converting research papers into machine-readable "
                "formats.\n\n"
                "Second, there are **document manipulation tools** like "
                "[Stirling PDF](/apps/stirling-pdf) that handle the mechanical operations: "
                "merging, splitting, compressing, adding OCR, converting formats. These tools "
                "may use AI internally (especially for OCR), but their primary value is in "
                "automating repetitive document tasks.\n\n"
                "### When to use which\n\n"
                "Use an AI parsing tool when you need to **extract and understand** the content "
                "of a document \u2014 for example, pulling tables from a PDF report into a spreadsheet, "
                "or converting a policy document into structured JSON for analysis. Use a document "
                "manipulation tool when you need to **transform** documents \u2014 merging meeting notes "
                "into a single PDF, compressing large files for email, or adding OCR to a batch "
                "of scanned documents.\n\n"
                "### Privacy advantage\n\n"
                "Both Docling and Stirling PDF run entirely on your own machine. This means you "
                "can process confidential contracts, internal reports, and sensitive data without "
                "uploading anything to a third-party service. For organisations with data handling "
                "requirements, this is a significant advantage over cloud-based alternatives.\n\n"
                "### Getting started\n\n"
                "If you are new to document processing tools, start with Stirling PDF \u2014 its web "
                "interface is intuitive and you can be productive within minutes. If you need "
                "programmatic document parsing for a data pipeline or research project, Docling "
                "is the better choice."
            ),
            "learning_objectives": [
                "Use an open-source tool for document processing",
                "Evaluate output quality for real work documents",
                "Identify time-saving opportunities in your document workflows",
            ],
            "task_type": "action",
            "task_prompt": (
                "Choose either [Docling](/apps/docling) for AI-powered document parsing or "
                "[Stirling PDF](/apps/stirling-pdf) for PDF manipulation. Process a real document "
                "from your work. Report: what did you process? What was the output quality? How "
                "could this tool save time in your regular workflow? What limitations did you "
                "encounter?"
            ),
            "task_hints": [
                "Stirling PDF is easier to start with if you just need PDF operations",
                "Docling is better for extracting structured data from complex documents",
            ],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 4,
            "estimated_minutes": 20,
            "status": "published",
            "related_app_slugs": ["docling", "stirling-pdf"],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "academic", "business", "ngo"],
        },

        # ================================================================ #
        # MODULE 4: AI for Your Organisation                               #
        # ================================================================ #

        # ---- Lesson 5: Find the Right AI Tool ----
        {
            "module_id": mod4_id,
            "slug": "org-find-right-tool",
            "title": "Find the Right AI Tool",
            "description": "Learn to systematically evaluate AI tools using the Grounded platform's CDI framework.",
            "content_markdown": (
                "## Find the Right AI Tool\n\n"
                "One of the biggest challenges in adopting AI is not the technology itself \u2014 "
                "it is choosing the right tool from an overwhelming number of options. New AI "
                "tools launch every week, each claiming to revolutionise a different aspect of "
                "work. Without a systematic approach to evaluation, teams either get stuck in "
                "analysis paralysis or adopt whatever tool is trending on social media.\n\n"
                "### The CDI framework\n\n"
                "Grounded uses a CDI scoring system to help you evaluate tools objectively. CDI "
                "stands for **Cost**, **Difficulty**, and **Invasiveness** \u2014 three dimensions "
                "that matter more than marketing promises when deciding whether a tool is right "
                "for your organisation.\n\n"
                "- **Cost** measures the total expense of adopting a tool, including subscription "
                "fees, infrastructure costs, and the time investment required for setup.\n"
                "- **Difficulty** measures how hard the tool is to learn and integrate into "
                "existing workflows. A tool might be powerful, but if it takes weeks to set up, "
                "that matters.\n"
                "- **Invasiveness** measures how much the tool requires you to change your "
                "existing processes, share your data, or lock into a vendor's ecosystem.\n\n"
                "### Cloud vs self-hosted\n\n"
                "Every tool comes with a hosting decision. Cloud tools are faster to start but "
                "give you less control. Self-hosted tools take more effort to set up but keep "
                "your data under your control. The [App Directory](/apps/) focuses on self-hosted "
                "and open-source options, while the [Tools Directory](/tools) covers both cloud "
                "and self-hosted tools.\n\n"
                "### How to evaluate systematically\n\n"
                "Start with the problem, not the tool. Write down the specific task you need to "
                "improve, then look for tools that address that task. Compare at least three "
                "options before committing. Check CDI scores, read the documentation, and \u2014 "
                "crucially \u2014 try the tool on a real task before making a recommendation to "
                "your team."
            ),
            "learning_objectives": [
                "Use CDI scores to evaluate AI tools objectively",
                "Compare cloud and self-hosted AI options",
                "Make an evidence-based tool recommendation",
            ],
            "task_type": "exploration",
            "task_prompt": (
                "Go to the [Tools Directory](/tools) and find 3 tools relevant to your work. "
                "Compare their CDI scores (Cost, Difficulty, Invasiveness). Then check the "
                "[App Directory](/apps/) for any self-hosted alternatives. Report: which tools "
                "did you compare? What did the CDI scores reveal? Which tool would you recommend "
                "to a colleague and why?"
            ),
            "task_hints": [
                "Filter by your sector or use case for more relevant results",
                "Low CDI scores indicate easier adoption \u2014 start there if you're new",
            ],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 1,
            "estimated_minutes": 15,
            "status": "published",
            "related_app_slugs": [],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },

        # ---- Lesson 6: Build a Proof of Concept ----
        {
            "module_id": mod4_id,
            "slug": "org-build-poc",
            "title": "Build a Proof of Concept",
            "description": "Take an AI tool from the App Directory and build a working prototype for a real use case.",
            "content_markdown": (
                "## Build a Proof of Concept\n\n"
                "A proof of concept (PoC) is a small, time-boxed experiment that answers one "
                "question: does this tool actually work for our specific use case? A good PoC is "
                "not a full implementation \u2014 it is a focused test that gives you enough evidence "
                "to make a go/no-go decision.\n\n"
                "### How to scope a PoC\n\n"
                "The most common mistake in AI adoption is trying to do too much at once. A good "
                "PoC focuses on a single use case, uses real data, and has clear success criteria. "
                "For example, instead of 'we want to use AI for all our document processing', a "
                "good PoC scope would be 'we want to test whether Whisper can transcribe our "
                "weekly team meetings with 90% accuracy'.\n\n"
                "### The go/no-go framework\n\n"
                "Before you start building, define what success looks like. Ask three questions:\n\n"
                "1. **Does it work?** \u2014 Can the tool perform the task at an acceptable quality level?\n"
                "2. **Is it practical?** \u2014 Can your team realistically set up and maintain this tool?\n"
                "3. **Is it worth it?** \u2014 Does the time/money saved justify the setup effort?\n\n"
                "If the answer to all three is yes, you have a green light. If any answer is no, "
                "you have specific, actionable reasons why \u2014 which is much more useful than a "
                "vague feeling that 'it didn't work out'.\n\n"
                "### Time-boxing\n\n"
                "Set a hard time limit for your PoC \u2014 typically 2-4 hours for a single tool. "
                "If you cannot get a basic version working within that time, the tool is either "
                "too complex for your current needs or its documentation is inadequate. Both are "
                "valid findings.\n\n"
                "### Setting success criteria\n\n"
                "Write down 2-3 measurable criteria before you start. Examples: 'Transcription "
                "accuracy above 85%', 'Setup time under 30 minutes', 'Can process our standard "
                "report format without errors'. This prevents the PoC from becoming an open-ended "
                "exploration."
            ),
            "learning_objectives": [
                "Scope and execute a focused AI proof of concept",
                "Follow installation documentation independently",
                "Make a go/no-go recommendation based on evidence",
            ],
            "task_type": "action",
            "task_prompt": (
                "Pick one app from the [App Directory](/apps/) that could solve a real problem "
                "in your organisation. Follow its installation guide to get it running. Build "
                "a minimal proof of concept for one specific use case. Report: what did you "
                "build? What worked well? What didn't? Would you recommend your organisation "
                "invest further in this tool?"
            ),
            "task_hints": [
                "Start with the simplest possible use case \u2014 you can expand later",
                "Time-box your setup to 30 minutes \u2014 if it takes longer, note that as a finding",
            ],
            "verification_type": "ai_review",
            "token_reward": 3,
            "order": 2,
            "estimated_minutes": 45,
            "status": "published",
            "related_app_slugs": [],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },

        # ---- Lesson 7: Measure AI Impact ----
        {
            "module_id": mod4_id,
            "slug": "org-measure-impact",
            "title": "Measure AI Impact",
            "description": "Define meaningful KPIs and build a measurement plan for your AI initiative.",
            "content_markdown": (
                "## Measure AI Impact\n\n"
                "AI adoption without measurement is just expensive experimentation. To justify "
                "ongoing investment \u2014 whether that is time, money, or organisational attention \u2014 "
                "you need concrete evidence that AI is delivering value. This lesson teaches "
                "you how to define meaningful metrics and build a simple measurement plan.\n\n"
                "### Why measurement matters\n\n"
                "Without measurement, AI projects tend to drift. Teams adopt tools because they "
                "are interesting, not because they solve real problems. Managers approve budgets "
                "based on hype rather than evidence. And when budget cuts come, AI projects are "
                "the first to go because nobody can demonstrate their value. Good measurement "
                "prevents all of this.\n\n"
                "### Types of AI KPIs\n\n"
                "Useful AI metrics fall into four categories:\n\n"
                "- **Efficiency metrics** \u2014 Time saved per task, tasks completed per hour, "
                "documents processed per day. These are the easiest to measure and often the "
                "most compelling to stakeholders.\n"
                "- **Quality metrics** \u2014 Error rates, accuracy scores, human review rates. "
                "AI might be fast but produce low-quality output \u2014 you need to measure both.\n"
                "- **Cost metrics** \u2014 API costs, infrastructure expenses, total cost per output "
                "compared to manual processes.\n"
                "- **Adoption metrics** \u2014 How many team members are using the tool, how often, "
                "and for what tasks. Low adoption is a signal that something is wrong.\n\n"
                "### The before/after framework\n\n"
                "The simplest measurement approach is before/after comparison. Measure how long "
                "a task takes and how accurate the output is without AI, then measure the same "
                "things with AI. The difference is your impact. Document both carefully \u2014 "
                "anecdotal claims like 'it feels faster' are not evidence.\n\n"
                "### Common pitfalls\n\n"
                "Avoid measuring only what is easy to count. Time saved is important, but if "
                "quality drops, the net impact may be negative. Avoid cherry-picking successful "
                "examples \u2014 include failures in your measurement. And be honest about setup "
                "costs: if it took 20 hours to save 5 minutes per day, the payback period matters."
            ),
            "learning_objectives": [
                "Define measurable KPIs for an AI initiative",
                "Create a practical measurement plan",
                "Distinguish between efficiency and quality metrics",
            ],
            "task_type": "reflection",
            "task_prompt": (
                "For the AI tool or proof of concept you explored in previous lessons, define "
                "3 measurable KPIs. Examples: time saved per task, accuracy improvement, cost "
                "reduction, user satisfaction. Create a simple measurement plan: what will you "
                "measure, how will you measure it, and over what timeframe?"
            ),
            "task_hints": [
                "Good KPIs are specific and measurable \u2014 'saves time' is vague, '20 minutes saved per report' is specific",
                "Include at least one quality metric, not just efficiency",
            ],
            "verification_type": "ai_review",
            "token_reward": 2,
            "order": 3,
            "estimated_minutes": 20,
            "status": "published",
            "related_app_slugs": [],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },

        # ---- Lesson 8: Present AI to Stakeholders ----
        {
            "module_id": mod4_id,
            "slug": "org-present-stakeholders",
            "title": "Present AI to Stakeholders",
            "description": "Communicate AI value to decision-makers using clear, jargon-free language.",
            "content_markdown": (
                "## Present AI to Stakeholders\n\n"
                "The ability to communicate AI value to non-technical decision-makers is one "
                "of the most underrated skills in AI adoption. Many promising AI initiatives "
                "fail not because the technology does not work, but because the people who "
                "control budgets and priorities do not understand what it does or why it matters.\n\n"
                "### Communicating AI to non-technical audiences\n\n"
                "The biggest mistake people make when presenting AI to stakeholders is leading "
                "with the technology. Managers and board members do not care about model "
                "architectures, parameter counts, or benchmark scores. They care about outcomes: "
                "what problem does this solve, how much does it cost, and what are the risks?\n\n"
                "### Framing value\n\n"
                "Frame AI value in terms your audience already understands. Instead of 'we "
                "deployed a local LLM for document processing', say 'we reduced report "
                "preparation time from 4 hours to 45 minutes using a privacy-safe AI tool "
                "that costs nothing to run'. Translate technical capabilities into business "
                "outcomes: time saved, costs reduced, quality improved, risks mitigated.\n\n"
                "### Addressing fears honestly\n\n"
                "Stakeholders often have legitimate concerns about AI: job displacement, data "
                "privacy, liability, and reputational risk. Address these head-on rather than "
                "dismissing them. Acknowledge the limitations you found during testing. Explain "
                "the safeguards you have in place. Stakeholders trust people who are honest "
                "about risks more than people who only present the upside.\n\n"
                "### The one-page briefing structure\n\n"
                "A good AI briefing fits on one page and follows this structure:\n\n"
                "1. **The problem** \u2014 What task or pain point are we addressing? (2 sentences)\n"
                "2. **What we tested** \u2014 Which tool, on what data, for how long? (2-3 sentences)\n"
                "3. **Results** \u2014 What worked, with at least one specific number. (2-3 sentences)\n"
                "4. **Risks and limitations** \u2014 What did not work, what could go wrong. (2-3 sentences)\n"
                "5. **Recommendation** \u2014 Should we invest further? What would the next step be? (1-2 sentences)\n\n"
                "If a non-technical person cannot understand your briefing in three minutes, "
                "it needs to be simpler."
            ),
            "learning_objectives": [
                "Write a clear AI briefing for non-technical stakeholders",
                "Frame AI value in terms of organisational outcomes",
                "Address risks and limitations honestly",
            ],
            "task_type": "action",
            "task_prompt": (
                "Draft a 1-page AI briefing for your manager, board, or team lead. Include: "
                "what you tested, what the results were, what the risks are (be honest), and "
                "your recommendation. Use plain language \u2014 no jargon. If a non-technical "
                "person can't understand it in 3 minutes, simplify further."
            ),
            "task_hints": [
                "Lead with the business problem, not the technology",
                "Include one specific number or result from your testing",
            ],
            "verification_type": "ai_review",
            "token_reward": 3,
            "order": 4,
            "estimated_minutes": 30,
            "status": "published",
            "related_app_slugs": [],
            "related_tool_slugs": [],
            "recommended_level": "intermediate",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },

        # ================================================================ #
        # MODULE 5: Advanced AI Workflows                                  #
        # ================================================================ #

        # ---- Lesson 9: Build a RAG Pipeline ----
        {
            "module_id": mod5_id,
            "slug": "advanced-build-rag",
            "title": "Build a RAG Pipeline",
            "description": "Create a document question-answering system using retrieval-augmented generation.",
            "content_markdown": (
                "## Build a RAG Pipeline\n\n"
                "Retrieval-Augmented Generation (RAG) is one of the most practical AI patterns "
                "available today. It solves a fundamental problem with large language models: "
                "they do not know about your specific documents. A RAG pipeline bridges this gap "
                "by retrieving relevant information from your own documents and feeding it to an "
                "LLM as context, so the model can answer questions about your data accurately.\n\n"
                "### How RAG works\n\n"
                "A RAG pipeline has three stages:\n\n"
                "1. **Indexing** \u2014 Your documents are split into chunks, converted into numerical "
                "representations (embeddings), and stored in a vector database.\n"
                "2. **Retrieval** \u2014 When you ask a question, the system converts your question "
                "into an embedding and finds the most similar document chunks.\n"
                "3. **Generation** \u2014 The retrieved chunks are passed to an LLM along with your "
                "question, and the model generates an answer grounded in your actual documents.\n\n"
                "This means the model's responses are based on your data rather than its general "
                "training knowledge, which dramatically reduces hallucination for domain-specific "
                "questions.\n\n"
                "### Haystack vs PrivateGPT\n\n"
                "[Haystack](/apps/haystack) is a modular framework for building custom RAG "
                "pipelines. It gives you control over every component \u2014 which document parser "
                "to use, which embedding model, which vector database, which LLM. This "
                "flexibility is powerful but requires more technical skill to set up.\n\n"
                "[PrivateGPT](/apps/privategpt) is an all-in-one solution that gets you from "
                "zero to a working document QA system quickly. It bundles all the components "
                "together and provides a web UI for uploading documents and asking questions. "
                "The trade-off is less customisation, but much faster time to first result.\n\n"
                "### When to use RAG\n\n"
                "RAG is ideal when you need to answer questions about a specific body of "
                "documents \u2014 internal policies, research papers, legal contracts, historical "
                "archives. It works best with well-structured, text-heavy documents. It is less "
                "effective with highly visual content, spreadsheets, or documents that require "
                "complex reasoning across many pages.\n\n"
                "### Tips for good results\n\n"
                "- Start with well-structured documents (reports, policies, manuals).\n"
                "- Ask specific questions rather than broad ones.\n"
                "- If accuracy matters, always verify the source citations the system provides."
            ),
            "learning_objectives": [
                "Set up a RAG pipeline with real documents",
                "Evaluate retrieval-augmented generation accuracy",
                "Identify document types and queries best suited to RAG",
            ],
            "task_type": "action",
            "task_prompt": (
                "Set up either [Haystack](/apps/haystack) or [PrivateGPT](/apps/privategpt). "
                "Index at least 5 documents from your work \u2014 reports, policies, manuals, or "
                "research papers. Ask 3 questions that require information from those documents. "
                "Report: how accurate were the answers? Did it correctly cite sources? What types "
                "of questions worked well and which didn't?"
            ),
            "task_hints": [
                "PrivateGPT is easier to get running quickly \u2014 Haystack gives you more control",
                "Start with well-structured documents like reports or policies for best results",
            ],
            "verification_type": "ai_review",
            "token_reward": 4,
            "order": 1,
            "estimated_minutes": 60,
            "status": "published",
            "related_app_slugs": ["haystack", "privategpt"],
            "related_tool_slugs": [],
            "recommended_level": "advanced",
            "sector_relevance": ["business", "academic", "newsroom"],
        },

        # ---- Lesson 10: Automate a Workflow ----
        {
            "module_id": mod5_id,
            "slug": "advanced-automate-workflow",
            "title": "Automate a Workflow",
            "description": "Design a multi-step AI workflow with human checkpoints for a task you do repeatedly.",
            "content_markdown": (
                "## Automate a Workflow\n\n"
                "Individual AI tools are useful, but the real productivity gains come from "
                "combining multiple tools into automated workflows. A workflow takes a repetitive "
                "multi-step task and turns it into a pipeline where AI handles the mechanical "
                "parts and humans review the critical decisions.\n\n"
                "### Multi-step AI workflows\n\n"
                "Most real-world tasks involve multiple steps. Summarising a meeting, for "
                "example, might involve: transcribing the audio (Whisper), extracting action "
                "items (an LLM), formatting the notes (a template), and sending them to the "
                "team (an email integration). Each step can be automated, but the overall "
                "pipeline needs to be designed thoughtfully.\n\n"
                "### Orchestration patterns\n\n"
                "There are three common patterns for AI workflows:\n\n"
                "1. **Sequential** \u2014 Each step feeds into the next. Simple and predictable, but "
                "if one step fails, the whole pipeline stops.\n"
                "2. **Branching** \u2014 The workflow takes different paths based on conditions. For "
                "example, if a document is in a foreign language, route it through translation "
                "first.\n"
                "3. **Review loop** \u2014 AI produces output, a human reviews it, and the workflow "
                "continues or reverts based on the review. This is the most robust pattern for "
                "high-stakes tasks.\n\n"
                "### Human-in-the-loop\n\n"
                "The most dangerous mistake in AI automation is removing human oversight entirely. "
                "AI models make mistakes \u2014 and those mistakes can compound across a multi-step "
                "pipeline. A human checkpoint at the highest-risk step (usually where the output "
                "goes to an external audience or makes a consequential decision) is essential. "
                "The goal is not to slow down the process but to catch errors before they have "
                "consequences.\n\n"
                "### When to automate\n\n"
                "Not every task should be automated. Automation is worth the effort when: you "
                "do the task at least weekly, the task has clear inputs and outputs, the "
                "consequences of AI errors are manageable, and you have the time to set up and "
                "test the pipeline. If you only do a task once a quarter, manual work with AI "
                "assistance is usually more practical than full automation."
            ),
            "learning_objectives": [
                "Design a multi-step AI workflow with appropriate checkpoints",
                "Identify risks in automated processes",
                "Apply human-in-the-loop principles to workflow design",
            ],
            "task_type": "action",
            "task_prompt": (
                "Design a multi-step AI workflow for a task you do repeatedly. Use the "
                "[Workflow Templates](/workflow-templates) feature in Grounded for inspiration, "
                "or design your own. Your workflow must have at least 3 steps and at least one "
                "human review checkpoint. Report: what is the workflow? Where is the human "
                "checkpoint? What could go wrong if the human step were removed?"
            ),
            "task_hints": [
                "Start with a task you already know well \u2014 automation of poorly understood processes often fails",
                "The human checkpoint should be at the highest-risk step",
            ],
            "verification_type": "ai_review",
            "token_reward": 3,
            "order": 2,
            "estimated_minutes": 45,
            "status": "published",
            "related_app_slugs": [],
            "related_tool_slugs": [],
            "recommended_level": "advanced",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },

        # ---- Lesson 11: Self-Host AI Responsibly ----
        {
            "module_id": mod5_id,
            "slug": "advanced-self-host-responsibly",
            "title": "Self-Host AI Responsibly",
            "description": "Deploy AI tools on your own infrastructure with proper security and access controls.",
            "content_markdown": (
                "## Self-Host AI Responsibly\n\n"
                "Self-hosting AI tools gives you full control over your data and infrastructure. "
                "But with that control comes responsibility. A poorly secured self-hosted AI "
                "deployment can be worse than using a commercial cloud service, because you are "
                "now responsible for security, access control, updates, and data protection "
                "yourself.\n\n"
                "### Security considerations\n\n"
                "When you deploy an AI tool on your own infrastructure, you need to think about "
                "several layers of security:\n\n"
                "- **Network access** \u2014 Who can reach the service? If you run Open WebUI on a "
                "server, is it accessible from the internet or only from your internal network? "
                "Use firewalls, VPNs, or reverse proxies to control access.\n"
                "- **Authentication** \u2014 Does the tool require login? [Open WebUI](/apps/open-webui) "
                "has built-in user management. [Stirling PDF](/apps/stirling-pdf) can be placed "
                "behind a reverse proxy with authentication. [Ollama](/apps/ollama) has no "
                "built-in auth \u2014 if exposed to a network, anyone can use it.\n"
                "- **Data storage** \u2014 Where does the tool store data? Conversation histories, "
                "uploaded documents, and generated outputs all need to be stored somewhere. "
                "Understand where, and ensure appropriate encryption and backup.\n\n"
                "### Access control\n\n"
                "Not everyone in your organisation needs the same level of access. Consider "
                "role-based access: administrators who can change settings, regular users who "
                "can use the tools, and potentially read-only users who can view outputs but "
                "not input new data. Even simple access controls are better than none.\n\n"
                "### Update practices\n\n"
                "Self-hosted tools need to be updated regularly. Security patches, bug fixes, "
                "and model updates all require your attention. Set a regular schedule \u2014 at "
                "least monthly \u2014 to check for updates. Docker-based deployments make this "
                "easier: pull the latest image, restart the container, and verify everything "
                "works.\n\n"
                "### Compliance\n\n"
                "Depending on your sector, you may have regulatory obligations around data "
                "processing. GDPR, HIPAA, and various national data protection laws all have "
                "requirements about how data is stored, processed, and deleted. Self-hosting "
                "can help you meet these requirements (because data stays within your control), "
                "but only if you implement the appropriate technical and organisational measures."
            ),
            "learning_objectives": [
                "Deploy an AI tool on controlled infrastructure",
                "Implement basic security controls for self-hosted AI",
                "Document a deployment with security considerations",
            ],
            "task_type": "action",
            "task_prompt": (
                "Deploy one tool from the [App Directory](/apps/) on infrastructure you control "
                "\u2014 your local machine, a team server, or a cloud VM. Document your security "
                "setup: how did you handle access control? Where is data stored? How will you "
                "handle updates? What risks remain, and what would you do differently in a "
                "production deployment?"
            ),
            "task_hints": [
                "Docker makes deployment easier but still requires network and access configuration",
                "Think about who else might need access and how you would manage credentials",
            ],
            "verification_type": "ai_review",
            "token_reward": 4,
            "order": 3,
            "estimated_minutes": 60,
            "status": "published",
            "related_app_slugs": ["ollama", "open-webui", "stirling-pdf"],
            "related_tool_slugs": [],
            "recommended_level": "advanced",
            "sector_relevance": ["newsroom", "ngo", "business"],
        },

        # ---- Lesson 12: Evaluate and Iterate ----
        {
            "module_id": mod5_id,
            "slug": "advanced-evaluate-iterate",
            "title": "Evaluate and Iterate",
            "description": "Systematically test your AI workflow on real data and improve it based on evidence.",
            "content_markdown": (
                "## Evaluate and Iterate\n\n"
                "Getting an AI tool or workflow running is only the first step. The difference "
                "between a toy demo and a production-ready system is systematic evaluation and "
                "iterative improvement. This lesson teaches you how to test your AI setup on "
                "real data, identify failure modes, and make targeted improvements.\n\n"
                "### Systematic evaluation\n\n"
                "To evaluate an AI workflow properly, you need to run it on a representative "
                "sample of real inputs \u2014 not just the examples that work well. Ten examples is "
                "a reasonable starting point for a quick evaluation. Track three things for each "
                "example:\n\n"
                "1. **Accuracy** \u2014 Was the output correct and usable? Score each example as "
                "fully usable, usable with edits, or not usable.\n"
                "2. **Time** \u2014 How long did the AI take compared to doing the task manually?\n"
                "3. **Failure mode** \u2014 When it went wrong, what specifically went wrong? "
                "Categorise failures: wrong content, wrong format, missing information, hallucinated "
                "content, etc.\n\n"
                "### Iteration frameworks\n\n"
                "Once you have evaluation data, identify the single most common failure mode and "
                "focus your improvement effort there. This is more effective than trying to fix "
                "everything at once. Common improvements include:\n\n"
                "- **Better prompts** \u2014 Adding more specific instructions or examples to the "
                "system prompt.\n"
                "- **Better preprocessing** \u2014 Cleaning or restructuring input data before it "
                "reaches the AI.\n"
                "- **Different model** \u2014 Switching to a larger or more specialised model for "
                "the task.\n"
                "- **Post-processing** \u2014 Adding a formatting or validation step after AI output.\n\n"
                "### Knowing when to stop\n\n"
                "Perfection is not the goal. AI workflows will always have some error rate. "
                "The question is whether the workflow is good enough to be useful and whether "
                "the error rate is acceptable for your context. A 90% accuracy rate might be "
                "excellent for draft generation but unacceptable for financial reporting. Define "
                "your threshold before you start iterating, so you know when to stop.\n\n"
                "### Measuring improvement\n\n"
                "After making a change, re-run a subset of your test examples (at least 5) "
                "and compare the results to your baseline. Did the change actually improve "
                "things, or did it just shift the failure modes? Document everything \u2014 both "
                "the change you made and its measured impact. This creates an improvement log "
                "that is invaluable when you need to justify continued investment or share "
                "learnings with other teams."
            ),
            "learning_objectives": [
                "Conduct systematic evaluation of an AI workflow",
                "Make evidence-based improvements to AI processes",
                "Measure the impact of iterative refinements",
            ],
            "task_type": "reflection",
            "task_prompt": (
                "Take any AI workflow or tool you set up during this course. Run it on 10 real "
                "examples from your work. Track: accuracy (how often was the output usable?), "
                "time taken (faster than manual?), and failures (what went wrong?). Then make "
                "one specific improvement based on your findings and re-run 5 examples. Report: "
                "what did you change, and did it measurably improve results?"
            ),
            "task_hints": [
                "Use a simple spreadsheet to track results across your 10 examples",
                "Focus your improvement on the most common failure mode",
            ],
            "verification_type": "ai_review",
            "token_reward": 4,
            "order": 4,
            "estimated_minutes": 45,
            "status": "published",
            "related_app_slugs": [],
            "related_tool_slugs": [],
            "recommended_level": "advanced",
            "sector_relevance": ["newsroom", "ngo", "business", "academic"],
        },
    ])


def downgrade():
    # Delete seeded data
    op.execute("DELETE FROM lessons WHERE slug LIKE 'hands-on-%' OR slug LIKE 'org-%' OR slug LIKE 'advanced-%'")
    op.execute("DELETE FROM lesson_modules WHERE slug IN ('hands-on-ai-tools', 'ai-for-your-org', 'advanced-ai-workflows')")
    op.execute("DELETE FROM open_source_apps WHERE slug IN ('whisper', 'ollama', 'open-webui', 'privategpt', 'docling', 'label-studio', 'haystack', 'comfyui', 'briefer', 'stirling-pdf')")

    # Drop lesson columns
    op.drop_constraint("ck_lesson_recommended_level", "lessons", type_="check")
    op.drop_column("lessons", "sector_relevance")
    op.drop_column("lessons", "recommended_level")
    op.drop_column("lessons", "related_tool_slugs")
    op.drop_column("lessons", "related_app_slugs")

    # Drop module column
    op.drop_column("lesson_modules", "prerequisites")

    # Drop app indexes
    op.execute("DROP INDEX IF EXISTS ix_open_source_apps_platforms_gin")
    op.drop_index("ix_open_source_apps_status_featured", "open_source_apps")
    op.drop_index("ix_open_source_apps_difficulty", "open_source_apps")
    op.drop_index("ix_open_source_apps_is_featured", "open_source_apps")
    op.drop_index("ix_open_source_apps_created_by", "open_source_apps")

    # Drop app columns
    op.drop_constraint("ck_open_source_apps_community_rating", "open_source_apps", type_="check")
    op.drop_column("open_source_apps", "last_verified_at")
    op.drop_column("open_source_apps", "community_rating")
    op.drop_column("open_source_apps", "github_stars")
