"""Personalized recommendations API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User
from app.dependencies import get_current_user, require_user
from app.services.recommendation import (
    get_recommendations,
    get_tool_guidance,
    get_suggested_for_location,
    build_user_context,
)
from app.services.kit_loader import get_tool
from app.schemas.recommendation import (
    RecommendationsResponse,
    ToolGuidanceResponse,
    SuggestedBlockResponse,
)


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/for-me", response_model=RecommendationsResponse)
async def get_recommendations_for_me(
    query: Optional[str] = Query(None, description="Search query to filter tools"),
    use_case: Optional[str] = Query(None, description="Use case to filter by"),
    limit: int = Query(5, ge=1, le=20, description="Maximum recommendations"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Get personalized tool recommendations based on user profile and activity.

    Returns tools scored and ranked for this specific user, with explanations
    and citations for why each tool is recommended.
    """
    recommendations = get_recommendations(
        db=db,
        user=user,
        query=query,
        use_case=use_case,
        limit=limit,
    )

    # Build summary of user context for transparency
    context = build_user_context(db, user)
    context_summary = {
        "budget": context.budget,
        "experience_level": context.ai_experience_level,
        "data_sensitivity": context.data_sensitivity,
        "use_cases": context.use_cases[:3] if context.use_cases else [],
        "constraints": {
            "max_cost": context.max_cost,
            "max_difficulty": context.max_difficulty,
            "max_invasiveness": context.max_invasiveness,
        },
    }

    return RecommendationsResponse(
        recommendations=recommendations,
        user_context_summary=context_summary,
        query=query,
        use_case=use_case,
    )


@router.get("/for-tool/{slug}", response_model=ToolGuidanceResponse)
async def get_guidance_for_tool(
    slug: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Get personalized guidance for a specific tool.

    Returns tailored training plan and rollout approach based on user's
    experience level, risk tolerance, and data sensitivity requirements.
    """
    result = get_tool_guidance(db, user, slug)

    if result is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    score, explanation, guidance, citations = result
    tool = get_tool(slug)

    return ToolGuidanceResponse(
        tool_slug=slug,
        tool_name=tool.get("name", slug),
        fit_score=score,
        explanation=explanation,
        guidance=guidance,
        citations=citations,
    )


@router.get("/suggested", response_model=SuggestedBlockResponse)
async def get_suggested_block(
    location: str = Query(..., description="UI location: home, tool_detail, cluster, finder"),
    cluster_slug: Optional[str] = Query(None, description="Current cluster context"),
    tool_slug: Optional[str] = Query(None, description="Current tool context"),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get suggested tools block for a UI location.

    Returns recommendations formatted for display in the specified location.
    For anonymous users, returns empty block (show_block=False).
    """
    if not user:
        return SuggestedBlockResponse(
            location=location,
            recommendations=[],
            title="",
            show_block=False,
        )

    recommendations = get_suggested_for_location(db, user, location)

    # Customize title based on location
    titles = {
        "home": "Suggested for You",
        "tool_detail": "You Might Also Like",
        "cluster": "Best Fit for You",
        "finder": "Personalized Picks",
    }
    title = titles.get(location, "Suggested for You")

    return SuggestedBlockResponse(
        location=location,
        recommendations=recommendations,
        title=title,
        show_block=len(recommendations) > 0,
    )
