"""Whisper tool adapter — transcription via local Whisper CLI or API."""
from app.tool_adapters.base import BaseToolAdapter, ToolAction, HealthCheck, InstallStep


class WhisperAdapter(BaseToolAdapter):
    """Adapter for OpenAI Whisper running locally."""

    def get_slug(self) -> str:
        return "openai-whisper"

    def get_display_name(self) -> str:
        return "OpenAI Whisper"

    def get_base_url(self) -> str:
        # Whisper is primarily CLI-based; no default API port
        return "http://localhost:9000"

    def get_health_check(self) -> HealthCheck:
        # Whisper doesn't have a standard API server
        # Health check verifies the CLI is installed
        return HealthCheck(
            url="http://localhost:9000/health",
            method="GET",
            expected_status=200,
        )

    def get_actions(self) -> list[ToolAction]:
        return [
            ToolAction(
                name="transcribe",
                label="Transcribe Audio",
                description="Transcribe an audio file to text using Whisper locally.",
                parameters=[
                    {"name": "file", "type": "file", "label": "Audio File", "required": True,
                     "accept": ".mp3,.wav,.m4a,.mp4,.webm,.ogg,.flac"},
                    {"name": "model", "type": "select", "label": "Model Size", "required": False,
                     "options": [
                         {"value": "tiny", "label": "Tiny (fast, less accurate)"},
                         {"value": "base", "label": "Base (balanced)"},
                         {"value": "small", "label": "Small (good accuracy)"},
                         {"value": "medium", "label": "Medium (high accuracy)"},
                         {"value": "large", "label": "Large (best accuracy, slow)"},
                     ],
                     "default": "base"},
                    {"name": "language", "type": "text", "label": "Language (optional)", "required": False,
                     "placeholder": "e.g. en, fr, de (auto-detect if empty)"},
                ],
                endpoint="/transcribe",
                method="POST",
            ),
        ]

    def get_install_steps(self) -> list[InstallStep]:
        return [
            InstallStep(
                platform="macos",
                commands=[
                    "pip install openai-whisper",
                    "# Or via Homebrew:",
                    "brew install openai-whisper",
                ],
                notes="Requires Python 3.8+ and ffmpeg. Install ffmpeg with: brew install ffmpeg",
            ),
            InstallStep(
                platform="linux",
                commands=[
                    "pip install openai-whisper",
                    "sudo apt-get install ffmpeg",
                ],
                notes="Requires Python 3.8+. GPU support available with CUDA.",
            ),
            InstallStep(
                platform="windows",
                commands=[
                    "pip install openai-whisper",
                    "# Install ffmpeg from https://ffmpeg.org/download.html",
                ],
                notes="Requires Python 3.8+. Add ffmpeg to PATH.",
            ),
        ]
