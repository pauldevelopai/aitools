"""
GROUNDED Core Exceptions - Custom exception hierarchy.

Provides GROUNDED-specific exceptions for clear error handling
across the infrastructure layer.
"""

from typing import Any, Dict, Optional


class GroundedException(Exception):
    """
    Base exception for all GROUNDED errors.

    All GROUNDED-specific exceptions should inherit from this class
    to allow for consistent error handling.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code or "GROUNDED_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class ProviderNotFoundError(GroundedException):
    """
    Raised when a requested provider is not found in the registry.

    Example:
        raise ProviderNotFoundError(
            provider_type="embedding",
            provider_key="unknown_provider"
        )
    """

    def __init__(
        self,
        provider_type: str,
        provider_key: str,
        available_providers: Optional[list[str]] = None,
    ):
        self.provider_type = provider_type
        self.provider_key = provider_key
        self.available_providers = available_providers or []

        message = f"{provider_type.title()} provider '{provider_key}' not found"
        if self.available_providers:
            message += f". Available: {', '.join(self.available_providers)}"

        super().__init__(
            message=message,
            code="PROVIDER_NOT_FOUND",
            details={
                "provider_type": provider_type,
                "provider_key": provider_key,
                "available_providers": self.available_providers,
            },
        )


class PolicyViolationError(GroundedException):
    """
    Raised when an action violates a governance policy.

    Example:
        raise PolicyViolationError(
            policy_name="content_moderation",
            action="create_embedding",
            reason="Content contains prohibited material"
        )
    """

    def __init__(
        self,
        policy_name: str,
        action: str,
        reason: str,
        remediation: Optional[str] = None,
    ):
        self.policy_name = policy_name
        self.action = action
        self.reason = reason
        self.remediation = remediation

        message = f"Policy '{policy_name}' violated for action '{action}': {reason}"

        super().__init__(
            message=message,
            code="POLICY_VIOLATION",
            details={
                "policy_name": policy_name,
                "action": action,
                "reason": reason,
                "remediation": remediation,
            },
        )


class ConfigurationError(GroundedException):
    """
    Raised when there is a configuration error.

    Example:
        raise ConfigurationError(
            setting="GROUNDED_OPENAI_API_KEY",
            reason="API key is required when using OpenAI provider"
        )
    """

    def __init__(
        self,
        setting: str,
        reason: str,
        suggestion: Optional[str] = None,
    ):
        self.setting = setting
        self.reason = reason
        self.suggestion = suggestion

        message = f"Configuration error for '{setting}': {reason}"
        if suggestion:
            message += f". Suggestion: {suggestion}"

        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details={
                "setting": setting,
                "reason": reason,
                "suggestion": suggestion,
            },
        )


class ComponentInitializationError(GroundedException):
    """
    Raised when a component fails to initialize.

    Example:
        raise ComponentInitializationError(
            component_name="openai_embedding_provider",
            reason="Failed to connect to OpenAI API"
        )
    """

    def __init__(
        self,
        component_name: str,
        reason: str,
        original_error: Optional[Exception] = None,
    ):
        self.component_name = component_name
        self.reason = reason
        self.original_error = original_error

        message = f"Failed to initialize component '{component_name}': {reason}"

        super().__init__(
            message=message,
            code="COMPONENT_INITIALIZATION_ERROR",
            details={
                "component_name": component_name,
                "reason": reason,
                "original_error": str(original_error) if original_error else None,
            },
        )


class IntegrationError(GroundedException):
    """
    Raised when an integration with an external service fails.

    Example:
        raise IntegrationError(
            service="partner_api",
            operation="fetch_data",
            reason="Connection timeout"
        )
    """

    def __init__(
        self,
        service: str,
        operation: str,
        reason: str,
        retry_possible: bool = True,
    ):
        self.service = service
        self.operation = operation
        self.reason = reason
        self.retry_possible = retry_possible

        message = f"Integration error with '{service}' during '{operation}': {reason}"

        super().__init__(
            message=message,
            code="INTEGRATION_ERROR",
            details={
                "service": service,
                "operation": operation,
                "reason": reason,
                "retry_possible": retry_possible,
            },
        )
