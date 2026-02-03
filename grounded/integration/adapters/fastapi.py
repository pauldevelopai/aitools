"""
GROUNDED FastAPI Adapter - FastAPI integration utilities.

Provides FastAPI dependencies, decorators, and utilities for
integrating GROUNDED infrastructure with FastAPI applications.
"""

import functools
import time
from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import Depends, HTTPException, Request

from grounded.core.config import GroundedSettings, get_settings
from grounded.core.exceptions import PolicyViolationError
from grounded.governance.audit.logger import AuditEvent, AuditEventType, AuditLogger, get_audit_logger
from grounded.governance.policies.base import PolicyEngine

F = TypeVar("F", bound=Callable[..., Any])


def get_grounded_settings() -> GroundedSettings:
    """
    FastAPI dependency for GROUNDED settings.

    Usage:
        @app.get("/")
        async def endpoint(settings: GroundedSettings = Depends(get_grounded_settings)):
            return {"env": settings.env}
    """
    return get_settings()


def get_audit_logger_dep() -> AuditLogger:
    """
    FastAPI dependency for audit logger.

    Usage:
        @app.get("/")
        async def endpoint(logger: AuditLogger = Depends(get_audit_logger_dep)):
            logger.log_action("my_action")
    """
    return get_audit_logger()


def audit_endpoint(
    action: str,
    resource: Optional[str] = None,
    include_request_details: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to automatically audit endpoint calls.

    Logs an audit event for each call to the decorated endpoint,
    including timing and outcome information.

    Usage:
        @app.post("/api/data")
        @audit_endpoint(action="create_data", resource="data")
        async def create_data(request: Request):
            return {"status": "created"}

    Args:
        action: The action name for audit logging
        resource: Optional resource identifier
        include_request_details: Whether to include request details in audit

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_audit_logger()
            start_time = time.time()

            # Extract request if available
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Build actor and details
            actor = "anonymous"
            details: Dict[str, Any] = {}

            if request and include_request_details:
                # Try to get user info from request state
                if hasattr(request.state, "user") and request.state.user:
                    actor = getattr(request.state.user, "email", str(request.state.user))

                details = {
                    "method": request.method,
                    "path": str(request.url.path),
                    "client_ip": request.client.host if request.client else None,
                }

            outcome = "success"
            error_details: Optional[str] = None

            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException as e:
                outcome = "error"
                error_details = f"HTTP {e.status_code}: {e.detail}"
                raise
            except Exception as e:
                outcome = "error"
                error_details = str(e)
                raise
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                details["duration_ms"] = round(duration_ms, 2)
                if error_details:
                    details["error"] = error_details

                # Log the audit event
                logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.ACTION_COMPLETED
                        if outcome == "success"
                        else AuditEventType.ACTION_FAILED,
                        action=action,
                        actor=actor,
                        resource=resource or action,
                        outcome=outcome,
                        details=details,
                    )
                )

        return wrapper  # type: ignore

    return decorator


def require_policy(
    policy_engine: PolicyEngine,
    action: str,
    context_builder: Optional[Callable[[Request], Dict[str, Any]]] = None,
) -> Callable[[F], F]:
    """
    Decorator to enforce policy on endpoint.

    Evaluates policies before allowing the endpoint to execute.
    Raises HTTP 403 if policy denies the action.

    Usage:
        engine = PolicyEngine()

        @app.post("/api/sensitive")
        @require_policy(engine, "sensitive_action")
        async def sensitive_endpoint(request: Request):
            return {"status": "ok"}

    Args:
        policy_engine: The PolicyEngine to use for evaluation
        action: The action name for policy evaluation
        context_builder: Optional function to build context from request

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Build context
            context: Dict[str, Any] = {}
            if context_builder and request:
                context = context_builder(request)

            # Add request info to context
            if request:
                context["request_path"] = str(request.url.path)
                context["request_method"] = request.method

            # Evaluate policy
            try:
                result = policy_engine.evaluate(action, context, raise_on_deny=True)
            except PolicyViolationError as e:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "policy_violation",
                        "policy": e.policy_name,
                        "action": e.action,
                        "reason": e.reason,
                    },
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


class GroundedMiddleware:
    """
    FastAPI middleware for GROUNDED integration.

    Adds GROUNDED context to requests and handles cross-cutting concerns.

    Usage:
        from grounded.integration.adapters.fastapi import GroundedMiddleware

        app = FastAPI()
        app.add_middleware(GroundedMiddleware)
    """

    def __init__(self, app: Any):
        """
        Initialize the middleware.

        Args:
            app: The FastAPI application
        """
        self.app = app
        self._settings = get_settings()
        self._logger = get_audit_logger()

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        """Process the request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Add GROUNDED context to scope
        scope["grounded"] = {
            "settings": self._settings,
            "env": self._settings.env,
        }

        await self.app(scope, receive, send)
