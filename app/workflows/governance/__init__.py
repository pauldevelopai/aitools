"""Governance & Tools Intelligence Workflow package.

This package provides workflows for:
1. Researching governance frameworks (regulations, guidelines, standards)
2. Testing tools for compliance and quality
3. Generating Grounded-ready content with evidence
"""
from app.workflows.governance.graph import (
    create_governance_graph,
    register_governance_workflows,
    run_governance_workflow,
    run_framework_research,
    run_tool_testing,
    WORKFLOW_GOVERNANCE,
)
from app.workflows.governance.state import (
    GovernanceTargetState,
    EvidenceSource,
    ExtractedFramework,
    ExtractedControl,
    TestResult,
    GeneratedContent,
)

__all__ = [
    # Graph creators
    "create_governance_graph",
    "register_governance_workflows",
    # Convenience runners
    "run_governance_workflow",
    "run_framework_research",
    "run_tool_testing",
    # Workflow name
    "WORKFLOW_GOVERNANCE",
    # State types
    "GovernanceTargetState",
    "EvidenceSource",
    "ExtractedFramework",
    "ExtractedControl",
    "TestResult",
    "GeneratedContent",
]
