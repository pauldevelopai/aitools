"""Workflow nodes for Governance & Tools Intelligence."""
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Any
import httpx
from openai import AsyncOpenAI

from app.workflows.governance.state import (
    GovernanceTargetState,
    EvidenceSource,
    ExtractedFramework,
    ExtractedControl,
    TestResult,
    GeneratedContent,
)


# =============================================================================
# UTILITIES
# =============================================================================

def get_openai_client() -> AsyncOpenAI:
    """Get OpenAI client."""
    import os
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def fetch_url_content(url: str, timeout: int = 30) -> tuple[str, str]:
    """Fetch URL content. Returns (content, error)."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GroundedBot/1.0; +https://grounded.ai)"
            })
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or "text/plain" in content_type:
                return response.text[:50000], ""  # Limit content size
            else:
                return "", f"Unsupported content type: {content_type}"
    except httpx.TimeoutException:
        return "", "Request timed out"
    except httpx.HTTPStatusError as e:
        return "", f"HTTP {e.response.status_code}"
    except Exception as e:
        return "", str(e)


def clean_html_to_text(html: str) -> str:
    """Simple HTML to text conversion."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def generate_slug(name: str) -> str:
    """Generate URL-safe slug from name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:100]


# =============================================================================
# RESEARCH NODES
# =============================================================================

async def discover_urls(state: GovernanceTargetState) -> dict[str, Any]:
    """Discover relevant URLs for the target using search terms."""
    errors = list(state.get("errors", []))
    discovered_urls = list(state.get("known_urls", []))

    # For now, we primarily use known_urls
    # Future: integrate with web search APIs

    search_terms = state.get("search_terms", [])
    target_name = state.get("target_name", "")

    # If we have search terms but no known URLs, try to construct likely URLs
    if search_terms and not discovered_urls:
        # Try common official sources
        if state.get("target_type") == "framework":
            jurisdiction = state.get("jurisdiction", "").lower()
            if "eu" in jurisdiction or "european" in jurisdiction:
                discovered_urls.append("https://eur-lex.europa.eu/")
            if "us" in jurisdiction or "united states" in jurisdiction:
                discovered_urls.append("https://www.congress.gov/")

    return {
        "discovered_urls": discovered_urls,
        "current_step": "discover_urls_complete",
    }


async def fetch_pages(state: GovernanceTargetState) -> dict[str, Any]:
    """Fetch content from discovered URLs."""
    errors = list(state.get("errors", []))
    fetched_pages: list[EvidenceSource] = []

    urls_to_fetch = state.get("discovered_urls", []) + state.get("known_urls", [])
    urls_to_fetch = list(set(urls_to_fetch))  # Dedupe

    for url in urls_to_fetch[:10]:  # Limit to 10 pages
        content, error = await fetch_url_content(url)

        if error:
            fetched_pages.append({
                "url": url,
                "title": "",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "excerpt": "",
                "content_hash": "",
                "fetch_status": "failed",
            })
            errors.append(f"Failed to fetch {url}: {error}")
        else:
            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else url

            # Clean content
            text_content = clean_html_to_text(content)
            excerpt = text_content[:1000] + "..." if len(text_content) > 1000 else text_content

            fetched_pages.append({
                "url": url,
                "title": title,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "excerpt": excerpt,
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                "fetch_status": "success",
            })

    return {
        "fetched_pages": fetched_pages,
        "errors": errors,
        "current_step": "fetch_pages_complete",
    }


# =============================================================================
# FRAMEWORK EXTRACTION NODES
# =============================================================================

async def extract_framework_info(state: GovernanceTargetState) -> dict[str, Any]:
    """Extract framework information from fetched pages using LLM."""
    errors = list(state.get("errors", []))

    target_name = state.get("target_name", "")
    target_description = state.get("target_description", "")
    jurisdiction = state.get("jurisdiction", "")
    fetched_pages = state.get("fetched_pages", [])

    # Combine successful page content
    combined_content = ""
    for page in fetched_pages:
        if page.get("fetch_status") == "success":
            combined_content += f"\n\n--- Source: {page.get('url')} ---\n{page.get('excerpt', '')}"

    if not combined_content:
        errors.append("No content available for extraction")
        return {
            "errors": errors,
            "extracted_framework": {},
            "current_step": "extract_framework_complete",
        }

    # Use LLM to extract framework information
    try:
        client = get_openai_client()

        prompt = f"""Analyze the following content about "{target_name}" and extract structured information about this governance framework/regulation.

Target Description: {target_description}
Jurisdiction: {jurisdiction}

Content to analyze:
{combined_content[:15000]}

Extract and return a JSON object with these fields:
- name: Full official name of the framework
- short_name: Common abbreviation (e.g., "GDPR", "EU AI Act")
- framework_type: One of: regulation, directive, guidance, standard, policy, treaty
- jurisdiction: Geographic jurisdiction (e.g., "EU", "US", "UK", "Global")
- jurisdiction_scope: One of: federal, state, regional, international
- description: 2-3 paragraph description of what this framework covers
- summary: 1-2 sentence summary
- key_provisions: List of 5-10 main provisions or requirements
- effective_date: Date when it came into effect (YYYY-MM-DD format if known)
- official_url: Official source URL if found
- applies_to: List of what it applies to (e.g., ["ai_systems", "data_processing", "automated_decisions"])

Return ONLY valid JSON, no additional text."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        result_text = response.choices[0].message.content.strip()

        # Try to parse JSON
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)

        framework_data = json.loads(result_text)

        extracted_framework: ExtractedFramework = {
            "name": framework_data.get("name", target_name),
            "short_name": framework_data.get("short_name", ""),
            "framework_type": framework_data.get("framework_type", "regulation"),
            "jurisdiction": framework_data.get("jurisdiction", jurisdiction),
            "jurisdiction_scope": framework_data.get("jurisdiction_scope", ""),
            "description": framework_data.get("description", ""),
            "summary": framework_data.get("summary", ""),
            "key_provisions": framework_data.get("key_provisions", []),
            "effective_date": framework_data.get("effective_date", ""),
            "official_url": framework_data.get("official_url", ""),
            "applies_to": framework_data.get("applies_to", []),
        }

    except json.JSONDecodeError as e:
        errors.append(f"Failed to parse LLM response: {e}")
        extracted_framework = {"name": target_name, "jurisdiction": jurisdiction}
    except Exception as e:
        errors.append(f"Framework extraction failed: {e}")
        extracted_framework = {"name": target_name, "jurisdiction": jurisdiction}

    return {
        "extracted_framework": extracted_framework,
        "errors": errors,
        "current_step": "extract_framework_complete",
    }


async def extract_controls(state: GovernanceTargetState) -> dict[str, Any]:
    """Extract specific controls/obligations from the framework."""
    errors = list(state.get("errors", []))

    target_name = state.get("target_name", "")
    fetched_pages = state.get("fetched_pages", [])
    extracted_framework = state.get("extracted_framework", {})

    # Combine content
    combined_content = ""
    for page in fetched_pages:
        if page.get("fetch_status") == "success":
            combined_content += f"\n\n{page.get('excerpt', '')}"

    if not combined_content:
        return {
            "extracted_controls": [],
            "errors": errors,
            "current_step": "extract_controls_complete",
        }

    try:
        client = get_openai_client()

        prompt = f"""Analyze the following content about "{target_name}" and extract specific controls, obligations, or requirements.

Framework Summary: {extracted_framework.get('summary', '')}

Content:
{combined_content[:12000]}

Extract up to 10 key controls/requirements. For each, return a JSON array with objects containing:
- control_id: Article/Section number if available (e.g., "Article 5", "Section 2.3")
- name: Short name for this control
- description: What this control requires
- obligations: List of specific obligations
- control_type: One of: transparency, accountability, security, rights, fairness, documentation, assessment
- risk_level: One of: high, medium, low
- applies_to_tools: true if this applies to AI tools
- applies_to_data: true if this applies to data processing
- applies_to_content: true if this applies to content/media

Return ONLY a valid JSON array, no additional text."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000,
        )

        result_text = response.choices[0].message.content.strip()

        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)

        controls_data = json.loads(result_text)

        extracted_controls: list[ExtractedControl] = []
        for ctrl in controls_data[:10]:
            extracted_controls.append({
                "control_id": ctrl.get("control_id", ""),
                "name": ctrl.get("name", ""),
                "description": ctrl.get("description", ""),
                "obligations": ctrl.get("obligations", []),
                "control_type": ctrl.get("control_type", ""),
                "risk_level": ctrl.get("risk_level", "medium"),
                "applies_to_tools": ctrl.get("applies_to_tools", False),
                "applies_to_data": ctrl.get("applies_to_data", False),
                "applies_to_content": ctrl.get("applies_to_content", False),
            })

    except Exception as e:
        errors.append(f"Control extraction failed: {e}")
        extracted_controls = []

    return {
        "extracted_controls": extracted_controls,
        "errors": errors,
        "current_step": "extract_controls_complete",
    }


# =============================================================================
# TOOL TESTING NODES
# =============================================================================

async def load_test_cases(state: GovernanceTargetState) -> dict[str, Any]:
    """Load test cases for the tool."""
    errors = list(state.get("errors", []))

    tool_id = state.get("tool_id", "")
    tool_name = state.get("tool_name", state.get("target_name", ""))

    # Default test cases for any tool
    default_test_cases = [
        {
            "name": "Website Availability",
            "test_type": "availability",
            "description": "Check if the tool's website is accessible",
            "severity": "critical",
        },
        {
            "name": "Documentation Check",
            "test_type": "functionality",
            "description": "Verify documentation is available and accessible",
            "severity": "high",
        },
        {
            "name": "Privacy Policy Check",
            "test_type": "privacy",
            "description": "Check for presence of privacy policy",
            "severity": "high",
        },
        {
            "name": "Terms of Service Check",
            "test_type": "privacy",
            "description": "Check for presence of terms of service",
            "severity": "medium",
        },
        {
            "name": "HTTPS Security",
            "test_type": "security",
            "description": "Verify the site uses HTTPS",
            "severity": "critical",
        },
    ]

    # TODO: Load custom test cases from database for specific tool

    return {
        "test_cases": default_test_cases,
        "current_step": "load_test_cases_complete",
    }


async def run_tool_tests(state: GovernanceTargetState) -> dict[str, Any]:
    """Execute test cases against the tool."""
    errors = list(state.get("errors", []))
    test_results: list[TestResult] = []

    tool_url = state.get("tool_url", "")
    test_cases = state.get("test_cases", [])

    if not tool_url:
        errors.append("No tool URL provided for testing")
        return {
            "test_results": [],
            "errors": errors,
            "current_step": "run_tests_complete",
        }

    for test_case in test_cases:
        test_name = test_case.get("name", "Unknown Test")
        test_type = test_case.get("test_type", "functionality")
        start_time = datetime.now(timezone.utc)

        result: TestResult = {
            "test_name": test_name,
            "passed": False,
            "score": 0.0,
            "duration_ms": 0,
            "metrics": {},
            "output": "",
            "error_message": "",
            "red_flags": [],
        }

        try:
            if test_type == "availability":
                # Check website availability
                content, error = await fetch_url_content(tool_url, timeout=10)
                if error:
                    result["passed"] = False
                    result["error_message"] = error
                    result["red_flags"].append("Website not accessible")
                else:
                    result["passed"] = True
                    result["score"] = 1.0
                    result["output"] = f"Website responded successfully ({len(content)} bytes)"

            elif test_type == "security":
                # Check HTTPS
                if tool_url.startswith("https://"):
                    result["passed"] = True
                    result["score"] = 1.0
                    result["output"] = "Site uses HTTPS"
                else:
                    result["passed"] = False
                    result["score"] = 0.0
                    result["red_flags"].append("Site does not use HTTPS")
                    result["output"] = "Site does not use HTTPS"

            elif test_type == "privacy":
                # Check for privacy policy
                content, error = await fetch_url_content(tool_url)
                if not error:
                    content_lower = content.lower()
                    has_privacy = "privacy" in content_lower and ("policy" in content_lower or "notice" in content_lower)
                    has_terms = "terms" in content_lower and ("service" in content_lower or "use" in content_lower)

                    if "privacy" in test_name.lower():
                        result["passed"] = has_privacy
                        result["score"] = 1.0 if has_privacy else 0.0
                        result["output"] = "Privacy policy found" if has_privacy else "No privacy policy link found"
                        if not has_privacy:
                            result["red_flags"].append("No privacy policy visible")
                    else:
                        result["passed"] = has_terms
                        result["score"] = 1.0 if has_terms else 0.0
                        result["output"] = "Terms of service found" if has_terms else "No terms of service link found"
                else:
                    result["error_message"] = error

            elif test_type == "functionality":
                # Check documentation
                content, error = await fetch_url_content(tool_url)
                if not error:
                    content_lower = content.lower()
                    has_docs = any(word in content_lower for word in ["documentation", "docs", "guide", "tutorial", "help"])
                    result["passed"] = has_docs
                    result["score"] = 1.0 if has_docs else 0.5
                    result["output"] = "Documentation reference found" if has_docs else "No documentation link found"
                else:
                    result["error_message"] = error

            else:
                result["output"] = f"Test type '{test_type}' not implemented"
                result["score"] = 0.5  # Neutral score for unimplemented tests

        except Exception as e:
            result["error_message"] = str(e)
            result["passed"] = False

        end_time = datetime.now(timezone.utc)
        result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
        test_results.append(result)

    # Calculate overall score
    if test_results:
        passed_count = sum(1 for r in test_results if r.get("passed"))
        overall_score = passed_count / len(test_results)
        overall_passed = all(
            r.get("passed") for r in test_results
            if test_cases[test_results.index(r)].get("severity") == "critical"
        )
    else:
        overall_score = 0.0
        overall_passed = False

    # Collect all red flags
    all_red_flags = []
    for r in test_results:
        all_red_flags.extend(r.get("red_flags", []))

    return {
        "test_results": test_results,
        "overall_test_score": overall_score,
        "red_flags": all_red_flags,
        "current_step": "run_tests_complete",
    }


# =============================================================================
# CONTENT GENERATION NODES
# =============================================================================

async def generate_framework_content(state: GovernanceTargetState) -> dict[str, Any]:
    """Generate Grounded-ready content for a framework."""
    errors = list(state.get("errors", []))
    generated_content: list[GeneratedContent] = []

    extracted_framework = state.get("extracted_framework", {})
    extracted_controls = state.get("extracted_controls", [])
    fetched_pages = state.get("fetched_pages", [])

    if not extracted_framework.get("name"):
        errors.append("No framework data to generate content from")
        return {
            "generated_content": [],
            "errors": errors,
            "current_step": "generate_content_complete",
        }

    framework_name = extracted_framework.get("name", "")
    short_name = extracted_framework.get("short_name", "")
    jurisdiction = extracted_framework.get("jurisdiction", "")

    # Build sources list from fetched pages
    sources: list[EvidenceSource] = [
        page for page in fetched_pages if page.get("fetch_status") == "success"
    ]

    try:
        client = get_openai_client()

        # Generate framework summary content
        prompt = f"""Write a comprehensive guide about "{framework_name}" ({short_name}) for journalists and newsroom technologists.

Framework Information:
- Type: {extracted_framework.get('framework_type', 'regulation')}
- Jurisdiction: {jurisdiction}
- Summary: {extracted_framework.get('summary', '')}
- Description: {extracted_framework.get('description', '')}
- Key Provisions: {json.dumps(extracted_framework.get('key_provisions', []))}
- Effective Date: {extracted_framework.get('effective_date', 'Unknown')}

Key Controls/Requirements:
{json.dumps([{"name": c.get("name"), "description": c.get("description")} for c in extracted_controls[:5]], indent=2)}

Write the content in Markdown format with:
1. A brief introduction (what is this framework and why it matters to journalists)
2. Key requirements section (bullet points)
3. Implications for newsrooms using AI tools
4. Compliance checklist (what newsrooms should do)
5. Further resources section

Keep the tone professional but accessible. Focus on practical implications for journalism."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=3000,
        )

        content_markdown = response.choices[0].message.content.strip()

        # Create slug
        slug = generate_slug(f"{short_name or framework_name}-guide")

        generated_content.append({
            "title": f"{short_name or framework_name}: A Guide for Journalists",
            "slug": slug,
            "content_markdown": content_markdown,
            "summary": extracted_framework.get("summary", ""),
            "content_type": "framework_summary",
            "section": "governance",
            "tags": ["governance", "compliance", jurisdiction.lower()] + extracted_framework.get("applies_to", []),
            "jurisdiction": jurisdiction,
            "audience": ["journalists", "editors", "technologists"],
            "sources": sources,
        })

    except Exception as e:
        errors.append(f"Content generation failed: {e}")

    return {
        "generated_content": generated_content,
        "errors": errors,
        "current_step": "generate_content_complete",
    }


async def generate_tool_content(state: GovernanceTargetState) -> dict[str, Any]:
    """Generate Grounded-ready content for a tool based on test results."""
    errors = list(state.get("errors", []))
    generated_content: list[GeneratedContent] = []

    tool_name = state.get("tool_name", state.get("target_name", ""))
    tool_url = state.get("tool_url", "")
    test_results = state.get("test_results", [])
    overall_score = state.get("overall_test_score", 0.0)
    red_flags = state.get("red_flags", [])

    if not tool_name:
        errors.append("No tool data to generate content from")
        return {
            "generated_content": [],
            "errors": errors,
            "current_step": "generate_content_complete",
        }

    try:
        client = get_openai_client()

        # Format test results for prompt
        test_summary = "\n".join([
            f"- {r.get('test_name')}: {'PASSED' if r.get('passed') else 'FAILED'} ({r.get('output', '')})"
            for r in test_results
        ])

        prompt = f"""Write a brief governance assessment guide for the tool "{tool_name}" for journalists.

Tool URL: {tool_url}
Overall Test Score: {overall_score * 100:.0f}%

Test Results:
{test_summary}

Red Flags Found:
{chr(10).join(['- ' + f for f in red_flags]) if red_flags else 'None'}

Write the content in Markdown format with:
1. Brief overview of the tool
2. Governance assessment summary (based on test results)
3. Privacy and security considerations
4. Red flags or concerns (if any)
5. Recommendations for use in newsrooms

Be factual and balanced. If there are concerns, mention them clearly but fairly."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000,
        )

        content_markdown = response.choices[0].message.content.strip()

        slug = generate_slug(f"{tool_name}-governance-guide")

        generated_content.append({
            "title": f"{tool_name}: Governance Assessment",
            "slug": slug,
            "content_markdown": content_markdown,
            "summary": f"Governance assessment for {tool_name} with {overall_score * 100:.0f}% compliance score.",
            "content_type": "tool_guide",
            "section": "tools",
            "tags": ["tool-assessment", "governance", "compliance"],
            "jurisdiction": "",
            "audience": ["journalists", "technologists"],
            "sources": [{"url": tool_url, "title": tool_name, "retrieved_at": datetime.now(timezone.utc).isoformat()}],
        })

    except Exception as e:
        errors.append(f"Tool content generation failed: {e}")

    return {
        "generated_content": generated_content,
        "errors": errors,
        "current_step": "generate_content_complete",
    }


# =============================================================================
# PERSISTENCE NODES
# =============================================================================

async def save_framework(state: GovernanceTargetState) -> dict[str, Any]:
    """Save extracted framework to database."""
    from app.db import SessionLocal
    from app.models.governance import GovernanceFramework, GovernanceControl

    errors = list(state.get("errors", []))
    framework_id = None

    extracted_framework = state.get("extracted_framework", {})
    extracted_controls = state.get("extracted_controls", [])
    fetched_pages = state.get("fetched_pages", [])

    if not extracted_framework.get("name"):
        return {"framework_id": None, "errors": errors}

    try:
        db = SessionLocal()

        # Create framework
        slug = generate_slug(extracted_framework.get("short_name") or extracted_framework.get("name", ""))

        # Check if exists
        existing = db.query(GovernanceFramework).filter(GovernanceFramework.slug == slug).first()
        if existing:
            framework = existing
        else:
            framework = GovernanceFramework(
                name=extracted_framework.get("name", ""),
                slug=slug,
                short_name=extracted_framework.get("short_name", ""),
                framework_type=extracted_framework.get("framework_type", "regulation"),
                jurisdiction=extracted_framework.get("jurisdiction", ""),
                jurisdiction_scope=extracted_framework.get("jurisdiction_scope", ""),
                description=extracted_framework.get("description", ""),
                summary=extracted_framework.get("summary", ""),
                key_provisions=extracted_framework.get("key_provisions", []),
                official_url=extracted_framework.get("official_url", ""),
                applies_to=extracted_framework.get("applies_to", []),
                evidence_sources=[
                    {"url": p.get("url"), "retrieved_at": p.get("retrieved_at"), "excerpt": p.get("excerpt", "")[:500]}
                    for p in fetched_pages if p.get("fetch_status") == "success"
                ],
                status="draft",
            )
            db.add(framework)

        # Handle effective date
        if extracted_framework.get("effective_date"):
            try:
                from datetime import date
                date_str = extracted_framework["effective_date"]
                if len(date_str) == 10:  # YYYY-MM-DD
                    framework.effective_date = date.fromisoformat(date_str)
            except (ValueError, TypeError):
                pass

        db.commit()
        framework_id = str(framework.id)

        # Add controls
        for ctrl_data in extracted_controls:
            control = GovernanceControl(
                framework_id=framework.id,
                control_id=ctrl_data.get("control_id", ""),
                name=ctrl_data.get("name", ""),
                description=ctrl_data.get("description", ""),
                obligations=ctrl_data.get("obligations", []),
                control_type=ctrl_data.get("control_type", ""),
                risk_level=ctrl_data.get("risk_level", "medium"),
                applies_to_tools=ctrl_data.get("applies_to_tools", False),
                applies_to_data=ctrl_data.get("applies_to_data", False),
                applies_to_content=ctrl_data.get("applies_to_content", False),
            )
            db.add(control)

        db.commit()
        db.close()

    except Exception as e:
        errors.append(f"Failed to save framework: {e}")

    return {
        "framework_id": framework_id,
        "errors": errors,
        "current_step": "save_framework_complete",
    }


async def save_test_results(state: GovernanceTargetState) -> dict[str, Any]:
    """Save tool test results to database."""
    from app.db import SessionLocal
    from app.models.governance import ToolsCatalogEntry, ToolTest

    errors = list(state.get("errors", []))

    tool_id = state.get("tool_id", "")
    test_results = state.get("test_results", [])
    overall_score = state.get("overall_test_score", 0.0)
    red_flags = state.get("red_flags", [])
    workflow_run_id = state.get("workflow_run_id")

    if not tool_id or not test_results:
        return {"errors": errors, "current_step": "save_tests_complete"}

    try:
        db = SessionLocal()
        from uuid import UUID

        tool = db.query(ToolsCatalogEntry).filter(ToolsCatalogEntry.id == UUID(tool_id)).first()
        if tool:
            # Update tool testing status
            tool.last_tested_at = datetime.now(timezone.utc)
            tool.last_test_passed = all(r.get("passed") for r in test_results)
            tool.test_score = overall_score
            tool.red_flags = red_flags

            # Save individual test results
            for result in test_results:
                test = ToolTest(
                    tool_id=tool.id,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=result.get("duration_ms", 0),
                    passed=result.get("passed", False),
                    score=result.get("score", 0.0),
                    status="passed" if result.get("passed") else "failed",
                    metrics=result.get("metrics", {}),
                    output=result.get("output", ""),
                    error_message=result.get("error_message", ""),
                    red_flags=result.get("red_flags", []),
                    workflow_run_id=UUID(workflow_run_id) if workflow_run_id else None,
                )
                db.add(test)

            db.commit()

        db.close()

    except Exception as e:
        errors.append(f"Failed to save test results: {e}")

    return {
        "errors": errors,
        "current_step": "save_tests_complete",
    }


async def save_content_items(state: GovernanceTargetState) -> dict[str, Any]:
    """Save generated content items to database for review."""
    from app.db import SessionLocal
    from app.models.governance import ContentItem

    errors = list(state.get("errors", []))
    content_item_ids: list[str] = []

    generated_content = state.get("generated_content", [])
    framework_id = state.get("framework_id")
    tool_id = state.get("tool_id")
    workflow_run_id = state.get("workflow_run_id")

    if not generated_content:
        return {"content_item_ids": [], "errors": errors, "current_step": "save_content_complete"}

    try:
        db = SessionLocal()
        from uuid import UUID

        for content in generated_content:
            # Check for existing slug
            slug = content.get("slug", "")
            existing = db.query(ContentItem).filter(ContentItem.slug == slug).first()
            if existing:
                # Create new version
                slug = f"{slug}-v{existing.version + 1}"

            item = ContentItem(
                title=content.get("title", ""),
                slug=slug,
                content_markdown=content.get("content_markdown", ""),
                summary=content.get("summary", ""),
                content_type=content.get("content_type", "guide"),
                section=content.get("section", "governance"),
                tags=content.get("tags", []),
                jurisdiction=content.get("jurisdiction", ""),
                audience=content.get("audience", []),
                sources=content.get("sources", []),
                framework_id=UUID(framework_id) if framework_id else None,
                tool_id=UUID(tool_id) if tool_id else None,
                generated_by_workflow=UUID(workflow_run_id) if workflow_run_id else None,
                status="pending_review",  # Always route to review
            )
            db.add(item)
            db.commit()
            content_item_ids.append(str(item.id))

        db.close()

    except Exception as e:
        errors.append(f"Failed to save content items: {e}")

    return {
        "content_item_ids": content_item_ids,
        "errors": errors,
        "current_step": "save_content_complete",
    }


# =============================================================================
# ROUTING/DECISION NODES
# =============================================================================

async def route_by_target_type(state: GovernanceTargetState) -> str:
    """Route workflow based on target type."""
    target_type = state.get("target_type", "framework")

    if target_type == "tool":
        return "tool_flow"
    elif target_type == "template":
        return "template_flow"
    else:
        return "framework_flow"


async def check_needs_review(state: GovernanceTargetState) -> dict[str, Any]:
    """Check if output needs human review."""
    errors = state.get("errors", [])
    generated_content = state.get("generated_content", [])
    red_flags = state.get("red_flags", [])

    needs_review = True  # Default to always needing review
    review_reason = "Generated content requires editorial review before publishing"

    if errors:
        review_reason = f"Workflow completed with errors: {len(errors)} issues found"
    elif red_flags:
        review_reason = f"Red flags detected: {', '.join(red_flags[:3])}"
    elif not generated_content:
        review_reason = "No content was generated"

    return {
        "needs_review": needs_review,
        "review_reason": review_reason,
        "current_step": "review_check_complete",
    }


async def finalize_target(state: GovernanceTargetState) -> dict[str, Any]:
    """Finalize the governance target processing."""
    errors = state.get("errors", [])

    processing_notes = []
    if state.get("framework_id"):
        processing_notes.append(f"Created/updated framework: {state.get('framework_id')}")
    if state.get("content_item_ids"):
        processing_notes.append(f"Generated {len(state.get('content_item_ids', []))} content items")
    if state.get("test_results"):
        passed = sum(1 for r in state.get("test_results", []) if r.get("passed"))
        total = len(state.get("test_results", []))
        processing_notes.append(f"Ran {total} tests, {passed} passed")
    if errors:
        processing_notes.append(f"Errors: {len(errors)}")

    return {
        "processing_notes": "\n".join(processing_notes),
        "current_step": "complete",
    }
