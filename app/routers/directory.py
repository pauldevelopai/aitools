"""Directory routes for journalist and media organization management."""
import json
from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from app.db import get_db
from app.dependencies import require_admin
from app.models.auth import User
from app.models.directory import (
    MediaOrganization,
    Department,
    Team,
    Journalist,
    Engagement,
    JournalistNote,
    EngagementDocument,
)
from app.models.ai_journey import AIJourneyEntry
from app.templates_engine import templates
from app.products.admin_context import get_admin_context_dict
from app.workflows.audit import (
    log_workflow_start,
    log_workflow_complete,
    log_workflow_failure,
    log_content_action,
    log_rate_limit_hit,
    WorkflowAuditAction,
)
from app.workflows.rate_limit import check_workflow_rate_limit

router = APIRouter(prefix="/admin/directory", tags=["directory"])


# =============================================================================
# DASHBOARD
# =============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def directory_dashboard(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Directory dashboard with overview stats."""
    # Get counts
    org_count = db.query(func.count(MediaOrganization.id)).scalar() or 0
    journalist_count = db.query(func.count(Journalist.id)).scalar() or 0
    engagement_count = db.query(func.count(Engagement.id)).scalar() or 0

    # Engagements this month
    today = date.today()
    first_of_month = today.replace(day=1)
    this_month_count = db.query(func.count(Engagement.id)).filter(
        Engagement.date >= first_of_month
    ).scalar() or 0

    # Recent engagements
    recent_engagements = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist))
        .order_by(desc(Engagement.date))
        .limit(10)
        .all()
    )

    # Upcoming follow-ups
    upcoming_followups = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist))
        .filter(Engagement.follow_up_date >= today)
        .order_by(Engagement.follow_up_date)
        .limit(10)
        .all()
    )

    # Skill level distribution
    skill_distribution = (
        db.query(Journalist.ai_skill_level, func.count(Journalist.id))
        .group_by(Journalist.ai_skill_level)
        .all()
    )
    skill_stats = {level or "none": count for level, count in skill_distribution}

    # Organizations for quick-add dropdown
    organizations = db.query(MediaOrganization).filter(MediaOrganization.is_active == True).order_by(MediaOrganization.name).all()

    # AI Journey stage distribution
    journey_distribution = (
        db.query(MediaOrganization.ai_journey_stage, func.count(MediaOrganization.id))
        .group_by(MediaOrganization.ai_journey_stage)
        .all()
    )
    journey_stats = {stage or "not_started": count for stage, count in journey_distribution}

    # Recently added organizations
    recent_orgs = (
        db.query(MediaOrganization)
        .order_by(desc(MediaOrganization.created_at))
        .limit(10)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": {
                "organizations": org_count,
                "journalists": journalist_count,
                "engagements": engagement_count,
                "this_month": this_month_count,
            },
            "skill_stats": skill_stats,
            "journey_stats": journey_stats,
            "recent_orgs": recent_orgs,
            "recent_engagements": recent_engagements,
            "upcoming_followups": upcoming_followups,
            "organizations": organizations,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


# =============================================================================
# ORGANIZATIONS
# =============================================================================

@router.get("/organizations", response_class=HTMLResponse)
async def list_organizations(
    request: Request,
    org_type: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all media organizations."""
    from app.models.organization_profile import OrganizationProfile

    query = db.query(MediaOrganization).options(joinedload(MediaOrganization.client))

    if org_type:
        query = query.filter(MediaOrganization.org_type == org_type)
    if country:
        query = query.filter(MediaOrganization.country == country)
    if search:
        query = query.filter(MediaOrganization.name.ilike(f"%{search}%"))
    if client_id:
        query = query.filter(MediaOrganization.client_id == client_id)
    if journey_stage:
        query = query.filter(MediaOrganization.ai_journey_stage == journey_stage)

    # Pagination
    per_page = 50
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    organizations = query.order_by(MediaOrganization.name).offset((page - 1) * per_page).limit(per_page).all()

    # Get journalist counts for each org
    org_journalist_counts = dict(
        db.query(Journalist.organization_id, func.count(Journalist.id))
        .group_by(Journalist.organization_id)
        .all()
    )

    # Get unique countries and types for filters
    countries = db.query(MediaOrganization.country).distinct().filter(
        MediaOrganization.country.isnot(None)
    ).all()
    org_types = db.query(MediaOrganization.org_type).distinct().all()

    # Get clients for filter dropdown
    clients = db.query(OrganizationProfile).order_by(OrganizationProfile.name).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/organizations.html",
        {
            "request": request,
            "user": user,
            "organizations": organizations,
            "org_journalist_counts": org_journalist_counts,
            "countries": [c[0] for c in countries if c[0]],
            "org_types": [t[0] for t in org_types if t[0]],
            "clients": clients,
            "filters": {"org_type": org_type, "country": country, "search": search, "client_id": client_id, "journey_stage": journey_stage},
            "current_page": page,
            "total_pages": total_pages,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.get("/organizations/new", response_class=HTMLResponse)
async def new_organization_form(
    request: Request,
    user: User = Depends(require_admin),
):
    """Show form to create a new organization."""
    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/organization_form.html",
        {
            "request": request,
            "user": user,
            "organization": None,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/organizations")
async def create_organization(
    request: Request,
    name: str = Form(...),
    org_type: str = Form(...),
    country: str = Form(None),
    website: str = Form(None),
    logo_url: str = Form(None),
    description: str = Form(None),
    notes: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new media organization."""
    org = MediaOrganization(
        name=name,
        org_type=org_type,
        country=country or None,
        website=website or None,
        logo_url=logo_url or None,
        description=description or None,
        notes=notes or None,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    return RedirectResponse(url=f"/admin/directory/organizations/{org.id}", status_code=303)


@router.get("/organizations/{org_id}", response_class=HTMLResponse)
async def organization_detail(
    org_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show organization detail with departments, teams, and journalists."""
    org = (
        db.query(MediaOrganization)
        .options(
            joinedload(MediaOrganization.departments).joinedload(Department.teams),
            joinedload(MediaOrganization.journalists),
            joinedload(MediaOrganization.journey_entries).joinedload(AIJourneyEntry.recorded_by),
        )
        .filter(MediaOrganization.id == org_id)
        .first()
    )

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get engagement history for this org's journalists
    journalist_ids = [j.id for j in org.journalists]
    engagements = []
    if journalist_ids:
        engagements = (
            db.query(Engagement)
            .options(joinedload(Engagement.journalist))
            .filter(Engagement.journalist_id.in_(journalist_ids))
            .order_by(desc(Engagement.date))
            .limit(20)
            .all()
        )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/organization_detail.html",
        {
            "request": request,
            "user": user,
            "organization": org,
            "engagements": engagements,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.get("/organizations/{org_id}/edit", response_class=HTMLResponse)
async def edit_organization_form(
    org_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to edit an organization."""
    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/organization_form.html",
        {
            "request": request,
            "user": user,
            "organization": org,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/organizations/{org_id}")
async def update_organization(
    org_id: str,
    name: str = Form(...),
    org_type: str = Form(...),
    country: str = Form(None),
    website: str = Form(None),
    logo_url: str = Form(None),
    description: str = Form(None),
    notes: str = Form(None),
    is_active: bool = Form(True),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update an organization."""
    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.name = name
    org.org_type = org_type
    org.country = country or None
    org.website = website or None
    org.logo_url = logo_url or None
    org.description = description or None
    org.notes = notes or None
    org.is_active = is_active

    db.commit()

    return RedirectResponse(url=f"/admin/directory/organizations/{org_id}", status_code=303)


@router.post("/organizations/{org_id}/delete")
async def delete_organization(
    org_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an organization (and cascade to departments/teams)."""
    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    db.delete(org)
    db.commit()

    return RedirectResponse(url="/admin/directory/organizations", status_code=303)


# =============================================================================
# AI JOURNEY
# =============================================================================

JOURNEY_STAGES = [
    ("not_started", "Not Started"),
    ("awareness", "Awareness"),
    ("exploring", "Exploring"),
    ("piloting", "Piloting"),
    ("implementing", "Implementing"),
    ("integrated", "Integrated"),
    ("advanced", "Advanced"),
]


@router.get("/organizations/{org_id}/journey", response_class=HTMLResponse)
async def journey_detail(
    org_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show journey detail and update form for an organization."""
    org = (
        db.query(MediaOrganization)
        .options(joinedload(MediaOrganization.journey_entries).joinedload(AIJourneyEntry.recorded_by))
        .filter(MediaOrganization.id == org_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/journey_update.html",
        {
            "request": request,
            "user": user,
            "organization": org,
            "journey_stages": JOURNEY_STAGES,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/organizations/{org_id}/journey")
async def update_journey(
    org_id: str,
    stage: str = Form(...),
    notes: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save a new journey entry and update the org's current stage."""
    valid_stages = [s[0] for s in JOURNEY_STAGES]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")

    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    entry = AIJourneyEntry(
        organization_id=org.id,
        stage=stage,
        notes=notes or None,
        recorded_by_id=user.id,
    )
    db.add(entry)
    org.ai_journey_stage = stage
    db.commit()

    return RedirectResponse(url=f"/admin/directory/organizations/{org_id}/journey", status_code=303)


@router.post("/organizations/{org_id}/journey/quick")
async def quick_journey_update(
    org_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """AJAX quick stage update from dashboard."""
    data = await request.json()
    stage = data.get("stage")

    valid_stages = [s[0] for s in JOURNEY_STAGES]
    if stage not in valid_stages:
        return JSONResponse({"error": "Invalid stage"}, status_code=400)

    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        return JSONResponse({"error": "Organization not found"}, status_code=404)

    entry = AIJourneyEntry(
        organization_id=org.id,
        stage=stage,
        notes=f"Quick update from dashboard",
        recorded_by_id=user.id,
    )
    db.add(entry)
    org.ai_journey_stage = stage
    db.commit()

    return JSONResponse({"success": True, "stage": stage})


# =============================================================================
# DEPARTMENTS
# =============================================================================

@router.post("/organizations/{org_id}/departments")
async def create_department(
    org_id: str,
    name: str = Form(...),
    description: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a department to an organization."""
    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    dept = Department(
        organization_id=org.id,
        name=name,
        description=description or None,
    )
    db.add(dept)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/organizations/{org_id}", status_code=303)


@router.post("/departments/{dept_id}/delete")
async def delete_department(
    dept_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a department."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    org_id = dept.organization_id
    db.delete(dept)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/organizations/{org_id}", status_code=303)


# =============================================================================
# TEAMS
# =============================================================================

@router.post("/departments/{dept_id}/teams")
async def create_team(
    dept_id: str,
    name: str = Form(...),
    description: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a team to a department."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    team = Team(
        department_id=dept.id,
        name=name,
        description=description or None,
    )
    db.add(team)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/organizations/{dept.organization_id}", status_code=303)


@router.post("/teams/{team_id}/delete")
async def delete_team(
    team_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a team."""
    team = db.query(Team).options(joinedload(Team.department)).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    org_id = team.department.organization_id
    db.delete(team)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/organizations/{org_id}", status_code=303)


# =============================================================================
# JOURNALISTS
# =============================================================================

@router.get("/journalists", response_class=HTMLResponse)
async def list_journalists(
    request: Request,
    org_id: Optional[str] = Query(None),
    skill_level: Optional[str] = Query(None),
    beat: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all journalists with filters."""
    query = db.query(Journalist).options(joinedload(Journalist.organization))

    if org_id:
        query = query.filter(Journalist.organization_id == org_id)
    if skill_level:
        query = query.filter(Journalist.ai_skill_level == skill_level)
    if beat:
        query = query.filter(Journalist.beat.ilike(f"%{beat}%"))
    if search:
        query = query.filter(
            or_(
                Journalist.first_name.ilike(f"%{search}%"),
                Journalist.last_name.ilike(f"%{search}%"),
                Journalist.email.ilike(f"%{search}%"),
            )
        )

    journalists = query.order_by(Journalist.last_name, Journalist.first_name).all()

    # Get last engagement for each journalist
    last_engagements = {}
    journalist_ids = [j.id for j in journalists]
    if journalist_ids:
        subq = (
            db.query(
                Engagement.journalist_id,
                func.max(Engagement.date).label("last_date")
            )
            .filter(Engagement.journalist_id.in_(journalist_ids))
            .group_by(Engagement.journalist_id)
            .subquery()
        )
        results = db.query(subq.c.journalist_id, subq.c.last_date).all()
        last_engagements = {r[0]: r[1] for r in results}

    # Get organizations and beats for filters
    organizations = db.query(MediaOrganization).order_by(MediaOrganization.name).all()
    beats = db.query(Journalist.beat).distinct().filter(Journalist.beat.isnot(None)).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/journalists.html",
        {
            "request": request,
            "user": user,
            "journalists": journalists,
            "last_engagements": last_engagements,
            "organizations": organizations,
            "beats": [b[0] for b in beats if b[0]],
            "filters": {"org_id": org_id, "skill_level": skill_level, "beat": beat, "search": search},
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.get("/journalists/new", response_class=HTMLResponse)
async def new_journalist_form(
    request: Request,
    org_id: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to create a new journalist."""
    organizations = db.query(MediaOrganization).order_by(MediaOrganization.name).all()

    # Get departments and teams for the selected org
    departments = []
    teams = []
    if org_id:
        departments = db.query(Department).filter(Department.organization_id == org_id).all()
        dept_ids = [d.id for d in departments]
        if dept_ids:
            teams = db.query(Team).filter(Team.department_id.in_(dept_ids)).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/journalist_form.html",
        {
            "request": request,
            "user": user,
            "journalist": None,
            "organizations": organizations,
            "departments": departments,
            "teams": teams,
            "selected_org_id": org_id,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/journalists")
async def create_journalist(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    organization_id: str = Form(None),
    department_id: str = Form(None),
    team_id: str = Form(None),
    role: str = Form(None),
    beat: str = Form(None),
    bio: str = Form(None),
    photo_url: str = Form(None),
    twitter: str = Form(None),
    linkedin: str = Form(None),
    website: str = Form(None),
    ai_skill_level: str = Form("none"),
    areas_of_interest: str = Form("[]"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new journalist."""
    # Parse areas of interest
    try:
        interests = json.loads(areas_of_interest) if areas_of_interest else []
    except json.JSONDecodeError:
        interests = []

    journalist = Journalist(
        first_name=first_name,
        last_name=last_name,
        email=email or None,
        phone=phone or None,
        organization_id=organization_id if organization_id else None,
        department_id=department_id if department_id else None,
        team_id=team_id if team_id else None,
        role=role or None,
        beat=beat or None,
        bio=bio or None,
        photo_url=photo_url or None,
        twitter=twitter.lstrip("@") if twitter else None,
        linkedin=linkedin or None,
        website=website or None,
        ai_skill_level=ai_skill_level,
        areas_of_interest=interests,
    )
    db.add(journalist)
    db.commit()
    db.refresh(journalist)

    return RedirectResponse(url=f"/admin/directory/journalists/{journalist.id}", status_code=303)


@router.get("/journalists/{journalist_id}", response_class=HTMLResponse)
async def journalist_detail(
    journalist_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show journalist profile with AI journey timeline."""
    journalist = (
        db.query(Journalist)
        .options(
            joinedload(Journalist.organization),
            joinedload(Journalist.department),
            joinedload(Journalist.team),
            joinedload(Journalist.notes),
        )
        .filter(Journalist.id == journalist_id)
        .first()
    )

    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    # Get all engagements (AI journey timeline)
    engagements = (
        db.query(Engagement)
        .options(joinedload(Engagement.documents))
        .filter(Engagement.journalist_id == journalist_id)
        .order_by(desc(Engagement.date))
        .all()
    )

    # Calculate skill progression
    skill_progression = []
    for e in reversed(engagements):
        if e.skill_before or e.skill_after:
            skill_progression.append({
                "date": e.date,
                "title": e.title,
                "before": e.skill_before,
                "after": e.skill_after,
            })

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/journalist_detail.html",
        {
            "request": request,
            "user": user,
            "journalist": journalist,
            "engagements": engagements,
            "skill_progression": skill_progression,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.get("/journalists/{journalist_id}/edit", response_class=HTMLResponse)
async def edit_journalist_form(
    journalist_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to edit a journalist."""
    journalist = (
        db.query(Journalist)
        .options(
            joinedload(Journalist.organization),
            joinedload(Journalist.department),
            joinedload(Journalist.team),
        )
        .filter(Journalist.id == journalist_id)
        .first()
    )

    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    organizations = db.query(MediaOrganization).order_by(MediaOrganization.name).all()

    # Get departments and teams
    departments = []
    teams = []
    if journalist.organization_id:
        departments = db.query(Department).filter(Department.organization_id == journalist.organization_id).all()
        dept_ids = [d.id for d in departments]
        if dept_ids:
            teams = db.query(Team).filter(Team.department_id.in_(dept_ids)).all()

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/journalist_form.html",
        {
            "request": request,
            "user": user,
            "journalist": journalist,
            "organizations": organizations,
            "departments": departments,
            "teams": teams,
            "selected_org_id": str(journalist.organization_id) if journalist.organization_id else None,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/journalists/{journalist_id}")
async def update_journalist(
    journalist_id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    organization_id: str = Form(None),
    department_id: str = Form(None),
    team_id: str = Form(None),
    role: str = Form(None),
    beat: str = Form(None),
    bio: str = Form(None),
    photo_url: str = Form(None),
    twitter: str = Form(None),
    linkedin: str = Form(None),
    website: str = Form(None),
    ai_skill_level: str = Form("none"),
    areas_of_interest: str = Form("[]"),
    is_active: bool = Form(True),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a journalist."""
    journalist = db.query(Journalist).filter(Journalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    # Parse areas of interest
    try:
        interests = json.loads(areas_of_interest) if areas_of_interest else []
    except json.JSONDecodeError:
        interests = []

    journalist.first_name = first_name
    journalist.last_name = last_name
    journalist.email = email or None
    journalist.phone = phone or None
    journalist.organization_id = organization_id if organization_id else None
    journalist.department_id = department_id if department_id else None
    journalist.team_id = team_id if team_id else None
    journalist.role = role or None
    journalist.beat = beat or None
    journalist.bio = bio or None
    journalist.photo_url = photo_url or None
    journalist.twitter = twitter.lstrip("@") if twitter else None
    journalist.linkedin = linkedin or None
    journalist.website = website or None
    journalist.ai_skill_level = ai_skill_level
    journalist.areas_of_interest = interests
    journalist.is_active = is_active

    db.commit()

    return RedirectResponse(url=f"/admin/directory/journalists/{journalist_id}", status_code=303)


@router.post("/journalists/{journalist_id}/delete")
async def delete_journalist(
    journalist_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a journalist."""
    journalist = db.query(Journalist).filter(Journalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    db.delete(journalist)
    db.commit()

    return RedirectResponse(url="/admin/directory/journalists", status_code=303)


# =============================================================================
# ENGAGEMENTS
# =============================================================================

@router.get("/journalists/{journalist_id}/engagements/new", response_class=HTMLResponse)
async def new_engagement_form(
    journalist_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to create a new engagement."""
    journalist = db.query(Journalist).filter(Journalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/engagement_form.html",
        {
            "request": request,
            "user": user,
            "journalist": journalist,
            "engagement": None,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/journalists/{journalist_id}/engagements")
async def create_engagement(
    journalist_id: str,
    engagement_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    date: str = Form(...),
    duration_minutes: int = Form(None),
    location: str = Form(None),
    topics_covered: str = Form("[]"),
    materials_used: str = Form("[]"),
    outcomes: str = Form(None),
    follow_up_actions: str = Form(None),
    follow_up_date: str = Form(None),
    skill_before: str = Form(None),
    skill_after: str = Form(None),
    notes: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new engagement."""
    journalist = db.query(Journalist).filter(Journalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    # Parse JSON fields
    try:
        topics = json.loads(topics_covered) if topics_covered else []
    except json.JSONDecodeError:
        topics = []

    try:
        materials = json.loads(materials_used) if materials_used else []
    except json.JSONDecodeError:
        materials = []

    # Parse dates
    engagement_date = datetime.strptime(date, "%Y-%m-%d").date()
    followup = None
    if follow_up_date:
        followup = datetime.strptime(follow_up_date, "%Y-%m-%d").date()

    engagement = Engagement(
        journalist_id=journalist.id,
        engagement_type=engagement_type,
        title=title,
        description=description or None,
        date=engagement_date,
        duration_minutes=duration_minutes,
        location=location or None,
        topics_covered=topics,
        materials_used=materials,
        outcomes=outcomes or None,
        follow_up_actions=follow_up_actions or None,
        follow_up_date=followup,
        skill_before=skill_before or None,
        skill_after=skill_after or None,
        notes=notes or None,
    )
    db.add(engagement)

    # Update journalist skill level if skill_after is set
    if skill_after:
        journalist.ai_skill_level = skill_after

    db.commit()
    db.refresh(engagement)

    return RedirectResponse(url=f"/admin/directory/journalists/{journalist_id}", status_code=303)


@router.get("/engagements/{engagement_id}", response_class=HTMLResponse)
async def engagement_detail(
    engagement_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show engagement detail."""
    engagement = (
        db.query(Engagement)
        .options(
            joinedload(Engagement.journalist),
            joinedload(Engagement.documents),
        )
        .filter(Engagement.id == engagement_id)
        .first()
    )

    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/engagement_detail.html",
        {
            "request": request,
            "user": user,
            "engagement": engagement,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.get("/engagements/{engagement_id}/edit", response_class=HTMLResponse)
async def edit_engagement_form(
    engagement_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show form to edit an engagement."""
    engagement = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist))
        .filter(Engagement.id == engagement_id)
        .first()
    )

    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/engagement_form.html",
        {
            "request": request,
            "user": user,
            "journalist": engagement.journalist,
            "engagement": engagement,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/engagements/{engagement_id}")
async def update_engagement(
    engagement_id: str,
    engagement_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    date: str = Form(...),
    duration_minutes: int = Form(None),
    location: str = Form(None),
    topics_covered: str = Form("[]"),
    materials_used: str = Form("[]"),
    outcomes: str = Form(None),
    follow_up_actions: str = Form(None),
    follow_up_date: str = Form(None),
    skill_before: str = Form(None),
    skill_after: str = Form(None),
    notes: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update an engagement."""
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Parse JSON fields
    try:
        topics = json.loads(topics_covered) if topics_covered else []
    except json.JSONDecodeError:
        topics = []

    try:
        materials = json.loads(materials_used) if materials_used else []
    except json.JSONDecodeError:
        materials = []

    # Parse dates
    engagement_date = datetime.strptime(date, "%Y-%m-%d").date()
    followup = None
    if follow_up_date:
        followup = datetime.strptime(follow_up_date, "%Y-%m-%d").date()

    engagement.engagement_type = engagement_type
    engagement.title = title
    engagement.description = description or None
    engagement.date = engagement_date
    engagement.duration_minutes = duration_minutes
    engagement.location = location or None
    engagement.topics_covered = topics
    engagement.materials_used = materials
    engagement.outcomes = outcomes or None
    engagement.follow_up_actions = follow_up_actions or None
    engagement.follow_up_date = followup
    engagement.skill_before = skill_before or None
    engagement.skill_after = skill_after or None
    engagement.notes = notes or None

    db.commit()

    return RedirectResponse(url=f"/admin/directory/journalists/{engagement.journalist_id}", status_code=303)


@router.post("/engagements/{engagement_id}/delete")
async def delete_engagement(
    engagement_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an engagement."""
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    journalist_id = engagement.journalist_id
    db.delete(engagement)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/journalists/{journalist_id}", status_code=303)


# =============================================================================
# NOTES
# =============================================================================

@router.post("/journalists/{journalist_id}/notes")
async def create_note(
    journalist_id: str,
    content: str = Form(...),
    note_type: str = Form("general"),
    is_private: bool = Form(False),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a note to a journalist."""
    journalist = db.query(Journalist).filter(Journalist.id == journalist_id).first()
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    note = JournalistNote(
        journalist_id=journalist.id,
        content=content,
        note_type=note_type,
        is_private=is_private,
    )
    db.add(note)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/journalists/{journalist_id}", status_code=303)


@router.post("/notes/{note_id}/delete")
async def delete_note(
    note_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a note."""
    note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    journalist_id = note.journalist_id
    db.delete(note)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/journalists/{journalist_id}", status_code=303)


# =============================================================================
# ENGAGEMENT DOCUMENTS
# =============================================================================

@router.post("/engagements/{engagement_id}/documents")
async def add_engagement_document(
    engagement_id: str,
    title: str = Form(...),
    doc_type: str = Form(...),
    url: str = Form(None),
    notes: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a document to an engagement."""
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    doc = EngagementDocument(
        engagement_id=engagement.id,
        title=title,
        doc_type=doc_type,
        url=url or None,
        notes=notes or None,
    )
    db.add(doc)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/engagements/{engagement_id}", status_code=303)


@router.post("/documents/{doc_id}/delete")
async def delete_engagement_document(
    doc_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an engagement document."""
    doc = db.query(EngagementDocument).filter(EngagementDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    engagement_id = doc.engagement_id
    db.delete(doc)
    db.commit()

    return RedirectResponse(url=f"/admin/directory/engagements/{engagement_id}", status_code=303)


# =============================================================================
# SEARCH
# =============================================================================

@router.get("/search", response_class=HTMLResponse)
async def search_directory(
    request: Request,
    q: Optional[str] = Query(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Search across all directory entities."""
    results = {
        "organizations": [],
        "journalists": [],
        "engagements": [],
    }

    if q:
        search_term = f"%{q}%"

        # Search organizations
        results["organizations"] = (
            db.query(MediaOrganization)
            .filter(
                or_(
                    MediaOrganization.name.ilike(search_term),
                    MediaOrganization.description.ilike(search_term),
                )
            )
            .limit(10)
            .all()
        )

        # Search journalists
        results["journalists"] = (
            db.query(Journalist)
            .options(joinedload(Journalist.organization))
            .filter(
                or_(
                    Journalist.first_name.ilike(search_term),
                    Journalist.last_name.ilike(search_term),
                    Journalist.email.ilike(search_term),
                    Journalist.beat.ilike(search_term),
                )
            )
            .limit(10)
            .all()
        )

        # Search engagements
        results["engagements"] = (
            db.query(Engagement)
            .options(joinedload(Engagement.journalist))
            .filter(
                or_(
                    Engagement.title.ilike(search_term),
                    Engagement.description.ilike(search_term),
                )
            )
            .limit(10)
            .all()
        )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/search.html",
        {
            "request": request,
            "user": user,
            "query": q,
            "results": results,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


# =============================================================================
# API ENDPOINTS FOR DYNAMIC FORMS
# =============================================================================

@router.get("/api/organizations/{org_id}/departments")
async def get_organization_departments(
    org_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get departments for an organization (for dynamic form population)."""
    departments = db.query(Department).filter(Department.organization_id == org_id).all()
    return [{"id": str(d.id), "name": d.name} for d in departments]


@router.get("/api/departments/{dept_id}/teams")
async def get_department_teams(
    dept_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get teams for a department (for dynamic form population)."""
    teams = db.query(Team).filter(Team.department_id == dept_id).all()
    return [{"id": str(t.id), "name": t.name} for t in teams]


# =============================================================================
# AI INSIGHTS
# =============================================================================

# =============================================================================
# GROUNDED SYNC
# =============================================================================

@router.get("/sync", response_class=HTMLResponse)
async def sync_page():
    """Redirect to consolidated AI & Automation page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/agent/?tab=sync", status_code=302)


@router.post("/sync/all")
async def sync_all_to_grounded(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync all directory data to GROUNDED knowledge base."""
    from app.services.directory_sync import get_directory_sync_service

    sync_service = get_directory_sync_service()
    results = sync_service.sync_all(db)

    return results


@router.post("/sync/organizations")
async def sync_organizations_to_grounded(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync organizations to GROUNDED."""
    from app.services.directory_sync import get_directory_sync_service

    sync_service = get_directory_sync_service()
    return sync_service.sync_organizations(db)


@router.post("/sync/journalists")
async def sync_journalists_to_grounded(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync journalists to GROUNDED."""
    from app.services.directory_sync import get_directory_sync_service

    sync_service = get_directory_sync_service()
    return sync_service.sync_journalists(db)


@router.post("/sync/engagements")
async def sync_engagements_to_grounded(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync engagements to GROUNDED."""
    from app.services.directory_sync import get_directory_sync_service

    sync_service = get_directory_sync_service()
    return sync_service.sync_engagements(db)


@router.get("/sync/search")
async def search_grounded_directory(
    q: str = Query(...),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(10),
    user: User = Depends(require_admin),
):
    """Search the GROUNDED knowledge base."""
    from app.services.directory_sync import get_directory_sync_service

    sync_service = get_directory_sync_service()
    return sync_service.search(q, limit=limit, entity_type=entity_type)


# =============================================================================
# AI INSIGHTS
# =============================================================================

@router.get("/insights", response_class=HTMLResponse)
async def directory_insights(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """AI-powered insights page for the directory."""
    # Get summary stats for context
    org_count = db.query(func.count(MediaOrganization.id)).scalar() or 0
    journalist_count = db.query(func.count(Journalist.id)).scalar() or 0
    engagement_count = db.query(func.count(Engagement.id)).scalar() or 0

    # Skill distribution
    skill_distribution = (
        db.query(Journalist.ai_skill_level, func.count(Journalist.id))
        .group_by(Journalist.ai_skill_level)
        .all()
    )
    skill_stats = {level or "none": count for level, count in skill_distribution}

    # Engagement type distribution
    engagement_types = (
        db.query(Engagement.engagement_type, func.count(Engagement.id))
        .group_by(Engagement.engagement_type)
        .all()
    )

    # Organizations by type
    org_types = (
        db.query(MediaOrganization.org_type, func.count(MediaOrganization.id))
        .group_by(MediaOrganization.org_type)
        .all()
    )

    # Top organizations by journalist count
    top_orgs = (
        db.query(
            MediaOrganization.name,
            func.count(Journalist.id).label("journalist_count")
        )
        .outerjoin(Journalist, Journalist.organization_id == MediaOrganization.id)
        .group_by(MediaOrganization.id)
        .order_by(desc("journalist_count"))
        .limit(10)
        .all()
    )

    # Recent skill progressions
    recent_progressions = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist))
        .filter(Engagement.skill_after.isnot(None))
        .order_by(desc(Engagement.date))
        .limit(10)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/insights.html",
        {
            "request": request,
            "user": user,
            "stats": {
                "organizations": org_count,
                "journalists": journalist_count,
                "engagements": engagement_count,
            },
            "skill_stats": skill_stats,
            "engagement_types": engagement_types,
            "org_types": org_types,
            "top_orgs": top_orgs,
            "recent_progressions": recent_progressions,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/insights/query")
async def query_directory_insights(
    request: Request,
    question: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Query the directory with natural language using an LLM."""
    import os
    from openai import OpenAI

    # Gather comprehensive data for the LLM
    organizations = db.query(MediaOrganization).all()
    journalists = (
        db.query(Journalist)
        .options(joinedload(Journalist.organization))
        .all()
    )
    engagements = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist))
        .order_by(desc(Engagement.date))
        .limit(100)
        .all()
    )

    # Build context for the LLM
    org_data = []
    for org in organizations:
        journalist_count = sum(1 for j in journalists if j.organization_id == org.id)
        org_data.append(f"- {org.name} ({org.org_type}, {org.country or 'Unknown country'}): {journalist_count} journalists")

    journalist_data = []
    for j in journalists:
        org_name = j.organization.name if j.organization else "Freelance"
        journalist_data.append(
            f"- {j.full_name} | Org: {org_name} | Role: {j.role or 'N/A'} | "
            f"Beat: {j.beat or 'N/A'} | AI Skill: {j.ai_skill_level} | "
            f"Email: {j.email or 'N/A'}"
        )

    engagement_data = []
    for e in engagements:
        engagement_data.append(
            f"- {e.date.strftime('%Y-%m-%d')}: {e.journalist.full_name} - {e.title} ({e.engagement_type}) | "
            f"Skill: {e.skill_before or '?'} -> {e.skill_after or '?'}"
        )

    # Skill stats
    skill_counts = {}
    for j in journalists:
        level = j.ai_skill_level or "none"
        skill_counts[level] = skill_counts.get(level, 0) + 1

    context = f"""You are an AI assistant helping analyze a media directory CRM system. Here is the current data:

## Summary
- Organizations: {len(organizations)}
- Journalists: {len(journalists)}
- Engagements: {len(engagements)} (showing most recent 100)

## AI Skill Distribution
{chr(10).join(f"- {k}: {v}" for k, v in skill_counts.items())}

## Organizations ({len(organizations)} total)
{chr(10).join(org_data[:30])}
{"... and more" if len(org_data) > 30 else ""}

## Journalists ({len(journalists)} total)
{chr(10).join(journalist_data[:50])}
{"... and more" if len(journalist_data) > 50 else ""}

## Recent Engagements (Training Sessions)
{chr(10).join(engagement_data[:30])}
{"... and more" if len(engagement_data) > 30 else ""}
"""

    # Call OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI assistant helping an admin analyze their media directory CRM.
You have access to data about journalists, media organizations, and AI training engagements.
Provide helpful, specific insights based on the data. When listing people or organizations, use their actual names from the data.
If asked about connections or patterns, analyze the data thoroughly.
Format your response with clear sections and bullet points where appropriate.
Be concise but thorough."""
                },
                {
                    "role": "user",
                    "content": f"""Based on this directory data:

{context}

User's question: {question}

Please provide a helpful, detailed response based on the actual data."""
                }
            ],
            max_tokens=1500,
            temperature=0.7
        )

        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Error generating insights: {str(e)}"

    # Return JSON for AJAX
    return {"question": question, "answer": answer}


@router.get("/insights/summary")
async def generate_directory_summary(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate an AI summary of the entire directory."""
    import os
    from openai import OpenAI

    # Get all data
    organizations = db.query(MediaOrganization).all()
    journalists = db.query(Journalist).options(joinedload(Journalist.organization)).all()
    engagements = db.query(Engagement).options(joinedload(Engagement.journalist)).all()

    # Calculate metrics
    skill_counts = {}
    for j in journalists:
        level = j.ai_skill_level or "none"
        skill_counts[level] = skill_counts.get(level, 0) + 1

    engagement_counts = {}
    for e in engagements:
        engagement_counts[e.engagement_type] = engagement_counts.get(e.engagement_type, 0) + 1

    orgs_by_type = {}
    for o in organizations:
        orgs_by_type[o.org_type] = orgs_by_type.get(o.org_type, 0) + 1

    # Find journalists who progressed
    progressions = [e for e in engagements if e.skill_before and e.skill_after and e.skill_before != e.skill_after]

    context = f"""Directory Overview:
- {len(organizations)} organizations across types: {orgs_by_type}
- {len(journalists)} journalists with skill distribution: {skill_counts}
- {len(engagements)} total engagements: {engagement_counts}
- {len(progressions)} skill progressions recorded

Organizations: {[o.name for o in organizations[:20]]}
Recent engagements: {[(e.journalist.full_name, e.title, e.date.strftime('%Y-%m-%d')) for e in engagements[:20]]}
"""

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant providing executive summaries of a media directory CRM."
                },
                {
                    "role": "user",
                    "content": f"""Generate a brief executive summary of this media directory, highlighting:
1. Key statistics
2. Notable patterns or trends
3. Potential opportunities
4. Suggested next actions

Data:
{context}"""
                }
            ],
            max_tokens=800
        )
        summary = response.choices[0].message.content
    except Exception as e:
        summary = f"Error: {str(e)}"

    return {"summary": summary}


# =============================================================================
# PARTNER INTELLIGENCE - WEB ENRICHMENT
# =============================================================================

@router.post("/organizations/{org_id}/enrich")
async def trigger_organization_enrichment(
    org_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Trigger Partner Intelligence workflow to enrich an organization from the web."""
    from app.workflows.runtime import WorkflowRuntime
    from app.workflows.partner_intelligence import WORKFLOW_NAME
    from app.workflows.partner_intelligence.graph import run_partner_intelligence

    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.website:
        raise HTTPException(status_code=400, detail="Organization has no website URL")

    # Check rate limit
    allowed, retry_after, reason = check_workflow_rate_limit(
        workflow_name=WORKFLOW_NAME,
        user_id=str(user.id),
        resource_id=org_id,
    )
    if not allowed:
        log_rate_limit_hit(
            workflow_name=WORKFLOW_NAME,
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="organization",
            resource_id=org_id,
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # Create workflow run record
    runtime = WorkflowRuntime(db)
    workflow_run = runtime.create_run(
        workflow_name=WORKFLOW_NAME,
        inputs={
            "organization_id": str(org.id),
            "organization_name": org.name,
            "website_url": org.website,
        },
        triggered_by=user.id,
        tags=["partner_intelligence", "enrichment"],
    )

    # Log workflow start
    log_workflow_start(
        workflow_name=WORKFLOW_NAME,
        workflow_run_id=str(workflow_run.id),
        actor_id=str(user.id),
        actor_email=user.email,
        resource_type="organization",
        resource_id=org_id,
        inputs_summary={"organization_name": org.name, "website": org.website},
    )

    # Execute the workflow asynchronously (in background)
    import asyncio
    import time as time_module

    async def run_enrichment():
        start_time = time_module.time()
        try:
            # Create a new database session for the background task
            from app.db import SessionLocal
            bg_db = SessionLocal()
            try:
                result = await run_partner_intelligence(
                    organization_id=str(org.id),
                    organization_name=org.name,
                    website_url=org.website,
                    current_description=org.description,
                    current_notes=org.notes,
                    db_session=bg_db,
                    workflow_run_id=str(workflow_run.id),
                )

                # Update workflow run with results
                bg_runtime = WorkflowRuntime(bg_db)
                run = bg_runtime.get_run(workflow_run.id)
                if run:
                    if result.get("needs_review"):
                        bg_runtime.update_status(
                            run,
                            status="needs_review",
                            outputs=result,
                            state=result.get("__state__", {}),
                            review_required=result.get("review_reason"),
                        )
                    else:
                        bg_runtime.update_status(
                            run,
                            status="completed",
                            outputs=result,
                        )

                # Log workflow completion
                log_workflow_complete(
                    workflow_name=WORKFLOW_NAME,
                    workflow_run_id=str(workflow_run.id),
                    actor_id=str(user.id),
                    outputs_summary={"status": result.get("needs_review", False) and "needs_review" or "completed"},
                    duration_seconds=time_module.time() - start_time,
                )
            finally:
                bg_db.close()
        except Exception as e:
            # Log error and update workflow run
            import traceback
            traceback.print_exc()

            # Log workflow failure
            log_workflow_failure(
                workflow_name=WORKFLOW_NAME,
                workflow_run_id=str(workflow_run.id),
                error_message=str(e),
                actor_id=str(user.id),
            )

            from app.db import SessionLocal
            err_db = SessionLocal()
            try:
                err_runtime = WorkflowRuntime(err_db)
                run = err_runtime.get_run(workflow_run.id)
                if run:
                    err_runtime.update_status(
                        run,
                        status="failed",
                        error_message=str(e),
                    )
            finally:
                err_db.close()

    # Run in background
    asyncio.create_task(run_enrichment())

    # Return immediately with workflow run info
    return {
        "status": "started",
        "workflow_run_id": str(workflow_run.id),
        "message": f"Enrichment started for {org.name}",
    }


@router.get("/organizations/{org_id}/enrichment-status")
async def get_organization_enrichment_status(
    org_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get the latest enrichment status for an organization."""
    from app.models.workflow import WorkflowRun

    # Find the most recent enrichment workflow run for this org
    latest_run = (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.workflow_name == "partner_intelligence",
            WorkflowRun.inputs["organization_id"].astext == org_id,
        )
        .order_by(desc(WorkflowRun.created_at))
        .first()
    )

    if not latest_run:
        return {"status": "none", "message": "No enrichment has been run"}

    return {
        "status": latest_run.status,
        "workflow_run_id": str(latest_run.id),
        "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
        "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
        "error_message": latest_run.error_message,
        "review_required": latest_run.review_required,
        "outputs": latest_run.outputs,
    }


@router.get("/enrichment/needs-review", response_class=HTMLResponse)
async def enrichment_needs_review_queue(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show queue of enrichment runs that need human review."""
    from app.models.workflow import WorkflowRun

    pending_reviews = (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.workflow_name == "partner_intelligence",
            WorkflowRun.status == "needs_review",
        )
        .order_by(desc(WorkflowRun.created_at))
        .all()
    )

    # Get organization details for each run
    org_ids = [
        run.inputs.get("organization_id")
        for run in pending_reviews
        if run.inputs and run.inputs.get("organization_id")
    ]
    organizations = {}
    if org_ids:
        orgs = db.query(MediaOrganization).filter(MediaOrganization.id.in_(org_ids)).all()
        organizations = {str(o.id): o for o in orgs}

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/enrichment_review.html",
        {
            "request": request,
            "user": user,
            "pending_reviews": pending_reviews,
            "organizations": organizations,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/enrichment/{run_id}/approve")
async def approve_enrichment(
    run_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve a pending enrichment and apply changes."""
    from app.models.workflow import WorkflowRun
    from app.workflows.runtime import WorkflowRuntime
    from app.workflows.partner_intelligence.nodes import CONFIDENCE_THRESHOLD

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    if run.status != "needs_review":
        raise HTTPException(status_code=400, detail="Run is not pending review")

    # Get the organization
    org_id = run.inputs.get("organization_id") if run.inputs else None
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization ID in run")

    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Apply enrichment from outputs
    outputs = run.outputs or {}
    enrichment = outputs.get("enrichment", {})
    extracted_fields = outputs.get("extracted_fields", [])

    changes = []

    # Update description
    new_description = enrichment.get("description")
    if new_description:
        if not org.description or len(org.description.strip()) < 50:
            org.description = new_description
            changes.append("description")

    # Build enrichment notes
    enrichment_notes = []
    if enrichment.get("focus_areas"):
        enrichment_notes.append(f"Focus Areas: {', '.join(enrichment['focus_areas'])}")
    if enrichment.get("countries_served"):
        enrichment_notes.append(f"Countries/Regions: {', '.join(enrichment['countries_served'])}")
    if enrichment.get("programs"):
        enrichment_notes.append(f"Programs: {', '.join(enrichment['programs'])}")
    if enrichment.get("key_people"):
        people_strs = [f"{p.get('name', '?')} ({p.get('role', '?')})" for p in enrichment["key_people"][:5]]
        enrichment_notes.append(f"Key People: {', '.join(people_strs)}")

    if enrichment_notes:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        enrichment_section = f"\n\n--- Auto-enriched {timestamp} (approved) ---\n" + "\n".join(enrichment_notes)
        if org.notes:
            if "Auto-enriched" not in org.notes:
                org.notes = org.notes + enrichment_section
        else:
            org.notes = enrichment_section.strip()
        changes.append("notes")

    # Save evidence sources
    from app.models.evidence import EvidenceSource
    for field in extracted_fields:
        evidence = EvidenceSource(
            organization_id=org_id,
            source_url=field.get("source_url", run.inputs.get("website_url", "")),
            source_type="webpage",
            field_name=field.get("field_name", ""),
            extracted_value=str(field.get("value", "")),
            confidence_score=field.get("confidence"),
            extraction_method=field.get("extraction_method", "llm"),
            extraction_model="gpt-4o-mini",
            workflow_run_id=run.id,
        )
        db.add(evidence)

    # Update workflow run status
    runtime = WorkflowRuntime(db)
    runtime.submit_review(run, "approved", user.id)

    db.commit()

    return {
        "status": "approved",
        "changes": changes,
        "redirect_url": f"/admin/directory/organizations/{org_id}",
    }


@router.post("/enrichment/{run_id}/reject")
async def reject_enrichment(
    run_id: str,
    reason: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reject a pending enrichment."""
    from app.models.workflow import WorkflowRun
    from app.workflows.runtime import WorkflowRuntime

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    if run.status != "needs_review":
        raise HTTPException(status_code=400, detail="Run is not pending review")

    runtime = WorkflowRuntime(db)
    run.error_message = f"Rejected: {reason}" if reason else "Rejected by admin"
    runtime.submit_review(run, "rejected", user.id)

    db.commit()

    return {"status": "rejected"}


@router.get("/organizations/{org_id}/evidence", response_class=HTMLResponse)
async def organization_evidence_sources(
    org_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show evidence sources for an organization."""
    from app.models.evidence import EvidenceSource, WebPageSnapshot

    org = db.query(MediaOrganization).filter(MediaOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    evidence_sources = (
        db.query(EvidenceSource)
        .filter(EvidenceSource.organization_id == org_id)
        .order_by(desc(EvidenceSource.created_at))
        .all()
    )

    snapshots = (
        db.query(WebPageSnapshot)
        .filter(WebPageSnapshot.organization_id == org_id)
        .order_by(desc(WebPageSnapshot.fetched_at))
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/organization_evidence.html",
        {
            "request": request,
            "user": user,
            "organization": org,
            "evidence_sources": evidence_sources,
            "snapshots": snapshots,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


# =============================================================================
# MENTOR WORKFLOW
# =============================================================================

@router.post("/engagements/{engagement_id}/mentor/charter")
async def generate_prototype_charter(
    engagement_id: str,
    journalist_goals: str = Form(""),
    project_idea: str = Form(""),
    current_challenges: str = Form(""),
    available_time: str = Form(""),
    technical_comfort: str = Form(""),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate Prototype Charter using the Intake workflow."""
    from app.workflows.runtime import WorkflowRuntime
    from app.workflows.mentor import run_intake, WORKFLOW_INTAKE
    from app.models.mentor import MentorArtifact, MentorTask
    import time as time_module

    engagement = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist).joinedload(Journalist.organization))
        .filter(Engagement.id == engagement_id)
        .first()
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Check rate limit
    allowed, retry_after, reason = check_workflow_rate_limit(
        workflow_name=WORKFLOW_INTAKE,
        user_id=str(user.id),
        resource_id=engagement_id,
    )
    if not allowed:
        log_rate_limit_hit(
            workflow_name=WORKFLOW_INTAKE,
            actor_id=str(user.id),
            actor_email=user.email,
            resource_type="engagement",
            resource_id=engagement_id,
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    journalist = engagement.journalist
    org = journalist.organization if journalist else None

    # Create workflow run record
    runtime = WorkflowRuntime(db)
    workflow_run = runtime.create_run(
        workflow_name=WORKFLOW_INTAKE,
        inputs={
            "engagement_id": str(engagement.id),
            "journalist_name": journalist.full_name if journalist else "Unknown",
        },
        triggered_by=user.id,
        tags=["mentor", "intake", "charter"],
    )

    # Log workflow start
    log_workflow_start(
        workflow_name=WORKFLOW_INTAKE,
        workflow_run_id=str(workflow_run.id),
        actor_id=str(user.id),
        actor_email=user.email,
        resource_type="engagement",
        resource_id=engagement_id,
        inputs_summary={"journalist": journalist.full_name if journalist else "Unknown"},
    )

    start_time = time_module.time()

    # Run the intake workflow
    try:
        runtime.update_status(workflow_run, "running")

        result = await run_intake(
            engagement_id=str(engagement.id),
            journalist_name=journalist.full_name if journalist else "Unknown",
            journalist_role=journalist.role or "" if journalist else "",
            journalist_organization=org.name if org else "",
            journalist_skill_level=journalist.ai_skill_level if journalist else "beginner",
            engagement_title=engagement.title,
            engagement_description=engagement.description or "",
            engagement_topics=engagement.topics_covered or [],
            journalist_goals=journalist_goals,
            project_idea=project_idea,
            current_challenges=current_challenges,
            available_time=available_time,
            technical_comfort=technical_comfort,
            workflow_run_id=str(workflow_run.id),
        )

        # Save the Prototype Charter artifact
        charter_content = result.get("charter_content", "")
        if charter_content:
            # Check for existing charter and increment version
            existing = (
                db.query(MentorArtifact)
                .filter(
                    MentorArtifact.engagement_id == engagement_id,
                    MentorArtifact.artifact_type == "prototype_charter",
                    MentorArtifact.is_current == True,
                )
                .first()
            )

            if existing:
                existing.is_current = False
                version = existing.version + 1
            else:
                version = 1

            artifact = MentorArtifact(
                engagement_id=engagement_id,
                artifact_type="prototype_charter",
                title=f"Prototype Charter v{version}",
                version=version,
                is_current=True,
                content=charter_content,
                content_format="markdown",
                structured_data=result.get("charter_structured", {}),
                created_by_workflow="intake",
                workflow_run_id=workflow_run.id,
            )
            db.add(artifact)

        # Save initial tasks
        initial_tasks = result.get("initial_tasks", [])
        for i, task_data in enumerate(initial_tasks):
            task = MentorTask(
                engagement_id=engagement_id,
                title=task_data.get("title", "Untitled Task"),
                description=task_data.get("description", ""),
                task_type=task_data.get("task_type", "action"),
                priority=task_data.get("priority", 2),
                assigned_to=task_data.get("assigned_to", "journalist"),
                created_by_workflow="intake",
                workflow_run_id=workflow_run.id,
                sort_order=i,
            )
            db.add(task)

        runtime.update_status(
            workflow_run,
            "completed",
            outputs=result,
        )

        db.commit()

        # Log workflow completion
        log_workflow_complete(
            workflow_name=WORKFLOW_INTAKE,
            workflow_run_id=str(workflow_run.id),
            actor_id=str(user.id),
            outputs_summary={"charter_created": bool(charter_content), "tasks_created": len(initial_tasks)},
            duration_seconds=time_module.time() - start_time,
        )

        return {
            "status": "completed",
            "charter_created": bool(charter_content),
            "tasks_created": len(initial_tasks),
            "workflow_run_id": str(workflow_run.id),
        }

    except Exception as e:
        import traceback

        # Log workflow failure
        log_workflow_failure(
            workflow_name=WORKFLOW_INTAKE,
            workflow_run_id=str(workflow_run.id),
            error_message=str(e),
            actor_id=str(user.id),
        )

        runtime.update_status(
            workflow_run,
            "failed",
            error_message=str(e),
        )
        workflow_run.error_traceback = traceback.format_exc()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engagements/{engagement_id}/mentor/agenda")
async def generate_session_agenda(
    engagement_id: str,
    session_number: int = Form(1),
    session_focus: str = Form(""),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate session agenda using the Pre-Call workflow."""
    from app.workflows.runtime import WorkflowRuntime
    from app.workflows.mentor import run_pre_call, WORKFLOW_PRE_CALL
    from app.models.mentor import MentorArtifact, MentorTask

    engagement = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist).joinedload(Journalist.organization))
        .filter(Engagement.id == engagement_id)
        .first()
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    journalist = engagement.journalist
    org = journalist.organization if journalist else None

    # Get existing charter
    charter = (
        db.query(MentorArtifact)
        .filter(
            MentorArtifact.engagement_id == engagement_id,
            MentorArtifact.artifact_type == "prototype_charter",
            MentorArtifact.is_current == True,
        )
        .first()
    )

    # Get open and completed tasks
    open_tasks = (
        db.query(MentorTask)
        .filter(
            MentorTask.engagement_id == engagement_id,
            MentorTask.status.in_(["pending", "in_progress"]),
        )
        .order_by(MentorTask.priority, MentorTask.sort_order)
        .all()
    )
    completed_tasks = (
        db.query(MentorTask)
        .filter(
            MentorTask.engagement_id == engagement_id,
            MentorTask.status == "completed",
        )
        .order_by(desc(MentorTask.completed_at))
        .limit(10)
        .all()
    )

    # Create workflow run record
    runtime = WorkflowRuntime(db)
    workflow_run = runtime.create_run(
        workflow_name=WORKFLOW_PRE_CALL,
        inputs={
            "engagement_id": str(engagement.id),
            "session_number": session_number,
        },
        triggered_by=user.id,
        tags=["mentor", "pre_call", "agenda"],
    )

    try:
        runtime.update_status(workflow_run, "running")

        result = await run_pre_call(
            engagement_id=str(engagement.id),
            session_number=session_number,
            journalist_name=journalist.full_name if journalist else "Unknown",
            journalist_organization=org.name if org else "",
            charter_content=charter.content if charter else "",
            previous_decisions=[],  # TODO: Get from decision log artifact
            open_tasks=[{"title": t.title, "description": t.description, "priority": t.priority} for t in open_tasks],
            completed_tasks=[{"title": t.title} for t in completed_tasks],
            previous_session_notes=engagement.notes or "",
            session_focus=session_focus,
            workflow_run_id=str(workflow_run.id),
        )

        # Save the agenda artifact
        agenda_content = result.get("agenda_content", "")
        if agenda_content:
            artifact = MentorArtifact(
                engagement_id=engagement_id,
                artifact_type="session_agenda",
                title=f"Session {session_number} Agenda",
                version=1,
                is_current=True,
                content=agenda_content,
                content_format="markdown",
                structured_data={
                    "session_number": session_number,
                    "key_questions": result.get("key_questions", []),
                    "suggested_topics": result.get("suggested_topics", []),
                    "time_allocations": result.get("time_allocations", {}),
                },
                created_by_workflow="pre_call",
                workflow_run_id=workflow_run.id,
            )
            db.add(artifact)

        runtime.update_status(
            workflow_run,
            "completed",
            outputs=result,
        )

        db.commit()

        return {
            "status": "completed",
            "agenda_created": bool(agenda_content),
            "key_questions": len(result.get("key_questions", [])),
            "workflow_run_id": str(workflow_run.id),
        }

    except Exception as e:
        import traceback
        runtime.update_status(
            workflow_run,
            "failed",
            error_message=str(e),
        )
        workflow_run.error_traceback = traceback.format_exc()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engagements/{engagement_id}/mentor/pack")
async def generate_prototype_pack(
    engagement_id: str,
    session_number: int = Form(1),
    session_notes: str = Form(""),
    session_duration: int = Form(60),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate Prototype Pack using the Post-Call workflow."""
    from app.workflows.runtime import WorkflowRuntime
    from app.workflows.mentor import run_post_call, WORKFLOW_POST_CALL
    from app.models.mentor import MentorArtifact, MentorTask, MentorSession

    if not session_notes:
        raise HTTPException(status_code=400, detail="Session notes are required")

    engagement = (
        db.query(Engagement)
        .options(joinedload(Engagement.journalist).joinedload(Journalist.organization))
        .filter(Engagement.id == engagement_id)
        .first()
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    journalist = engagement.journalist
    org = journalist.organization if journalist else None

    # Get existing charter
    charter = (
        db.query(MentorArtifact)
        .filter(
            MentorArtifact.engagement_id == engagement_id,
            MentorArtifact.artifact_type == "prototype_charter",
            MentorArtifact.is_current == True,
        )
        .first()
    )

    # Get current tasks
    current_tasks = (
        db.query(MentorTask)
        .filter(MentorTask.engagement_id == engagement_id)
        .order_by(MentorTask.priority, MentorTask.sort_order)
        .all()
    )

    # Create workflow run record
    runtime = WorkflowRuntime(db)
    workflow_run = runtime.create_run(
        workflow_name=WORKFLOW_POST_CALL,
        inputs={
            "engagement_id": str(engagement.id),
            "session_number": session_number,
        },
        triggered_by=user.id,
        tags=["mentor", "post_call", "pack"],
    )

    try:
        runtime.update_status(workflow_run, "running")

        result = await run_post_call(
            engagement_id=str(engagement.id),
            session_number=session_number,
            journalist_name=journalist.full_name if journalist else "Unknown",
            journalist_organization=org.name if org else "",
            session_notes=session_notes,
            session_duration=session_duration,
            charter_content=charter.content if charter else "",
            previous_decisions=[],
            current_tasks=[{"title": t.title, "id": str(t.id)} for t in current_tasks],
            workflow_run_id=str(workflow_run.id),
        )

        # Save the session notes as an artifact
        notes_artifact = MentorArtifact(
            engagement_id=engagement_id,
            artifact_type="notes",
            title=f"Session {session_number} Notes",
            version=1,
            is_current=True,
            content=session_notes,
            content_format="text",
            created_by_workflow="post_call",
            workflow_run_id=workflow_run.id,
        )
        db.add(notes_artifact)

        # Save the Prototype Pack artifact
        pack_content = result.get("prototype_pack_content", "")
        if pack_content:
            # Mark previous packs as not current
            db.query(MentorArtifact).filter(
                MentorArtifact.engagement_id == engagement_id,
                MentorArtifact.artifact_type == "prototype_pack",
                MentorArtifact.is_current == True,
            ).update({"is_current": False})

            pack_artifact = MentorArtifact(
                engagement_id=engagement_id,
                artifact_type="prototype_pack",
                title=f"Prototype Pack (Session {session_number})",
                version=session_number,
                is_current=True,
                content=pack_content,
                content_format="markdown",
                structured_data=result.get("prototype_pack_structured", {}),
                source_notes=session_notes,
                created_by_workflow="post_call",
                workflow_run_id=workflow_run.id,
            )
            db.add(pack_artifact)

        # Save decision log update
        decision_log = result.get("decision_log_update", "")
        if decision_log:
            # Append to existing decision log or create new
            existing_log = (
                db.query(MentorArtifact)
                .filter(
                    MentorArtifact.engagement_id == engagement_id,
                    MentorArtifact.artifact_type == "decision_log",
                    MentorArtifact.is_current == True,
                )
                .first()
            )

            if existing_log:
                existing_log.content = existing_log.content + "\n\n" + decision_log
            else:
                log_artifact = MentorArtifact(
                    engagement_id=engagement_id,
                    artifact_type="decision_log",
                    title="Decision Log",
                    version=1,
                    is_current=True,
                    content=decision_log,
                    content_format="markdown",
                    created_by_workflow="post_call",
                    workflow_run_id=workflow_run.id,
                )
                db.add(log_artifact)

        # Update completed tasks
        completed_titles = result.get("completed_task_ids", [])
        for task in current_tasks:
            if task.title in completed_titles:
                task.status = "completed"
                task.completed_at = datetime.now(timezone)

        # Add new tasks
        next_tasks = result.get("next_tasks", [])
        for i, task_data in enumerate(next_tasks):
            task = MentorTask(
                engagement_id=engagement_id,
                title=task_data.get("title", "Untitled Task"),
                description=task_data.get("description", ""),
                task_type=task_data.get("task_type", "action"),
                priority=task_data.get("priority", 2),
                assigned_to=task_data.get("assigned_to", "journalist"),
                created_by_workflow="post_call",
                workflow_run_id=workflow_run.id,
                sort_order=len(current_tasks) + i,
            )
            db.add(task)

        # Create mentor session record
        session = MentorSession(
            engagement_id=engagement_id,
            session_number=session_number,
            session_type="regular" if session_number > 0 else "intake",
            actual_date=datetime.now(timezone),
            duration_minutes=session_duration,
            status="completed",
            notes=session_notes,
            key_decisions=result.get("new_decisions", []),
            action_items=[t.get("title") for t in next_tasks],
            workflow_run_id=workflow_run.id,
        )
        db.add(session)

        runtime.update_status(
            workflow_run,
            "completed",
            outputs=result,
        )

        db.commit()

        return {
            "status": "completed",
            "pack_created": bool(pack_content),
            "tasks_created": len(next_tasks),
            "decisions_logged": len(result.get("new_decisions", [])),
            "workflow_run_id": str(workflow_run.id),
        }

    except Exception as e:
        import traceback
        runtime.update_status(
            workflow_run,
            "failed",
            error_message=str(e),
        )
        workflow_run.error_traceback = traceback.format_exc()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engagements/{engagement_id}/mentor", response_class=HTMLResponse)
async def engagement_mentor_dashboard(
    engagement_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show mentor workflow dashboard for an engagement."""
    from app.models.mentor import MentorArtifact, MentorTask, MentorSession
    from app.models.workflow import WorkflowRun

    engagement = (
        db.query(Engagement)
        .options(
            joinedload(Engagement.journalist).joinedload(Journalist.organization),
            joinedload(Engagement.documents),
        )
        .filter(Engagement.id == engagement_id)
        .first()
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Get artifacts
    artifacts = (
        db.query(MentorArtifact)
        .filter(MentorArtifact.engagement_id == engagement_id)
        .order_by(desc(MentorArtifact.created_at))
        .all()
    )

    # Get tasks
    tasks = (
        db.query(MentorTask)
        .filter(MentorTask.engagement_id == engagement_id)
        .order_by(MentorTask.priority, MentorTask.sort_order)
        .all()
    )

    # Get sessions
    sessions = (
        db.query(MentorSession)
        .filter(MentorSession.engagement_id == engagement_id)
        .order_by(MentorSession.session_number)
        .all()
    )

    # Get workflow runs
    workflow_runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_name.in_(["mentor_intake", "mentor_pre_call", "mentor_post_call"]))
        .filter(WorkflowRun.inputs["engagement_id"].astext == engagement_id)
        .order_by(desc(WorkflowRun.created_at))
        .limit(20)
        .all()
    )

    # Group artifacts by type
    artifacts_by_type = {}
    for a in artifacts:
        if a.artifact_type not in artifacts_by_type:
            artifacts_by_type[a.artifact_type] = []
        artifacts_by_type[a.artifact_type].append(a)

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/engagement_mentor.html",
        {
            "request": request,
            "user": user,
            "engagement": engagement,
            "artifacts": artifacts,
            "artifacts_by_type": artifacts_by_type,
            "tasks": tasks,
            "sessions": sessions,
            "workflow_runs": workflow_runs,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/mentor/tasks/{task_id}/status")
async def update_mentor_task_status(
    task_id: str,
    status: str = Form(...),
    completion_notes: str = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a mentor task's status."""
    from app.models.mentor import MentorTask

    task = db.query(MentorTask).filter(MentorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = status
    if status == "completed":
        task.completed_at = datetime.now(timezone)
        task.completion_notes = completion_notes

    db.commit()

    return {"status": "updated", "task_status": status}


@router.get("/mentor/runs", response_class=HTMLResponse)
async def mentor_workflow_runs(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show audit view of all mentor workflow runs."""
    from app.models.workflow import WorkflowRun

    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_name.in_(["mentor_intake", "mentor_pre_call", "mentor_post_call"]))
        .order_by(desc(WorkflowRun.created_at))
        .limit(100)
        .all()
    )

    # Get engagement details for each run
    engagement_ids = [
        run.inputs.get("engagement_id")
        for run in runs
        if run.inputs and run.inputs.get("engagement_id")
    ]
    engagements = {}
    if engagement_ids:
        engs = (
            db.query(Engagement)
            .options(joinedload(Engagement.journalist))
            .filter(Engagement.id.in_(engagement_ids))
            .all()
        )
        engagements = {str(e.id): e for e in engs}

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/mentor_runs.html",
        {
            "request": request,
            "user": user,
            "runs": runs,
            "engagements": engagements,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


# =============================================================================
# SPREADSHEET IMPORT
# =============================================================================

@router.get("/import", response_class=HTMLResponse)
async def import_upload_page(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show the spreadsheet upload page."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.models.organization_profile import OrganizationProfile

    clients = db.query(OrganizationProfile).order_by(OrganizationProfile.name).all()
    recent_imports = (
        db.query(SpreadsheetImport)
        .order_by(desc(SpreadsheetImport.created_at))
        .limit(10)
        .all()
    )

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/import_upload.html",
        {
            "request": request,
            "user": user,
            "clients": clients,
            "recent_imports": recent_imports,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/import/upload")
async def import_upload_file(
    request: Request,
    file: UploadFile = File(...),
    client_id: Optional[str] = Form(None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Process uploaded spreadsheet file."""
    import os
    import uuid as uuid_mod
    import traceback
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import parse_spreadsheet, ai_map_columns, get_import_knowledge

    try:
        # Validate file type
        filename = file.filename or "upload"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ("csv", "xlsx", "xls"):
            raise HTTPException(status_code=400, detail="Only CSV, XLSX, and XLS files are supported")

        # Save uploaded file
        upload_dir = os.path.join("uploads", "imports")
        os.makedirs(upload_dir, exist_ok=True)
        file_id = str(uuid_mod.uuid4())[:8]
        saved_path = os.path.join(upload_dir, f"{file_id}_{filename}")

        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        # Parse spreadsheet
        parsed = parse_spreadsheet(saved_path, ext)

        # Load knowledge from past imports
        knowledge = get_import_knowledge(db)

        # AI map columns (with knowledge from past imports)
        mapping_result = ai_map_columns(parsed["headers"], parsed["sample_rows"], knowledge=knowledge)

        # Handle empty client_id string from form
        resolved_client_id = None
        if client_id and client_id.strip():
            resolved_client_id = uuid_mod.UUID(client_id.strip())

        # Create import session
        import_session = SpreadsheetImport(
            filename=filename,
            file_path=saved_path,
            file_type=ext,
            row_count=parsed["row_count"],
            raw_headers=parsed["headers"],
            sample_rows=parsed["sample_rows"],
            column_mapping=mapping_result["mapping"],
            status="mapped",
            uploaded_by_id=user.id,
            client_id=resolved_client_id,
            chat_history=[],
            field_defaults={},
        )
        db.add(import_session)
        db.commit()
        db.refresh(import_session)

        return RedirectResponse(
            url=f"/admin/directory/import/{import_session.id}/map",
            status_code=303,
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Import upload error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/import/{import_id}/map", response_class=HTMLResponse)
async def import_mapping_page(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show the column mapping review page."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import TARGET_FIELDS

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        raise HTTPException(status_code=404, detail="Import session not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/import_mapping.html",
        {
            "request": request,
            "user": user,
            "import_session": import_session,
            "target_fields": TARGET_FIELDS,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/import/{import_id}/map")
async def import_save_mapping(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save adjusted column mapping."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import TARGET_FIELDS
    from sqlalchemy.orm.attributes import flag_modified

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        raise HTTPException(status_code=404, detail="Import session not found")

    form = await request.form()

    # Build mapping from form data
    new_mapping = {}
    for header in import_session.raw_headers:
        target = form.get(f"mapping_{header}")
        if target and target != "skip":
            new_mapping[header] = target

    import_session.column_mapping = new_mapping
    flag_modified(import_session, "column_mapping")

    # Check if required fields are missing
    mapped_targets = set(new_mapping.values())
    missing_required = [
        f for f, info in TARGET_FIELDS.items()
        if info["required"] and f not in mapped_targets
    ]

    if missing_required:
        import_session.status = "chatting"
        db.commit()
        return RedirectResponse(
            url=f"/admin/directory/import/{import_id}/chat",
            status_code=303,
        )
    else:
        import_session.status = "ready"
        db.commit()
        return RedirectResponse(
            url=f"/admin/directory/import/{import_id}/preview",
            status_code=303,
        )


@router.get("/import/{import_id}/chat", response_class=HTMLResponse)
async def import_chat_page(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show the chat interface for missing data."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import generate_chat_response, get_import_knowledge, TARGET_FIELDS
    from sqlalchemy.orm.attributes import flag_modified

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        raise HTTPException(status_code=404, detail="Import session not found")

    # Auto-generate first AI question if chat history is empty
    if not import_session.chat_history:
        knowledge = get_import_knowledge(db)
        # Simple kickoff — the system prompt already has all the context
        intro = "Hi, I've uploaded my spreadsheet and mapped the columns. What else do you need from me?"

        result = generate_chat_response(import_session, intro, knowledge=knowledge)
        import_session.chat_history = result["chat_history"]
        import_session.field_defaults = result["field_defaults"]
        flag_modified(import_session, "chat_history")
        flag_modified(import_session, "field_defaults")
        if result["is_complete"]:
            import_session.status = "ready"
        db.commit()
        db.refresh(import_session)

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/import_chat.html",
        {
            "request": request,
            "user": user,
            "import_session": import_session,
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/import/{import_id}/chat")
async def import_chat_message(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Handle AJAX chat message for missing data."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import generate_chat_response, get_import_knowledge
    from sqlalchemy.orm.attributes import flag_modified

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        return JSONResponse({"error": "Import session not found"}, status_code=404)

    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    knowledge = get_import_knowledge(db)
    result = generate_chat_response(import_session, message, knowledge=knowledge)

    import_session.chat_history = result["chat_history"]
    import_session.field_defaults = result["field_defaults"]
    flag_modified(import_session, "chat_history")
    flag_modified(import_session, "field_defaults")

    response_text = result["response"]

    # Check if AI wants to trigger per-row classification
    if "[CLASSIFY_ROWS]" in response_text:
        from app.services.spreadsheet_ingest import ai_classify_rows
        response_text = response_text.replace("[CLASSIFY_ROWS]", "").strip()

        try:
            row_overrides = ai_classify_rows(import_session, knowledge=knowledge)
            import_session.row_overrides = row_overrides
            flag_modified(import_session, "row_overrides")

            # Count what was classified
            org_types_found = {}
            countries_found = {}
            for ov in row_overrides.values():
                ot = ov.get("org_type")
                if ot:
                    org_types_found[ot] = org_types_found.get(ot, 0) + 1
                ct = ov.get("country")
                if ct:
                    countries_found[ct] = countries_found.get(ct, 0) + 1

            # Build a summary to send back through the chat
            summary_parts = []
            if org_types_found:
                breakdown = ", ".join(f"**{count}** {t}" for t, count in sorted(org_types_found.items(), key=lambda x: -x[1]))
                summary_parts.append(f"Classified {len(row_overrides)} organizations: {breakdown}.")
            if countries_found:
                top_countries = sorted(countries_found.items(), key=lambda x: -x[1])[:5]
                breakdown = ", ".join(f"**{count}** from {c}" for c, count in top_countries)
                summary_parts.append(f"Countries identified: {breakdown}.")

            classify_msg = " ".join(summary_parts) if summary_parts else "Classification complete."

            # Generate a follow-up response with the classification results
            followup = generate_chat_response(import_session, f"[System: AI classification complete. {classify_msg}]", knowledge=knowledge)
            import_session.chat_history = followup["chat_history"]
            import_session.field_defaults = followup["field_defaults"]
            flag_modified(import_session, "chat_history")
            flag_modified(import_session, "field_defaults")
            response_text = followup["response"]
            result["is_complete"] = followup["is_complete"]
            result["field_defaults"] = followup["field_defaults"]

        except Exception as e:
            response_text += f"\n\nSorry, there was an error during classification: {str(e)}"

    if result["is_complete"]:
        import_session.status = "ready"

    db.commit()

    return JSONResponse({
        "response": response_text,
        "is_complete": result["is_complete"],
        "field_defaults": result["field_defaults"],
    })


@router.get("/import/{import_id}/preview", response_class=HTMLResponse)
async def import_preview_page(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show preview of all records before import."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import validate_and_preview

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        raise HTTPException(status_code=404, detail="Import session not found")

    preview = validate_and_preview(import_session)

    stats = {
        "total": len(preview),
        "valid": sum(1 for p in preview if p["status"] == "valid"),
        "warning": sum(1 for p in preview if p["status"] == "warning"),
        "error": sum(1 for p in preview if p["status"] == "error"),
    }

    # Build the list of all data fields that appear in the preview
    # (standard fields + any custom mapped fields)
    mapping = import_session.column_mapping or {}
    mapped_fields = sorted(set(mapping.values()) - {None})
    # Ensure standard fields come first in a logical order
    field_order = ["name", "org_type", "country", "website", "description", "notes"]
    extra_fields = [f for f in mapped_fields if f not in field_order]
    display_fields = [f for f in field_order if f in mapped_fields or any(p["data"].get(f) for p in preview)]
    display_fields.extend(extra_fields)

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/import_preview.html",
        {
            "request": request,
            "user": user,
            "import_session": import_session,
            "preview": preview,
            "stats": stats,
            "display_fields": display_fields,
            "raw_headers": import_session.raw_headers or [],
            **admin_context,
            "active_admin_page": "directory",
        }
    )


@router.post("/import/{import_id}/execute")
async def import_execute(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Execute the import."""
    from app.models.spreadsheet_import import SpreadsheetImport
    from app.services.spreadsheet_ingest import execute_import

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        return JSONResponse({"error": "Import session not found"}, status_code=404)

    # Accept row edits from the frontend
    from sqlalchemy.orm.attributes import flag_modified
    try:
        body = await request.json()
    except Exception:
        body = {}
    row_edits = body.get("row_edits", {})

    # Store edits in import session so execute_import can use them
    if row_edits:
        existing_overrides = dict(import_session.row_overrides or {})
        for row_idx_str, edits in row_edits.items():
            if row_idx_str not in existing_overrides:
                existing_overrides[row_idx_str] = {}
            existing_overrides[row_idx_str].update(edits)
        import_session.row_overrides = existing_overrides
        flag_modified(import_session, "row_overrides")

    import_session.status = "importing"
    db.commit()

    try:
        result = execute_import(db, import_session)
        return JSONResponse({
            "status": "completed",
            "created": result["created"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "errors": result["errors"],
        })
    except Exception as e:
        import_session.status = "failed"
        import_session.import_errors = [{"error": str(e)}]
        db.commit()
        return JSONResponse({"status": "failed", "error": str(e)}, status_code=500)


@router.get("/import/{import_id}/results", response_class=HTMLResponse)
async def import_results_page(
    import_id: str,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Show import results summary."""
    from app.models.spreadsheet_import import SpreadsheetImport

    import_session = db.query(SpreadsheetImport).filter(
        SpreadsheetImport.id == import_id
    ).first()
    if not import_session:
        raise HTTPException(status_code=404, detail="Import session not found")

    admin_context = get_admin_context_dict(request)
    return templates.TemplateResponse(
        "admin/directory/import_results.html",
        {
            "request": request,
            "user": user,
            "import_session": import_session,
            **admin_context,
            "active_admin_page": "directory",
        }
    )
