"""
GROUNDED AI Governance Integration - Decorators and context managers.

Provides easy-to-use integration utilities for adding governance tracking
to AI operations without major code changes.

Usage:
    # Decorator approach
    @track_ai_operation(AIOperationType.EMBEDDING, source_component="MyService")
    def create_embedding(text: str) -> List[float]:
        return provider.create_embedding(text)

    # Context manager approach
    with ai_operation_context(AIOperationType.COMPLETION) as ctx:
        result = provider.complete(prompt)
        ctx.record_output(tokens=100)
"""

import functools
import inspect
import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional, TypeVar

from grounded.governance.ai.models import (
    AIAuditRecord,
    AIDataType,
    AIOperationType,
)
from grounded.governance.ai.tracker import get_governance_tracker

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def track_ai_operation(
    operation_type: AIOperationType,
    source_component: Optional[str] = None,
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    input_data_type: AIDataType = AIDataType.TEXT,
    extract_input_size: Optional[Callable[[Any], int]] = None,
    extract_output_size: Optional[Callable[[Any], int]] = None,
) -> Callable[[F], F]:
    """
    Decorator to automatically track AI operations.

    Wraps a function to automatically record its execution in the
    AI governance audit trail.

    Args:
        operation_type: Type of AI operation being performed
        source_component: Name of the component (auto-detected if not provided)
        provider_name: AI provider name (can also be extracted from self)
        model_name: Model name (can also be extracted from self)
        input_data_type: Type of input data
        extract_input_size: Function to extract input size from args
        extract_output_size: Function to extract output size from result

    Returns:
        Decorated function

    Example:
        @track_ai_operation(
            AIOperationType.EMBEDDING,
            source_component="DocumentProcessor",
            extract_input_size=lambda text: len(text)
        )
        def create_embedding(self, text: str) -> List[float]:
            return self._provider.create_embedding(text)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracker = get_governance_tracker()

            # Extract source information
            module = func.__module__
            function_name = func.__name__

            # Try to get component name from self if not provided
            component = source_component
            prov_name = provider_name
            mod_name = model_name

            if args and hasattr(args[0], "__class__"):
                self = args[0]
                if not component:
                    component = self.__class__.__name__
                if not prov_name and hasattr(self, "name"):
                    prov_name = getattr(self, "name", "")
                if not mod_name and hasattr(self, "model_name"):
                    mod_name = getattr(self, "model_name", "")

            # Calculate input size
            input_size = 0
            if extract_input_size:
                try:
                    # Try with first positional arg after self
                    if len(args) > 1:
                        input_size = extract_input_size(args[1])
                    elif "text" in kwargs:
                        input_size = extract_input_size(kwargs["text"])
                    elif "texts" in kwargs:
                        input_size = extract_input_size(kwargs["texts"])
                except Exception:
                    pass

            # Start tracking
            record = tracker.start_operation(
                operation_type=operation_type,
                source_module=module,
                source_function=function_name,
                source_component=component or "",
                provider_name=prov_name or "",
                model_name=mod_name or "",
                input_data_type=input_data_type,
                input_size=input_size,
            )

            try:
                result = func(*args, **kwargs)

                # Calculate output size
                output_size = 0
                if extract_output_size:
                    try:
                        output_size = extract_output_size(result)
                    except Exception:
                        pass

                # Complete tracking
                tracker.complete_operation(
                    record.record_id,
                    output_size=output_size,
                )

                return result

            except Exception as e:
                tracker.fail_operation(
                    record.record_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
                raise

        return wrapper  # type: ignore

    return decorator


def track_ai_operation_async(
    operation_type: AIOperationType,
    source_component: Optional[str] = None,
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    input_data_type: AIDataType = AIDataType.TEXT,
    extract_input_size: Optional[Callable[[Any], int]] = None,
    extract_output_size: Optional[Callable[[Any], int]] = None,
) -> Callable[[F], F]:
    """
    Async version of track_ai_operation decorator.

    Same as track_ai_operation but for async functions.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracker = get_governance_tracker()

            # Extract source information (same as sync version)
            module = func.__module__
            function_name = func.__name__

            component = source_component
            prov_name = provider_name
            mod_name = model_name

            if args and hasattr(args[0], "__class__"):
                self = args[0]
                if not component:
                    component = self.__class__.__name__
                if not prov_name and hasattr(self, "name"):
                    prov_name = getattr(self, "name", "")
                if not mod_name and hasattr(self, "model_name"):
                    mod_name = getattr(self, "model_name", "")

            input_size = 0
            if extract_input_size:
                try:
                    if len(args) > 1:
                        input_size = extract_input_size(args[1])
                    elif "text" in kwargs:
                        input_size = extract_input_size(kwargs["text"])
                except Exception:
                    pass

            record = tracker.start_operation(
                operation_type=operation_type,
                source_module=module,
                source_function=function_name,
                source_component=component or "",
                provider_name=prov_name or "",
                model_name=mod_name or "",
                input_data_type=input_data_type,
                input_size=input_size,
            )

            try:
                result = await func(*args, **kwargs)

                output_size = 0
                if extract_output_size:
                    try:
                        output_size = extract_output_size(result)
                    except Exception:
                        pass

                tracker.complete_operation(
                    record.record_id,
                    output_size=output_size,
                )

                return result

            except Exception as e:
                tracker.fail_operation(
                    record.record_id,
                    error_message=str(e),
                    error_type=type(e).__name__,
                )
                raise

        return wrapper  # type: ignore

    return decorator


class AIOperationContextManager:
    """
    Context manager for tracking AI operations.

    Provides more control than the decorator, allowing you to
    record additional information during operation execution.

    Example:
        with AIOperationContextManager(
            AIOperationType.COMPLETION,
            source_component="Chatbot"
        ) as ctx:
            result = provider.complete(prompt)
            ctx.record_output(tokens=len(result.split()))
            ctx.add_metadata(model_version="2.0")
    """

    def __init__(
        self,
        operation_type: AIOperationType,
        source_module: str = "",
        source_function: str = "",
        source_component: str = "",
        provider_name: str = "",
        model_name: str = "",
        input_data_type: AIDataType = AIDataType.TEXT,
        input_size: int = 0,
        input_count: int = 1,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        parent_operation_id: Optional[str] = None,
        tokens_input: int = 0,
        **metadata: Any,
    ):
        """Initialize the context manager with operation details."""
        self._operation_type = operation_type
        self._source_module = source_module
        self._source_function = source_function
        self._source_component = source_component
        self._provider_name = provider_name
        self._model_name = model_name
        self._input_data_type = input_data_type
        self._input_size = input_size
        self._input_count = input_count
        self._actor_type = actor_type
        self._actor_id = actor_id
        self._correlation_id = correlation_id
        self._parent_operation_id = parent_operation_id
        self._tokens_input = tokens_input
        self._metadata = metadata

        self._record: Optional[AIAuditRecord] = None
        self._output_size = 0
        self._output_count = 0
        self._tokens_output = 0
        self._result_metadata: dict = {}

        # Auto-detect caller if not provided
        if not self._source_module or not self._source_function:
            self._detect_caller()

    def _detect_caller(self) -> None:
        """Detect the calling module and function."""
        try:
            frame = inspect.currentframe()
            # Go up the stack to find the actual caller (skip __init__ and __enter__)
            for _ in range(4):
                if frame is not None:
                    frame = frame.f_back

            if frame:
                if not self._source_module:
                    self._source_module = frame.f_globals.get("__name__", "")
                if not self._source_function:
                    self._source_function = frame.f_code.co_name
        except Exception:
            pass

    def __enter__(self) -> "AIOperationContextManager":
        """Start tracking the operation."""
        tracker = get_governance_tracker()

        self._record = tracker.start_operation(
            operation_type=self._operation_type,
            source_module=self._source_module,
            source_function=self._source_function,
            source_component=self._source_component,
            provider_name=self._provider_name,
            model_name=self._model_name,
            input_data_type=self._input_data_type,
            input_size=self._input_size,
            input_count=self._input_count,
            actor_type=self._actor_type,
            actor_id=self._actor_id,
            correlation_id=self._correlation_id,
            parent_operation_id=self._parent_operation_id,
            tokens_input=self._tokens_input,
            **self._metadata,
        )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Complete or fail the operation tracking."""
        if not self._record:
            return

        tracker = get_governance_tracker()

        if exc_type is not None:
            # Operation failed
            tracker.fail_operation(
                self._record.record_id,
                error_message=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None,
            )
        else:
            # Operation completed
            tracker.complete_operation(
                self._record.record_id,
                output_size=self._output_size,
                output_count=self._output_count,
                tokens_output=self._tokens_output,
                **self._result_metadata,
            )

    @property
    def record_id(self) -> Optional[str]:
        """Get the current operation's record ID."""
        return self._record.record_id if self._record else None

    @property
    def record(self) -> Optional[AIAuditRecord]:
        """Get the current audit record."""
        return self._record

    def record_input(
        self,
        size: Optional[int] = None,
        count: Optional[int] = None,
        tokens: Optional[int] = None,
    ) -> None:
        """
        Record input information during operation.

        Args:
            size: Input data size
            count: Number of input items
            tokens: Input token count
        """
        if size is not None:
            self._input_size = size
            if self._record:
                self._record.context.input_size = size
        if count is not None:
            self._input_count = count
            if self._record:
                self._record.context.input_count = count
        if tokens is not None:
            self._tokens_input = tokens
            if self._record:
                self._record.tokens_input = tokens

    def record_output(
        self,
        size: Optional[int] = None,
        count: Optional[int] = None,
        tokens: Optional[int] = None,
    ) -> None:
        """
        Record output information to be used when operation completes.

        Args:
            size: Output data size
            count: Number of output items
            tokens: Output token count
        """
        if size is not None:
            self._output_size = size
        if count is not None:
            self._output_count = count
        if tokens is not None:
            self._tokens_output = tokens

    def add_metadata(self, **metadata: Any) -> None:
        """
        Add metadata to the result.

        Args:
            **metadata: Key-value pairs to add
        """
        self._result_metadata.update(metadata)

    def set_provider(self, provider_name: str, model_name: str = "") -> None:
        """
        Set the provider information.

        Args:
            provider_name: AI provider name
            model_name: Model name
        """
        self._provider_name = provider_name
        self._model_name = model_name
        if self._record:
            self._record.context.provider_name = provider_name
            self._record.context.model_name = model_name


@contextmanager
def ai_operation_context(
    operation_type: AIOperationType,
    source_component: str = "",
    provider_name: str = "",
    model_name: str = "",
    input_data_type: AIDataType = AIDataType.TEXT,
    **kwargs: Any,
):
    """
    Convenience function for creating an AI operation context.

    Example:
        with ai_operation_context(
            AIOperationType.EMBEDDING,
            source_component="MyService",
            provider_name="openai"
        ) as ctx:
            result = create_embedding(text)
            ctx.record_output(size=len(result))
    """
    ctx = AIOperationContextManager(
        operation_type=operation_type,
        source_component=source_component,
        provider_name=provider_name,
        model_name=model_name,
        input_data_type=input_data_type,
        **kwargs,
    )
    with ctx:
        yield ctx
