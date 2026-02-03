"""
GROUNDED Governance Policy Base - Policy framework.

Defines the interfaces and base classes for governance policies,
enabling pluggable policy enforcement throughout the GROUNDED infrastructure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from grounded.core.base import GroundedComponent
from grounded.core.config import get_settings
from grounded.core.exceptions import PolicyViolationError


class PolicyDecision(Enum):
    """Decision outcome from policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    AUDIT = "audit"


@dataclass
class PolicyResult:
    """Result of a policy evaluation."""

    decision: PolicyDecision
    policy_name: str
    action: str
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_allowed(self) -> bool:
        """Check if the action is allowed."""
        return self.decision in (PolicyDecision.ALLOW, PolicyDecision.WARN, PolicyDecision.AUDIT)

    @property
    def is_denied(self) -> bool:
        """Check if the action is denied."""
        return self.decision == PolicyDecision.DENY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "decision": self.decision.value,
            "policy_name": self.policy_name,
            "action": self.action,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@runtime_checkable
class PolicyProtocol(Protocol):
    """
    Protocol for governance policies.

    Any class implementing this protocol can be used as a policy
    in the GROUNDED governance framework.
    """

    @property
    def name(self) -> str:
        """Policy name identifier."""
        ...

    @property
    def priority(self) -> int:
        """Policy priority (higher = evaluated first)."""
        ...

    def applies_to(self, action: str) -> bool:
        """
        Check if this policy applies to the given action.

        Args:
            action: The action being evaluated

        Returns:
            True if this policy should evaluate the action
        """
        ...

    def evaluate(self, action: str, context: Dict[str, Any]) -> PolicyResult:
        """
        Evaluate the policy for the given action and context.

        Args:
            action: The action being performed
            context: Additional context about the action

        Returns:
            PolicyResult with the evaluation outcome
        """
        ...


class BasePolicy(GroundedComponent, ABC):
    """
    Base class for governance policies.

    Extends GroundedComponent to add policy-specific utilities.
    Concrete policies should inherit from this class.

    Example:
        class ContentModerationPolicy(BasePolicy):
            @property
            def name(self) -> str:
                return "content_moderation"

            @property
            def priority(self) -> int:
                return 100

            def applies_to(self, action: str) -> bool:
                return action in ["create_embedding", "complete"]

            def evaluate(self, action: str, context: Dict[str, Any]) -> PolicyResult:
                # Your evaluation logic
                return PolicyResult(
                    decision=PolicyDecision.ALLOW,
                    policy_name=self.name,
                    action=action
                )
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize the policy.

        Args:
            enabled: Whether this policy is enabled
        """
        self._enabled = enabled

    @property
    @abstractmethod
    def name(self) -> str:
        """Policy name identifier."""
        ...

    @property
    def priority(self) -> int:
        """
        Policy priority (higher = evaluated first).

        Default priority is 0. Override to change evaluation order.
        """
        return 0

    @property
    def enabled(self) -> bool:
        """Check if this policy is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable this policy."""
        self._enabled = True

    def disable(self) -> None:
        """Disable this policy."""
        self._enabled = False

    @abstractmethod
    def applies_to(self, action: str) -> bool:
        """
        Check if this policy applies to the given action.

        Args:
            action: The action being evaluated

        Returns:
            True if this policy should evaluate the action
        """
        ...

    @abstractmethod
    def evaluate(self, action: str, context: Dict[str, Any]) -> PolicyResult:
        """
        Evaluate the policy for the given action and context.

        Args:
            action: The action being performed
            context: Additional context about the action

        Returns:
            PolicyResult with the evaluation outcome
        """
        ...


class PolicyEngine(GroundedComponent):
    """
    Engine for evaluating governance policies.

    Manages policy registration and evaluation, respecting priority ordering
    and enforcement modes.

    Example:
        engine = PolicyEngine()
        engine.register_policy(MyPolicy())

        result = engine.evaluate("create_embedding", {"text": "..."})
        if result.is_denied:
            raise PolicyViolationError(...)
    """

    def __init__(self):
        """Initialize the policy engine."""
        self._policies: List[BasePolicy] = []
        self._settings = get_settings()

    @property
    def name(self) -> str:
        return "policy_engine"

    @property
    def enforcement_mode(self) -> str:
        """Get current enforcement mode."""
        return self._settings.policy_enforcement_mode

    def register_policy(self, policy: BasePolicy) -> None:
        """
        Register a policy with the engine.

        Policies are sorted by priority (highest first).

        Args:
            policy: The policy to register
        """
        self._policies.append(policy)
        # Sort by priority descending
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    def unregister_policy(self, name: str) -> Optional[BasePolicy]:
        """
        Unregister a policy by name.

        Args:
            name: The policy name to remove

        Returns:
            The removed policy, or None if not found
        """
        for i, policy in enumerate(self._policies):
            if policy.name == name:
                return self._policies.pop(i)
        return None

    def get_policy(self, name: str) -> Optional[BasePolicy]:
        """
        Get a policy by name.

        Args:
            name: The policy name to find

        Returns:
            The policy, or None if not found
        """
        for policy in self._policies:
            if policy.name == name:
                return policy
        return None

    def list_policies(self) -> List[str]:
        """Get list of registered policy names."""
        return [p.name for p in self._policies]

    def evaluate(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        raise_on_deny: bool = False,
    ) -> PolicyResult:
        """
        Evaluate all applicable policies for an action.

        Policies are evaluated in priority order. The first DENY result
        stops evaluation. WARN and AUDIT results are collected but don't
        stop evaluation.

        Args:
            action: The action being performed
            context: Additional context about the action
            raise_on_deny: If True, raise PolicyViolationError on DENY

        Returns:
            Combined PolicyResult from all evaluations

        Raises:
            PolicyViolationError: If raise_on_deny and action is denied
        """
        context = context or {}

        # Check enforcement mode
        if self._settings.policy_enforcement_mode == "disabled":
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                policy_name="policy_engine",
                action=action,
                reason="Policy enforcement disabled",
            )

        # Collect results
        results: List[PolicyResult] = []
        final_decision = PolicyDecision.ALLOW

        for policy in self._policies:
            if not policy.enabled:
                continue
            if not policy.applies_to(action):
                continue

            result = policy.evaluate(action, context)
            results.append(result)

            # DENY stops evaluation
            if result.decision == PolicyDecision.DENY:
                final_decision = PolicyDecision.DENY
                break

            # Track warnings
            if result.decision == PolicyDecision.WARN:
                if final_decision == PolicyDecision.ALLOW:
                    final_decision = PolicyDecision.WARN

        # Build combined result
        combined = PolicyResult(
            decision=final_decision,
            policy_name="policy_engine",
            action=action,
            reason=results[-1].reason if results else "No policies evaluated",
            details={
                "policies_evaluated": [r.policy_name for r in results],
                "results": [r.to_dict() for r in results],
            },
        )

        # Handle enforcement mode
        if self._settings.policy_enforcement_mode == "audit":
            # Audit mode: log but don't deny
            combined.decision = PolicyDecision.AUDIT

        # Raise if requested and denied
        if raise_on_deny and combined.is_denied:
            last_deny = next((r for r in results if r.is_denied), combined)
            raise PolicyViolationError(
                policy_name=last_deny.policy_name,
                action=action,
                reason=last_deny.reason,
            )

        return combined

    async def evaluate_async(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        raise_on_deny: bool = False,
    ) -> PolicyResult:
        """
        Async version of evaluate.

        Args:
            action: The action being performed
            context: Additional context about the action
            raise_on_deny: If True, raise PolicyViolationError on DENY

        Returns:
            Combined PolicyResult from all evaluations
        """
        # For now, delegate to sync version
        # Future: support async policy evaluation
        return self.evaluate(action, context, raise_on_deny)
