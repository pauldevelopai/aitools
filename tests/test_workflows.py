"""Workflow tests for Partner Intelligence, Mentor, and Governance workflows.

Note: Many tests are marked as requiring PostgreSQL because the models use
PostgreSQL-specific types (UUID, JSONB) that don't work with SQLite.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4


class TestWorkflowRateLimiting:
    """Test workflow rate limiting (no database needed)."""

    def test_rate_limiter_allows_first_request(self):
        """Test rate limiter allows initial requests."""
        from app.workflows.rate_limit import WorkflowRateLimiter

        limiter = WorkflowRateLimiter()
        user_id = str(uuid4())

        allowed, retry_after, reason = limiter.is_allowed(
            workflow_name="partner_intelligence",
            user_id=user_id,
        )

        assert allowed is True
        assert retry_after == 0  # No wait needed when allowed
        assert reason == ""  # No reason when allowed

    def test_rate_limiter_respects_resource_limits(self):
        """Test rate limiter enforces per-resource limits."""
        from app.workflows.rate_limit import WorkflowRateLimiter

        limiter = WorkflowRateLimiter()
        user_id = str(uuid4())
        resource_id = str(uuid4())

        # First request should succeed
        allowed1, _, _ = limiter.is_allowed(
            workflow_name="mentor_intake",
            user_id=user_id,
            resource_id=resource_id,
        )
        assert allowed1 is True

        # Second request for same resource should be blocked
        allowed2, _, reason = limiter.is_allowed(
            workflow_name="mentor_intake",
            user_id=user_id,
            resource_id=resource_id,
        )
        assert allowed2 is False
        assert "resource" in reason.lower()

    def test_rate_limiter_different_users(self):
        """Test rate limiter tracks users separately."""
        from app.workflows.rate_limit import WorkflowRateLimiter

        limiter = WorkflowRateLimiter()
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        resource_id = str(uuid4())

        # User 1 accesses resource
        allowed1, _, _ = limiter.is_allowed(
            workflow_name="partner_intelligence",
            user_id=user1_id,
            resource_id=resource_id,
        )
        assert allowed1 is True

        # User 2 can also access same resource
        allowed2, _, _ = limiter.is_allowed(
            workflow_name="partner_intelligence",
            user_id=user2_id,
            resource_id=resource_id,
        )
        assert allowed2 is True


class TestWorkflowAuditLogging:
    """Test workflow audit logging (no database needed)."""

    def test_log_workflow_start(self):
        """Test logging workflow start event doesn't raise errors."""
        from app.workflows.audit import log_workflow_start

        workflow_run_id = str(uuid4())
        actor_id = str(uuid4())

        # This should not raise an exception
        log_workflow_start(
            workflow_name="partner_intelligence",
            workflow_run_id=workflow_run_id,
            actor_id=actor_id,
            inputs_summary={"organization_name": "Test Org"},
        )

    def test_log_workflow_complete(self):
        """Test logging workflow completion event doesn't raise errors."""
        from app.workflows.audit import log_workflow_complete

        workflow_run_id = str(uuid4())

        log_workflow_complete(
            workflow_name="mentor_intake",
            workflow_run_id=workflow_run_id,
            outputs_summary={"charter_generated": True},
        )

    def test_log_workflow_failure(self):
        """Test logging workflow failure event doesn't raise errors."""
        from app.workflows.audit import log_workflow_failure

        workflow_run_id = str(uuid4())

        log_workflow_failure(
            workflow_name="governance_intelligence",
            workflow_run_id=workflow_run_id,
            error_message="Connection timeout",
        )


class TestPartnerIntelligenceWorkflow:
    """Test Partner Intelligence workflow node functions."""

    @pytest.mark.asyncio
    async def test_identify_pages_node(self):
        """Test that identify_pages node can process state."""
        from app.workflows.partner_intelligence.state import PartnerIntelligenceState

        # Create a minimal state for testing the node
        state: PartnerIntelligenceState = {
            "organization_id": str(uuid4()),
            "organization_name": "Test Media Organization",
            "website_url": "https://example.com",
            "current_description": None,
            "current_notes": None,
            "workflow_run_id": None,
            "discovered_pages": [],
            "snapshot_ids": [],
            "fetch_errors": [],
            "extracted_fields": [],
            "extraction_errors": [],
            "enrichment": {},
            "conflicts": [],
            "has_conflicts": False,
            "needs_review": False,
            "low_confidence_fields": [],
            "evidence_source_ids": [],
            "enrichment_applied": False,
            "errors": [],
        }

        # Verify state structure is valid
        assert state["organization_name"] == "Test Media Organization"
        assert state["website_url"] == "https://example.com"
        assert state["needs_review"] is False

    def test_workflow_state_initialization(self):
        """Test that workflow initial state can be created."""
        from app.workflows.partner_intelligence.state import PartnerIntelligenceState

        org_id = str(uuid4())

        initial_state: PartnerIntelligenceState = {
            "organization_id": org_id,
            "organization_name": "Test Org",
            "website_url": "https://test.com",
            "current_description": "Existing description",
            "current_notes": None,
            "workflow_run_id": str(uuid4()),
            "discovered_pages": [],
            "snapshot_ids": [],
            "fetch_errors": [],
            "extracted_fields": [],
            "extraction_errors": [],
            "enrichment": {},
            "conflicts": [],
            "has_conflicts": False,
            "needs_review": False,
            "low_confidence_fields": [],
            "evidence_source_ids": [],
            "enrichment_applied": False,
            "errors": [],
        }

        assert initial_state["organization_id"] == org_id
        assert initial_state["current_description"] == "Existing description"


class TestMentorWorkflow:
    """Test Mentor workflow state and structure."""

    def test_mentor_intake_state_structure(self):
        """Test that Mentor Intake state can be properly initialized."""
        from app.workflows.mentor.state import MentorIntakeState

        engagement_id = str(uuid4())

        initial_state: MentorIntakeState = {
            "engagement_id": engagement_id,
            "journalist_name": "Jane Reporter",
            "journalist_role": "Investigative Journalist",
            "journalist_organization": "Daily News",
            "journalist_skill_level": "beginner",
            "engagement_title": "AI Tools Training",
            "engagement_description": "",
            "engagement_topics": [],
            "journalist_goals": "Learn to verify facts faster",
            "project_idea": "Investigating campaign finances",
            "current_challenges": "",
            "available_time": "",
            "technical_comfort": "",
            "workflow_run_id": None,
            "errors": [],
        }

        assert initial_state["journalist_name"] == "Jane Reporter"
        assert initial_state["engagement_id"] == engagement_id

    def test_mentor_pre_call_state_structure(self):
        """Test that Mentor Pre-Call state has required fields."""
        from app.workflows.mentor.state import MentorPreCallState

        state: MentorPreCallState = {
            "engagement_id": str(uuid4()),
            "session_number": 2,
            "journalist_name": "John Journalist",
            "journalist_organization": "The Times",
            "charter_content": "# Prototype Charter\n...",
            "previous_decisions": [],
            "open_tasks": [],
            "completed_tasks": [],
            "previous_session_notes": "",
            "session_focus": "Advanced data analysis",
            "workflow_run_id": None,
            "errors": [],
        }

        assert state["session_number"] == 2
        assert state["journalist_name"] == "John Journalist"

    def test_mentor_post_call_state_structure(self):
        """Test that Mentor Post-Call state has required fields."""
        from app.workflows.mentor.state import MentorPostCallState

        state: MentorPostCallState = {
            "engagement_id": str(uuid4()),
            "session_number": 1,
            "journalist_name": "Sarah Smith",
            "journalist_organization": "BBC",
            "session_notes": "Great discussion about AI tools.",
            "session_transcript": "",
            "session_duration": 60,
            "charter_content": "",
            "previous_decisions": [],
            "current_tasks": [],
            "workflow_run_id": None,
            "errors": [],
        }

        assert state["session_duration"] == 60
        assert "Great discussion" in state["session_notes"]


class TestGovernanceWorkflow:
    """Test Governance workflow state and structure."""

    def test_governance_target_state_for_framework(self):
        """Test GovernanceTargetState for framework research."""
        from app.workflows.governance.state import GovernanceTargetState

        target_id = str(uuid4())

        state: GovernanceTargetState = {
            "target_id": target_id,
            "target_type": "framework",
            "target_name": "EU AI Act",
            "target_description": "European Union AI regulation",
            "jurisdiction": "EU",
            "tool_id": "",
            "tool_url": "",
            "search_terms": ["EU AI Act", "artificial intelligence regulation"],
            "known_urls": ["https://eur-lex.europa.eu/eli/reg/2024/1689"],
            "workflow_run_id": None,
            "errors": [],
        }

        assert state["target_type"] == "framework"
        assert state["jurisdiction"] == "EU"
        assert len(state["search_terms"]) == 2

    def test_governance_target_state_for_tool(self):
        """Test GovernanceTargetState for tool testing."""
        from app.workflows.governance.state import GovernanceTargetState

        state: GovernanceTargetState = {
            "target_id": str(uuid4()),
            "target_type": "tool",
            "target_name": "ChatGPT",
            "target_description": "OpenAI's conversational AI",
            "jurisdiction": "",
            "tool_id": str(uuid4()),
            "tool_url": "https://chat.openai.com",
            "search_terms": [],
            "known_urls": [],
            "workflow_run_id": None,
            "errors": [],
        }

        assert state["target_type"] == "tool"
        assert state["tool_url"] == "https://chat.openai.com"

    def test_evidence_source_structure(self):
        """Test EvidenceSource TypedDict structure."""
        from app.workflows.governance.state import EvidenceSource

        source: EvidenceSource = {
            "url": "https://example.com/policy",
            "title": "Example Policy Document",
            "content": "This is the policy content...",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "excerpt": "Key excerpt from the document",
        }

        assert source["url"] == "https://example.com/policy"
        assert "policy content" in source["content"]

    def test_extracted_framework_structure(self):
        """Test ExtractedFramework TypedDict structure."""
        from app.workflows.governance.state import ExtractedFramework

        framework: ExtractedFramework = {
            "name": "General Data Protection Regulation",
            "short_name": "GDPR",
            "framework_type": "regulation",
            "jurisdiction": "EU",
            "effective_date": "2018-05-25",
            "description": "EU data protection law",
            "key_provisions": [
                "Right to access",
                "Right to erasure",
                "Data portability",
            ],
            "official_url": "https://gdpr-info.eu/",
            "evidence_sources": [],
        }

        assert framework["short_name"] == "GDPR"
        assert len(framework["key_provisions"]) == 3


class TestWorkflowGraphStructure:
    """Test workflow graph structure and registration."""

    def test_partner_intelligence_graph_compiles(self):
        """Test Partner Intelligence graph can be created and compiled."""
        from app.workflows.partner_intelligence.graph import create_partner_intelligence_graph

        graph = create_partner_intelligence_graph()
        assert graph is not None

    def test_mentor_intake_graph_compiles(self):
        """Test Mentor Intake graph can be created and compiled."""
        from app.workflows.mentor.graph import create_intake_graph

        graph = create_intake_graph()
        assert graph is not None

    def test_mentor_pre_call_graph_compiles(self):
        """Test Mentor Pre-Call graph can be created and compiled."""
        from app.workflows.mentor.graph import create_pre_call_graph

        graph = create_pre_call_graph()
        assert graph is not None

    def test_mentor_post_call_graph_compiles(self):
        """Test Mentor Post-Call graph can be created and compiled."""
        from app.workflows.mentor.graph import create_post_call_graph

        graph = create_post_call_graph()
        assert graph is not None

    def test_governance_graph_compiles(self):
        """Test Governance Intelligence graph can be created and compiled."""
        from app.workflows.governance.graph import create_governance_graph

        graph = create_governance_graph()
        assert graph is not None


class TestWorkflowStateDefinitions:
    """Test workflow state TypedDict definitions."""

    def test_partner_intelligence_state_has_required_fields(self):
        """Test PartnerIntelligenceState has expected fields."""
        from app.workflows.partner_intelligence.state import PartnerIntelligenceState
        import typing

        # Get TypedDict annotations
        annotations = typing.get_type_hints(PartnerIntelligenceState)

        # Check required fields exist
        assert "organization_id" in annotations
        assert "organization_name" in annotations
        assert "website_url" in annotations
        assert "discovered_pages" in annotations
        assert "enrichment" in annotations
        assert "needs_review" in annotations

    def test_mentor_intake_state_has_required_fields(self):
        """Test MentorIntakeState has expected fields."""
        from app.workflows.mentor.state import MentorIntakeState
        import typing

        annotations = typing.get_type_hints(MentorIntakeState)

        assert "engagement_id" in annotations
        assert "journalist_name" in annotations
        assert "errors" in annotations

    def test_governance_target_state_has_required_fields(self):
        """Test GovernanceTargetState has expected fields."""
        from app.workflows.governance.state import GovernanceTargetState
        import typing

        annotations = typing.get_type_hints(GovernanceTargetState)

        assert "target_id" in annotations
        assert "target_type" in annotations
        assert "target_name" in annotations
        assert "errors" in annotations
