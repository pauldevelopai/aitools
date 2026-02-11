"""Rate limiting utilities for workflow execution.

Provides workflow-specific rate limiting to prevent spam-triggering
of expensive LLM-based workflows.
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowRateLimitBucket:
    """Token bucket for workflow rate limiting."""
    requests: list = field(default_factory=list)


class WorkflowRateLimiter:
    """Rate limiter for workflow execution.

    Implements a sliding window rate limiter that tracks workflow
    executions per user and per resource to prevent abuse.
    """

    def __init__(self):
        # Store: {workflow_name: {user_id: WorkflowRateLimitBucket}}
        self.user_buckets: Dict[str, Dict[str, WorkflowRateLimitBucket]] = defaultdict(
            lambda: defaultdict(WorkflowRateLimitBucket)
        )
        # Store: {workflow_name: {resource_id: WorkflowRateLimitBucket}}
        self.resource_buckets: Dict[str, Dict[str, WorkflowRateLimitBucket]] = defaultdict(
            lambda: defaultdict(WorkflowRateLimitBucket)
        )

        # Default limits (can be overridden per workflow)
        self.default_limits = {
            # Per user: max 5 workflow runs per 10 minutes
            "user_max_requests": 5,
            "user_window_seconds": 600,
            # Per resource: max 2 workflow runs per 30 minutes
            "resource_max_requests": 2,
            "resource_window_seconds": 1800,
        }

        # Workflow-specific limits
        self.workflow_limits = {
            "partner_intelligence": {
                "user_max_requests": 10,
                "user_window_seconds": 600,
                "resource_max_requests": 2,
                "resource_window_seconds": 1800,  # 30 min cooldown per org
            },
            "mentor_intake": {
                "user_max_requests": 10,
                "user_window_seconds": 600,
                "resource_max_requests": 1,
                "resource_window_seconds": 3600,  # 1 hour cooldown per engagement
            },
            "mentor_pre_call": {
                "user_max_requests": 20,
                "user_window_seconds": 600,
                "resource_max_requests": 3,
                "resource_window_seconds": 1800,
            },
            "mentor_post_call": {
                "user_max_requests": 20,
                "user_window_seconds": 600,
                "resource_max_requests": 3,
                "resource_window_seconds": 1800,
            },
            "governance_intelligence": {
                "user_max_requests": 10,
                "user_window_seconds": 600,
                "resource_max_requests": 2,
                "resource_window_seconds": 1800,
            },
            "agent_mission": {
                "user_max_requests": 5,
                "user_window_seconds": 3600,  # 5 per hour
                "resource_max_requests": 5,
                "resource_window_seconds": 3600,
            },
        }

    def get_limits(self, workflow_name: str) -> dict:
        """Get rate limits for a specific workflow."""
        return self.workflow_limits.get(workflow_name, self.default_limits)

    def _check_bucket(
        self,
        bucket: WorkflowRateLimitBucket,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """Check if a request is allowed under the rate limit.

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()

        # Remove expired timestamps (sliding window)
        bucket.requests = [
            ts for ts in bucket.requests
            if now - ts < window_seconds
        ]

        if len(bucket.requests) < max_requests:
            bucket.requests.append(now)
            return True, 0

        # Calculate retry-after
        oldest_request = min(bucket.requests)
        retry_after = int(window_seconds - (now - oldest_request)) + 1
        return False, retry_after

    def is_allowed(
        self,
        workflow_name: str,
        user_id: str,
        resource_id: Optional[str] = None,
    ) -> Tuple[bool, int, str]:
        """Check if a workflow execution is allowed.

        Args:
            workflow_name: Name of the workflow
            user_id: ID of the user triggering the workflow
            resource_id: Optional ID of the resource (org, engagement, target)

        Returns:
            Tuple of (is_allowed, retry_after_seconds, reason)
        """
        limits = self.get_limits(workflow_name)

        # Check user rate limit
        user_bucket = self.user_buckets[workflow_name][user_id]
        user_allowed, user_retry = self._check_bucket(
            user_bucket,
            limits["user_max_requests"],
            limits["user_window_seconds"],
        )

        if not user_allowed:
            logger.warning(
                f"Rate limit exceeded for user {user_id} on workflow {workflow_name}"
            )
            return False, user_retry, "user_rate_limit"

        # Check resource rate limit if resource_id provided
        if resource_id:
            resource_bucket = self.resource_buckets[workflow_name][resource_id]
            resource_allowed, resource_retry = self._check_bucket(
                resource_bucket,
                limits["resource_max_requests"],
                limits["resource_window_seconds"],
            )

            if not resource_allowed:
                logger.warning(
                    f"Rate limit exceeded for resource {resource_id} on workflow {workflow_name}"
                )
                return False, resource_retry, "resource_rate_limit"

        return True, 0, ""

    def reset_user(self, workflow_name: str, user_id: str) -> None:
        """Reset rate limit for a specific user (admin use only)."""
        if workflow_name in self.user_buckets:
            if user_id in self.user_buckets[workflow_name]:
                self.user_buckets[workflow_name][user_id].requests = []

    def reset_resource(self, workflow_name: str, resource_id: str) -> None:
        """Reset rate limit for a specific resource (admin use only)."""
        if workflow_name in self.resource_buckets:
            if resource_id in self.resource_buckets[workflow_name]:
                self.resource_buckets[workflow_name][resource_id].requests = []


# Global singleton instance
_workflow_rate_limiter: Optional[WorkflowRateLimiter] = None


def get_workflow_rate_limiter() -> WorkflowRateLimiter:
    """Get the global workflow rate limiter instance."""
    global _workflow_rate_limiter
    if _workflow_rate_limiter is None:
        _workflow_rate_limiter = WorkflowRateLimiter()
    return _workflow_rate_limiter


def check_workflow_rate_limit(
    workflow_name: str,
    user_id: str,
    resource_id: Optional[str] = None,
) -> Tuple[bool, int, str]:
    """Convenience function to check workflow rate limit.

    Returns:
        Tuple of (is_allowed, retry_after_seconds, reason)
    """
    limiter = get_workflow_rate_limiter()
    return limiter.is_allowed(workflow_name, user_id, resource_id)
