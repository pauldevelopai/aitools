"""
Directory Sync Service - Sync directory data to GROUNDED knowledge base.

Provides functionality to sync journalists, organizations, and engagements
to GROUNDED's knowledge system for semantic search and AI-powered queries.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.directory import (
    MediaOrganization,
    Department,
    Team,
    Journalist,
    Engagement,
    JournalistNote,
)
from app.grounded_adapter import is_grounded_initialized, log_audit_event_compat

logger = logging.getLogger(__name__)

# Constants
DIRECTORY_KNOWLEDGE_BASE_ID = "directory-crm"
DIRECTORY_KNOWLEDGE_BASE_NAME = "Media Directory CRM"


class DirectorySyncService:
    """Service for syncing directory data to GROUNDED knowledge base."""

    def __init__(self):
        self._service = None
        self._base_id = DIRECTORY_KNOWLEDGE_BASE_ID

    def _get_service(self):
        """Get or create the knowledge service instance."""
        if self._service is None:
            from grounded.knowledge.service import KnowledgeService
            self._service = KnowledgeService()
        return self._service

    def _ensure_knowledge_base(self) -> str:
        """Ensure the directory knowledge base exists."""
        service = self._get_service()

        try:
            # Try to get existing base
            service.get_knowledge_base(self._base_id)
            logger.debug(f"Using existing knowledge base: {self._base_id}")
        except Exception:
            # Create new base
            service.create_knowledge_base(
                name=DIRECTORY_KNOWLEDGE_BASE_NAME,
                owner_type="system",
                owner_id="directory",
                description="Knowledge base for Media Directory CRM - journalists, organizations, and AI training engagements",
                metadata={"type": "directory_crm"},
            )
            # Override the base_id since create_knowledge_base generates a UUID
            # For simplicity, we'll use the generated one
            bases = service.list_knowledge_bases(owner_type="system", owner_id="directory")
            if bases:
                self._base_id = bases[0].base_id
            logger.info(f"Created knowledge base: {self._base_id}")

        return self._base_id

    def _get_or_create_source(self, source_name: str, source_type: str = "database") -> str:
        """Get or create a knowledge source."""
        from grounded.knowledge.models import KnowledgeSourceType

        service = self._get_service()
        base_id = self._ensure_knowledge_base()

        # Check existing sources
        sources = service.list_sources(base_id)
        for source in sources:
            if source.name == source_name:
                return source.source_id

        # Create new source
        source = service.create_source(
            base_id=base_id,
            name=source_name,
            description=f"Directory data: {source_name}",
            source_type=KnowledgeSourceType.DATABASE,
            metadata={"sync_type": source_type},
        )
        logger.info(f"Created knowledge source: {source_name}")
        return source.source_id

    def sync_organizations(self, db: Session) -> Dict[str, Any]:
        """Sync all organizations to GROUNDED knowledge base."""
        if not is_grounded_initialized():
            return {"error": "GROUNDED not initialized", "synced": 0}

        service = self._get_service()
        base_id = self._ensure_knowledge_base()
        source_id = self._get_or_create_source("Organizations")

        organizations = db.query(MediaOrganization).all()
        synced = 0

        for org in organizations:
            # Build rich content for semantic search
            content = f"""Organization: {org.name}
Type: {org.org_type}
Country: {org.country or 'Not specified'}
Website: {org.website or 'Not specified'}
Description: {org.description or 'No description'}
Status: {'Active' if org.is_active else 'Inactive'}
Notes: {org.notes or 'No notes'}"""

            try:
                service.add_knowledge(
                    base_id=base_id,
                    source_id=source_id,
                    content=content,
                    title=f"Organization: {org.name}",
                    metadata={
                        "entity_type": "organization",
                        "entity_id": str(org.id),
                        "org_type": org.org_type,
                        "country": org.country,
                        "is_active": org.is_active,
                    },
                    generate_embedding=True,
                )
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync organization {org.name}: {e}")

        log_audit_event_compat(
            action="directory_sync_organizations",
            resource="knowledge_base",
            details={"synced": synced, "total": len(organizations)},
        )

        return {"synced": synced, "total": len(organizations)}

    def sync_journalists(self, db: Session) -> Dict[str, Any]:
        """Sync all journalists to GROUNDED knowledge base."""
        if not is_grounded_initialized():
            return {"error": "GROUNDED not initialized", "synced": 0}

        service = self._get_service()
        base_id = self._ensure_knowledge_base()
        source_id = self._get_or_create_source("Journalists")

        journalists = (
            db.query(Journalist)
            .options(
                joinedload(Journalist.organization),
                joinedload(Journalist.department),
                joinedload(Journalist.team),
            )
            .all()
        )
        synced = 0

        for j in journalists:
            org_name = j.organization.name if j.organization else "Freelance"
            dept_name = j.department.name if j.department else "N/A"
            team_name = j.team.name if j.team else "N/A"

            interests = ", ".join(j.areas_of_interest) if j.areas_of_interest else "None specified"

            content = f"""Journalist: {j.full_name}
Email: {j.email or 'Not provided'}
Phone: {j.phone or 'Not provided'}
Organization: {org_name}
Department: {dept_name}
Team: {team_name}
Role: {j.role or 'Not specified'}
Beat/Coverage: {j.beat or 'Not specified'}
AI Skill Level: {j.ai_skill_level}
AI Interests: {interests}
Bio: {j.bio or 'No bio'}
Twitter: @{j.twitter if j.twitter else 'N/A'}
LinkedIn: {j.linkedin or 'N/A'}
Website: {j.website or 'N/A'}
Status: {'Active' if j.is_active else 'Inactive'}"""

            try:
                service.add_knowledge(
                    base_id=base_id,
                    source_id=source_id,
                    content=content,
                    title=f"Journalist: {j.full_name}",
                    metadata={
                        "entity_type": "journalist",
                        "entity_id": str(j.id),
                        "organization": org_name,
                        "organization_id": str(j.organization_id) if j.organization_id else None,
                        "ai_skill_level": j.ai_skill_level,
                        "beat": j.beat,
                        "is_active": j.is_active,
                    },
                    generate_embedding=True,
                )
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync journalist {j.full_name}: {e}")

        log_audit_event_compat(
            action="directory_sync_journalists",
            resource="knowledge_base",
            details={"synced": synced, "total": len(journalists)},
        )

        return {"synced": synced, "total": len(journalists)}

    def sync_engagements(self, db: Session) -> Dict[str, Any]:
        """Sync all engagements to GROUNDED knowledge base."""
        if not is_grounded_initialized():
            return {"error": "GROUNDED not initialized", "synced": 0}

        service = self._get_service()
        base_id = self._ensure_knowledge_base()
        source_id = self._get_or_create_source("Engagements")

        engagements = (
            db.query(Engagement)
            .options(joinedload(Engagement.journalist).joinedload(Journalist.organization))
            .all()
        )
        synced = 0

        for e in engagements:
            journalist_name = e.journalist.full_name
            org_name = e.journalist.organization.name if e.journalist.organization else "Freelance"

            topics = ", ".join(e.topics_covered) if e.topics_covered else "None recorded"
            materials = ", ".join(e.materials_used) if e.materials_used else "None recorded"

            content = f"""Training Engagement: {e.title}
Date: {e.date.strftime('%Y-%m-%d')}
Type: {e.engagement_type}
Journalist: {journalist_name}
Organization: {org_name}
Duration: {e.duration_minutes or 'Not recorded'} minutes
Location: {e.location or 'Not specified'}
Topics Covered: {topics}
Materials Used: {materials}
Skill Before: {e.skill_before or 'Not recorded'}
Skill After: {e.skill_after or 'Not recorded'}
Outcomes: {e.outcomes or 'No outcomes recorded'}
Follow-up Actions: {e.follow_up_actions or 'None'}
Follow-up Date: {e.follow_up_date.strftime('%Y-%m-%d') if e.follow_up_date else 'Not scheduled'}
Description: {e.description or 'No description'}
Notes: {e.notes or 'No notes'}"""

            try:
                service.add_knowledge(
                    base_id=base_id,
                    source_id=source_id,
                    content=content,
                    title=f"Engagement: {e.title} - {journalist_name}",
                    metadata={
                        "entity_type": "engagement",
                        "entity_id": str(e.id),
                        "journalist_id": str(e.journalist_id),
                        "journalist_name": journalist_name,
                        "organization": org_name,
                        "engagement_type": e.engagement_type,
                        "date": e.date.isoformat(),
                        "skill_before": e.skill_before,
                        "skill_after": e.skill_after,
                    },
                    generate_embedding=True,
                )
                synced += 1
            except Exception as e_err:
                logger.error(f"Failed to sync engagement {e.title}: {e_err}")

        log_audit_event_compat(
            action="directory_sync_engagements",
            resource="knowledge_base",
            details={"synced": synced, "total": len(engagements)},
        )

        return {"synced": synced, "total": len(engagements)}

    def sync_all(self, db: Session) -> Dict[str, Any]:
        """Sync all directory data to GROUNDED."""
        results = {
            "organizations": self.sync_organizations(db),
            "journalists": self.sync_journalists(db),
            "engagements": self.sync_engagements(db),
            "synced_at": datetime.utcnow().isoformat(),
        }

        total_synced = sum(
            r.get("synced", 0) for r in [
                results["organizations"],
                results["journalists"],
                results["engagements"],
            ]
        )
        results["total_synced"] = total_synced

        log_audit_event_compat(
            action="directory_sync_all",
            resource="knowledge_base",
            details=results,
        )

        return results

    def search(self, query: str, limit: int = 10, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search the directory knowledge base."""
        if not is_grounded_initialized():
            return []

        service = self._get_service()

        filters = {}
        if entity_type:
            filters["entity_type"] = entity_type

        try:
            results = service.search(
                base_id=self._base_id,
                query=query,
                limit=limit,
                filters=filters if filters else None,
                search_type="hybrid",
            )

            return [
                {
                    "content": item.content,
                    "title": item.title,
                    "score": score,
                    "metadata": item.metadata,
                }
                for item, score in zip(results.items, results.scores)
            ]
        except Exception as e:
            logger.error(f"Directory search failed: {e}")
            return []

    def get_answer(self, question: str) -> Dict[str, Any]:
        """Get an AI-generated answer about the directory."""
        if not is_grounded_initialized():
            return {"error": "GROUNDED not initialized"}

        service = self._get_service()

        try:
            answer = service.get_answer(
                base_id=self._base_id,
                query=question,
                limit=10,
            )

            return {
                "answer": answer.answer,
                "citations": [
                    {
                        "content": c.content,
                        "title": c.source_title,
                        "relevance": c.relevance_score,
                    }
                    for c in answer.citations
                ],
                "confidence": answer.confidence,
            }
        except Exception as e:
            logger.error(f"Directory answer generation failed: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        if not is_grounded_initialized():
            return {"error": "GROUNDED not initialized"}

        service = self._get_service()

        try:
            return service.get_stats(self._base_id)
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
_sync_service: Optional[DirectorySyncService] = None


def get_directory_sync_service() -> DirectorySyncService:
    """Get the directory sync service singleton."""
    global _sync_service
    if _sync_service is None:
        _sync_service = DirectorySyncService()
    return _sync_service
