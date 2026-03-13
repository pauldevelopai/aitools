"""Generic tool adapter — configurable via OpenSourceApp database fields."""
from app.tool_adapters.base import BaseToolAdapter, ToolAction, HealthCheck


class GenericAPIAdapter(BaseToolAdapter):
    """Generic adapter for tools with standard REST APIs.

    Configured from OpenSourceApp.health_check_url and OpenSourceApp.api_base_path.
    """

    def __init__(self, slug: str, name: str, base_url: str,
                 health_url: str = "", api_base: str = ""):
        self._slug = slug
        self._name = name
        self._base_url = base_url
        self._health_url = health_url or f"{base_url}/health"
        self._api_base = api_base or ""

    def get_slug(self) -> str:
        return self._slug

    def get_display_name(self) -> str:
        return self._name

    def get_base_url(self) -> str:
        return self._base_url

    def get_health_check(self) -> HealthCheck:
        return HealthCheck(url=self._health_url)

    def get_actions(self) -> list[ToolAction]:
        # Generic adapters have no pre-defined actions
        # They can be extended per-tool via the database
        return []
