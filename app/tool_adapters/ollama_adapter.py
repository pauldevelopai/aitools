"""Ollama tool adapter — chat, generate, list models via local Ollama API."""
from app.tool_adapters.base import BaseToolAdapter, ToolAction, HealthCheck, InstallStep


class OllamaAdapter(BaseToolAdapter):
    """Adapter for Ollama running on user's local machine."""

    def get_slug(self) -> str:
        return "ollama"

    def get_display_name(self) -> str:
        return "Ollama"

    def get_base_url(self) -> str:
        return "http://localhost:11434"

    def get_health_check(self) -> HealthCheck:
        return HealthCheck(url="http://localhost:11434/api/tags")

    def get_actions(self) -> list[ToolAction]:
        return [
            ToolAction(
                name="list_models",
                label="List Models",
                description="See which models are downloaded and available locally.",
                endpoint="/api/tags",
                method="GET",
            ),
            ToolAction(
                name="pull_model",
                label="Pull Model",
                description="Download a model to your local machine.",
                parameters=[
                    {"name": "name", "type": "text", "label": "Model name", "required": True,
                     "placeholder": "e.g. llama3.1, mistral, gemma2"},
                ],
                endpoint="/api/pull",
                method="POST",
            ),
            ToolAction(
                name="generate",
                label="Generate Text",
                description="Generate text with a prompt using a local model.",
                parameters=[
                    {"name": "model", "type": "text", "label": "Model", "required": True,
                     "placeholder": "e.g. llama3.1"},
                    {"name": "prompt", "type": "textarea", "label": "Prompt", "required": True,
                     "placeholder": "Enter your prompt..."},
                    {"name": "stream", "type": "hidden", "label": "Stream", "required": False,
                     "default": False},
                ],
                endpoint="/api/generate",
                method="POST",
            ),
            ToolAction(
                name="chat",
                label="Chat",
                description="Have a conversation with a local model.",
                parameters=[
                    {"name": "model", "type": "text", "label": "Model", "required": True,
                     "placeholder": "e.g. llama3.1"},
                    {"name": "content", "type": "textarea", "label": "Message", "required": True,
                     "placeholder": "Type your message..."},
                    {"name": "stream", "type": "hidden", "label": "Stream", "required": False,
                     "default": False},
                ],
                endpoint="/api/chat",
                method="POST",
            ),
        ]

    def get_install_steps(self) -> list[InstallStep]:
        return [
            InstallStep(
                platform="macos",
                commands=["curl -fsSL https://ollama.com/install.sh | sh"],
                notes="Or download from ollama.com. Requires macOS 11+.",
            ),
            InstallStep(
                platform="linux",
                commands=["curl -fsSL https://ollama.com/install.sh | sh"],
                notes="Supports Ubuntu 18.04+, Debian 10+, Fedora 35+.",
            ),
            InstallStep(
                platform="windows",
                commands=["Download installer from ollama.com/download/windows"],
                notes="Requires Windows 10+. Run the downloaded installer.",
            ),
            InstallStep(
                platform="docker",
                commands=["docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama"],
                notes="GPU acceleration available with --gpus=all flag.",
            ),
        ]

    def build_request(self, action_name: str, params: dict) -> dict | None:
        """Build request with Ollama-specific payload formatting."""
        if action_name == "chat":
            # Transform flat params into Ollama chat format
            model = params.get("model", "llama3.1")
            content = params.get("content", "")
            base = self.get_base_url().rstrip("/")
            return {
                "url": f"{base}/api/chat",
                "method": "POST",
                "body": {
                    "model": model,
                    "messages": [{"role": "user", "content": content}],
                    "stream": False,
                },
                "headers": {"Content-Type": "application/json"},
            }
        # Default handling for other actions
        return super().build_request(action_name, params)
