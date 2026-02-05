"""Node implementations for Partner Intelligence workflow."""
import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.workflows.partner_intelligence.state import (
    PartnerIntelligenceState,
    PageInfo,
    ExtractedField,
    ConflictInfo,
)


# LLM Configuration
EXTRACTION_MODEL = "gpt-4o-mini"
CONFIDENCE_THRESHOLD = 0.7  # Below this triggers needs_review


def _get_llm():
    """Get the LLM instance for extraction."""
    return ChatOpenAI(model=EXTRACTION_MODEL, temperature=0)


def _hash_url(url: str) -> str:
    """Create a SHA256 hash of a URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def _clean_url(url: str) -> str:
    """Normalize a URL for consistency."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    # Remove trailing slash
    return url.rstrip('/')


# =============================================================================
# NODE 1: Identify Key Pages
# =============================================================================

async def identify_pages(state: PartnerIntelligenceState) -> dict:
    """Identify canonical website and key pages to fetch.

    This node:
    1. Validates the website URL
    2. Identifies the canonical domain
    3. Discovers key pages (about, team, contact, programs, news)
    """
    website_url = _clean_url(state.get("website_url", ""))

    if not website_url:
        return {
            "errors": ["No website URL provided"],
            "discovered_pages": [],
        }

    # Parse the base URL
    parsed = urlparse(website_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Define key pages to look for
    key_page_patterns = [
        ("homepage", "/", 1),
        ("about", "/about", 2),
        ("about", "/about-us", 2),
        ("about", "/who-we-are", 2),
        ("team", "/team", 3),
        ("team", "/our-team", 3),
        ("team", "/people", 3),
        ("team", "/staff", 3),
        ("contact", "/contact", 4),
        ("contact", "/contact-us", 4),
        ("programs", "/programs", 5),
        ("programs", "/what-we-do", 5),
        ("programs", "/services", 5),
        ("programs", "/projects", 5),
        ("news", "/news", 6),
        ("news", "/blog", 6),
        ("news", "/press", 6),
    ]

    discovered_pages: list[PageInfo] = []

    # Always include the homepage
    discovered_pages.append({
        "url": website_url,
        "page_type": "homepage",
        "priority": 1,
        "fetched": False,
    })

    # Add potential key pages
    seen_urls = {website_url}
    for page_type, path, priority in key_page_patterns:
        full_url = urljoin(base_url, path)
        if full_url not in seen_urls:
            discovered_pages.append({
                "url": full_url,
                "page_type": page_type,
                "priority": priority,
                "fetched": False,
            })
            seen_urls.add(full_url)

    # Sort by priority
    discovered_pages.sort(key=lambda p: p.get("priority", 99))

    return {
        "discovered_pages": discovered_pages,
        "canonical_url": base_url,
        "errors": [],
    }


# =============================================================================
# NODE 2: Fetch Pages
# =============================================================================

async def fetch_pages(state: PartnerIntelligenceState, db_session=None) -> dict:
    """Fetch pages and store snapshots.

    This node:
    1. Fetches each discovered page
    2. Stores HTML/text content as WebPageSnapshot
    3. Filters out pages that return errors
    """
    from app.models.evidence import WebPageSnapshot

    discovered_pages = state.get("discovered_pages", [])
    organization_id = state.get("organization_id")

    snapshot_ids = []
    fetch_errors = []
    updated_pages = []

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Grounded-PartnerIntelligence/1.0"}
    ) as client:
        # Fetch up to 10 pages to avoid overwhelming the target
        for page_info in discovered_pages[:10]:
            url = page_info.get("url")
            if not url:
                continue

            try:
                response = await client.get(url)
                page_info["status_code"] = response.status_code

                if response.status_code == 200:
                    page_info["fetched"] = True
                    html_content = response.text

                    # Extract text (simple approach - strip HTML tags)
                    text_content = _extract_text_from_html(html_content)
                    title = _extract_title_from_html(html_content)

                    # Store content in page_info for extraction
                    page_info["text_content"] = text_content
                    page_info["title"] = title

                    # Store snapshot if we have a database session
                    if db_session:
                        snapshot = WebPageSnapshot(
                            url=url,
                            url_hash=_hash_url(url),
                            page_type=page_info.get("page_type"),
                            html_content=html_content[:500000],  # Limit size
                            text_content=text_content[:100000],
                            title=title,
                            status_code=str(response.status_code),
                            content_type=response.headers.get("content-type"),
                            organization_id=organization_id,
                        )
                        db_session.add(snapshot)
                        db_session.flush()
                        snapshot_ids.append(str(snapshot.id))
                else:
                    page_info["error"] = f"HTTP {response.status_code}"
                    fetch_errors.append(f"{url}: HTTP {response.status_code}")

            except httpx.TimeoutException:
                page_info["error"] = "Timeout"
                fetch_errors.append(f"{url}: Timeout")
            except httpx.RequestError as e:
                page_info["error"] = str(e)
                fetch_errors.append(f"{url}: {str(e)}")

            updated_pages.append(page_info)

    if db_session:
        db_session.commit()

    return {
        "discovered_pages": updated_pages,
        "snapshot_ids": snapshot_ids,
        "fetch_errors": fetch_errors,
    }


def _extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML, removing scripts and styles."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_title_from_html(html: str) -> str:
    """Extract the title from HTML."""
    match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    return match.group(1).strip() if match else ""


# =============================================================================
# NODE 3: Extract Structured Fields
# =============================================================================

async def extract_fields(state: PartnerIntelligenceState) -> dict:
    """Extract structured fields from fetched pages using LLM.

    This node:
    1. Combines text from all fetched pages
    2. Uses LLM to extract structured fields
    3. Assigns confidence scores to each extraction
    """
    discovered_pages = state.get("discovered_pages", [])
    organization_name = state.get("organization_name", "the organization")

    # Gather text from fetched pages
    page_texts = []
    for page in discovered_pages:
        if page.get("fetched") and page.get("text_content"):
            page_texts.append(f"=== {page.get('page_type', 'page').upper()} PAGE ({page.get('url', '')}) ===\n{page.get('text_content', '')[:5000]}")

    if not page_texts:
        return {
            "extracted_fields": [],
            "extraction_errors": ["No pages were successfully fetched"],
            "enrichment": {},
        }

    combined_text = "\n\n".join(page_texts)[:20000]  # Limit total size

    # Create extraction prompt
    system_prompt = """You are an expert at extracting structured information about media organizations from their websites.
Extract the following fields if present. For each field, provide a confidence score from 0.0 to 1.0.

Fields to extract:
- description: A concise description of what the organization does (2-3 sentences)
- focus_areas: List of topic areas or beats they cover (e.g., investigative journalism, data journalism, etc.)
- countries_served: List of countries or regions they operate in or cover
- key_people: List of key staff with their roles (editors, directors, etc.) - max 10 people
- programs: List of programs, projects, or initiatives they run

Respond in JSON format:
{
    "description": {"value": "...", "confidence": 0.9},
    "focus_areas": {"value": ["area1", "area2"], "confidence": 0.8},
    "countries_served": {"value": ["Country1", "Country2"], "confidence": 0.7},
    "key_people": {"value": [{"name": "...", "role": "..."}], "confidence": 0.8},
    "programs": {"value": ["program1", "program2"], "confidence": 0.6}
}

If a field cannot be determined from the content, set confidence to 0.0 and value to null.
Be conservative with confidence scores - only use 0.9+ if the information is explicitly stated."""

    user_prompt = f"""Extract structured information about "{organization_name}" from these website pages:

{combined_text}

Respond with JSON only."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        # Parse the response
        response_text = response.content
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        import json
        extracted_data = json.loads(response_text.strip())

        # Convert to ExtractedField format
        extracted_fields: list[ExtractedField] = []
        enrichment = {}

        for field_name, field_data in extracted_data.items():
            if isinstance(field_data, dict) and "value" in field_data:
                confidence = field_data.get("confidence", 0.5)
                value = field_data.get("value")

                if value is not None:
                    extracted_fields.append({
                        "field_name": field_name,
                        "value": value,
                        "confidence": confidence,
                        "source_url": state.get("website_url", ""),
                        "extraction_method": "llm",
                        "needs_review": confidence < CONFIDENCE_THRESHOLD,
                        "review_reason": f"Low confidence ({confidence:.2f})" if confidence < CONFIDENCE_THRESHOLD else None,
                    })
                    enrichment[field_name] = value

        return {
            "extracted_fields": extracted_fields,
            "enrichment": enrichment,
            "extraction_errors": [],
        }

    except Exception as e:
        return {
            "extracted_fields": [],
            "extraction_errors": [f"LLM extraction failed: {str(e)}"],
            "enrichment": {},
        }


# =============================================================================
# NODE 4: Detect Conflicts
# =============================================================================

async def detect_conflicts(state: PartnerIntelligenceState) -> dict:
    """Detect conflicts between extracted data and existing data.

    This node:
    1. Compares extracted description with current description
    2. Identifies significant changes
    3. Routes to needs_review if conflicts detected
    """
    extracted_fields = state.get("extracted_fields", [])
    current_description = state.get("current_description")
    enrichment = state.get("enrichment", {})

    conflicts: list[ConflictInfo] = []
    low_confidence_fields = []

    # Check for low confidence extractions
    for field in extracted_fields:
        if field.get("needs_review"):
            low_confidence_fields.append(field.get("field_name", ""))

    # Check description conflict
    new_description = enrichment.get("description")
    if new_description and current_description:
        # If there's existing description, flag as potential conflict
        if len(current_description.strip()) > 50:  # Non-trivial existing description
            conflicts.append({
                "field_name": "description",
                "current_value": current_description[:200],
                "new_value": new_description[:200],
                "confidence": next(
                    (f.get("confidence", 0.5) for f in extracted_fields if f.get("field_name") == "description"),
                    0.5
                ),
                "resolution": None,
            })

    # Determine if review is needed
    needs_review = len(conflicts) > 0 or len(low_confidence_fields) > 0

    review_reasons = []
    if conflicts:
        review_reasons.append(f"{len(conflicts)} potential conflict(s) with existing data")
    if low_confidence_fields:
        review_reasons.append(f"Low confidence on: {', '.join(low_confidence_fields)}")

    return {
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
        "needs_review": needs_review,
        "review_reason": "; ".join(review_reasons) if review_reasons else None,
        "low_confidence_fields": low_confidence_fields,
    }


# =============================================================================
# NODE 5: Upsert Enrichment
# =============================================================================

async def upsert_enrichment(state: PartnerIntelligenceState, db_session=None) -> dict:
    """Upsert enrichment data into MediaOrganization.

    This node:
    1. Updates organization description if confidence is high enough
    2. Stores structured data in notes or extended fields
    3. Only runs if not needs_review (or after review approval)
    """
    from app.models.directory import MediaOrganization

    organization_id = state.get("organization_id")
    enrichment = state.get("enrichment", {})
    extracted_fields = state.get("extracted_fields", [])
    needs_review = state.get("needs_review", False)

    if needs_review:
        # Don't apply changes if review is needed
        return {
            "enrichment_applied": False,
            "summary": "Enrichment pending review",
        }

    if not db_session or not organization_id:
        return {
            "enrichment_applied": False,
            "summary": "No database session or organization ID",
            "errors": ["Cannot apply enrichment without database access"],
        }

    try:
        org = db_session.query(MediaOrganization).filter(
            MediaOrganization.id == organization_id
        ).first()

        if not org:
            return {
                "enrichment_applied": False,
                "summary": "Organization not found",
                "errors": [f"Organization {organization_id} not found"],
            }

        changes = []

        # Update description if we have a high-confidence one and current is empty/short
        new_description = enrichment.get("description")
        description_confidence = next(
            (f.get("confidence", 0) for f in extracted_fields if f.get("field_name") == "description"),
            0
        )

        if new_description and description_confidence >= CONFIDENCE_THRESHOLD:
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

        # Append to notes if we have enrichment data
        if enrichment_notes:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            enrichment_section = f"\n\n--- Auto-enriched {timestamp} ---\n" + "\n".join(enrichment_notes)

            if org.notes:
                # Avoid duplicate enrichment
                if "Auto-enriched" not in org.notes:
                    org.notes = org.notes + enrichment_section
            else:
                org.notes = enrichment_section.strip()

            changes.append("notes")

        db_session.commit()

        return {
            "enrichment_applied": True,
            "summary": f"Updated: {', '.join(changes)}" if changes else "No changes applied",
        }

    except Exception as e:
        return {
            "enrichment_applied": False,
            "summary": f"Error applying enrichment: {str(e)}",
            "errors": [str(e)],
        }


# =============================================================================
# NODE 6: Save Evidence
# =============================================================================

async def save_evidence(state: PartnerIntelligenceState, db_session=None) -> dict:
    """Save evidence sources for extracted fields.

    This node:
    1. Creates EvidenceSource records for each extracted field
    2. Links them to the organization
    3. Stores extraction metadata
    """
    from app.models.evidence import EvidenceSource

    organization_id = state.get("organization_id")
    extracted_fields = state.get("extracted_fields", [])
    workflow_run_id = state.get("workflow_run_id")

    if not db_session or not organization_id:
        return {
            "evidence_source_ids": [],
            "errors": ["Cannot save evidence without database access"],
        }

    evidence_ids = []

    try:
        for field in extracted_fields:
            evidence = EvidenceSource(
                organization_id=organization_id,
                source_url=field.get("source_url", state.get("website_url", "")),
                source_type="webpage",
                field_name=field.get("field_name", ""),
                extracted_value=str(field.get("value", "")),
                confidence_score=field.get("confidence"),
                extraction_method=field.get("extraction_method", "llm"),
                extraction_model=EXTRACTION_MODEL,
                workflow_run_id=workflow_run_id,
            )
            db_session.add(evidence)
            db_session.flush()
            evidence_ids.append(str(evidence.id))

        db_session.commit()

        return {
            "evidence_source_ids": evidence_ids,
        }

    except Exception as e:
        return {
            "evidence_source_ids": [],
            "errors": [f"Error saving evidence: {str(e)}"],
        }


# =============================================================================
# FINAL NODE: Compile Output
# =============================================================================

async def compile_output(state: PartnerIntelligenceState) -> dict:
    """Compile final workflow output."""
    needs_review = state.get("needs_review", False)
    enrichment_applied = state.get("enrichment_applied", False)
    extracted_fields = state.get("extracted_fields", [])
    errors = state.get("errors", []) + state.get("extraction_errors", []) + state.get("fetch_errors", [])

    if needs_review:
        summary = f"Enrichment requires review: {state.get('review_reason', 'Unknown reason')}"
    elif enrichment_applied:
        summary = f"Successfully enriched organization with {len(extracted_fields)} fields"
    else:
        summary = "Enrichment completed but no changes applied"

    # Prepare state for needs_review passthrough
    __state__ = {
        "needs_review": needs_review,
        "review_reason": state.get("review_reason"),
    }

    return {
        "summary": summary,
        "errors": list(set(errors)),  # Dedupe
        "__state__": __state__,
    }
