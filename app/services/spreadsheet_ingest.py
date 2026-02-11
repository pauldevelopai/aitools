"""Spreadsheet ingestion service for media organization imports."""
import json
from typing import Optional
from datetime import datetime, timezone

import pandas as pd
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.directory import MediaOrganization
from app.settings import settings
from app.models.spreadsheet_import import SpreadsheetImport


# Target fields for MediaOrganization
TARGET_FIELDS = {
    "name": {"required": True, "description": "Organization name (e.g. BBC, The Guardian)"},
    "org_type": {"required": True, "description": "Organization type (e.g. newspaper, broadcaster, digital, agency, magazine, or custom types)"},
    "country": {"required": False, "description": "Country where the organization is based"},
    "website": {"required": False, "description": "Website URL"},
    "description": {"required": False, "description": "Brief description of the organization"},
    "notes": {"required": False, "description": "Additional notes"},
}

SUGGESTED_ORG_TYPES = ["newspaper", "broadcaster", "digital", "agency", "magazine", "freelance_collective"]


def get_import_knowledge(db: Session) -> dict:
    """Build accumulated knowledge from past imports and the existing database.

    Returns a dict with:
        - column_patterns: common column→field mappings from past imports
        - known_org_types: all org_types in the database with counts
        - known_countries: all countries in the database with counts
        - past_import_summaries: brief summaries of recent completed imports
        - org_count: total organizations in the database
    """
    # 1. Column mapping patterns from completed imports
    column_patterns = {}
    completed = (
        db.query(SpreadsheetImport)
        .filter(SpreadsheetImport.status == "completed")
        .order_by(SpreadsheetImport.completed_at.desc())
        .limit(20)
        .all()
    )
    for imp in completed:
        if imp.column_mapping:
            for col, target in imp.column_mapping.items():
                col_lower = col.lower().strip()
                if col_lower not in column_patterns:
                    column_patterns[col_lower] = {}
                if target not in column_patterns[col_lower]:
                    column_patterns[col_lower][target] = 0
                column_patterns[col_lower][target] += 1

    # Keep only the most common mapping per column name
    best_mappings = {}
    for col, targets in column_patterns.items():
        best = max(targets, key=targets.get)
        best_mappings[col] = {"field": best, "times_used": targets[best]}

    # 2. All org_types from the database with counts
    org_type_counts = (
        db.query(MediaOrganization.org_type, func.count(MediaOrganization.id))
        .group_by(MediaOrganization.org_type)
        .order_by(func.count(MediaOrganization.id).desc())
        .all()
    )
    known_org_types = {ot: count for ot, count in org_type_counts if ot}

    # 3. All countries with counts
    country_counts = (
        db.query(MediaOrganization.country, func.count(MediaOrganization.id))
        .filter(MediaOrganization.country.isnot(None))
        .group_by(MediaOrganization.country)
        .order_by(func.count(MediaOrganization.id).desc())
        .limit(30)
        .all()
    )
    known_countries = {c: count for c, count in country_counts if c}

    # 4. Summaries of recent imports (what was imported, what defaults were used)
    past_summaries = []
    for imp in completed[:5]:
        summary = {
            "filename": imp.filename,
            "rows": imp.row_count,
            "created": imp.records_created,
            "updated": imp.records_updated,
        }
        if imp.field_defaults:
            summary["defaults_used"] = imp.field_defaults
        if imp.column_mapping:
            summary["mapping"] = imp.column_mapping
        past_summaries.append(summary)

    # 5. Total org count
    org_count = db.query(func.count(MediaOrganization.id)).scalar() or 0

    return {
        "column_patterns": best_mappings,
        "known_org_types": known_org_types,
        "known_countries": known_countries,
        "past_import_summaries": past_summaries,
        "org_count": org_count,
    }


def parse_spreadsheet(file_path: str, file_type: str) -> dict:
    """Parse a spreadsheet file and return headers, rows, and sample data.

    Returns:
        dict with keys: headers, rows (list of dicts), row_count, sample_rows
    """
    if file_type == "csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Drop completely empty rows
    df = df.dropna(how="all")

    headers = list(df.columns)
    rows = df.fillna("").astype(str).to_dict(orient="records")
    sample_rows = rows[:5]

    return {
        "headers": headers,
        "rows": rows,
        "row_count": len(rows),
        "sample_rows": sample_rows,
    }


def ai_map_columns(headers: list, sample_rows: list, knowledge: dict = None) -> dict:
    """Use GPT-4o-mini to map spreadsheet columns to target fields.

    Returns:
        dict with keys: mapping, unmapped, missing_required
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    target_desc = "\n".join(
        f"- {field}: {info['description']} {'(REQUIRED)' if info['required'] else '(optional)'}"
        for field, info in TARGET_FIELDS.items()
    )

    sample_text = ""
    for i, row in enumerate(sample_rows[:3]):
        sample_text += f"\nRow {i+1}: {json.dumps(row)}"

    # Build knowledge context from past imports
    knowledge_text = ""
    if knowledge and knowledge.get("column_patterns"):
        patterns = knowledge["column_patterns"]
        knowledge_text = "\n\nPrevious successful column mappings from this system:\n"
        for col, info in patterns.items():
            knowledge_text += f"- \"{col}\" was mapped to \"{info['field']}\" ({info['times_used']} times)\n"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a data mapping assistant. Given spreadsheet column headers and sample data,
map them to target database fields. Return ONLY valid JSON with no markdown formatting.""",
                },
                {
                    "role": "user",
                    "content": f"""Map these spreadsheet columns to the target fields.

Spreadsheet columns: {json.dumps(headers)}

Sample data:{sample_text}

Target fields:
{target_desc}
{knowledge_text}
Return a JSON object with this exact structure:
{{
    "mapping": {{"spreadsheet_column_name": "target_field_name_or_null"}},
    "unmapped_columns": ["columns that don't map to anything"],
    "missing_required": ["required target fields with no matching column"]
}}

Rules:
- Map each spreadsheet column to at most one target field
- Use null for columns that don't map to any target field
- Be smart about synonyms: "Organisation" = name, "Type" = org_type, "Location"/"Country" = country, "URL"/"Web" = website
- If previous mappings are provided, use them as strong hints for matching column names
- Only map a column if you're reasonably confident""",
                },
            ],
            max_tokens=500,
            temperature=0.1,
        )

        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        result = json.loads(content)

    except Exception as e:
        # Fallback: attempt simple name-based matching
        result = _fallback_mapping(headers)

    # Validate the mapping
    mapping = result.get("mapping", {})
    valid_mapping = {}
    used_targets = set()
    for col, target in mapping.items():
        if target and target in TARGET_FIELDS and target not in used_targets:
            valid_mapping[col] = target
            used_targets.add(target)

    unmapped = [h for h in headers if h not in valid_mapping]
    missing_required = [
        f for f, info in TARGET_FIELDS.items()
        if info["required"] and f not in used_targets
    ]

    return {
        "mapping": valid_mapping,
        "unmapped": unmapped,
        "missing_required": missing_required,
    }


def _fallback_mapping(headers: list) -> dict:
    """Simple keyword-based column mapping fallback."""
    mapping = {}
    keyword_map = {
        "name": ["name", "organisation", "organization", "org", "company", "outlet", "media"],
        "org_type": ["type", "org_type", "category", "kind"],
        "country": ["country", "location", "region", "nation", "based"],
        "website": ["website", "url", "web", "site", "link"],
        "description": ["description", "desc", "about", "summary"],
        "notes": ["notes", "note", "comments", "comment"],
    }
    used_targets = set()
    for header in headers:
        h_lower = header.lower().strip()
        for target, keywords in keyword_map.items():
            if target not in used_targets and any(kw in h_lower for kw in keywords):
                mapping[header] = target
                used_targets.add(target)
                break
        if header not in mapping:
            mapping[header] = None

    return {"mapping": mapping}


def ai_classify_rows(import_session: SpreadsheetImport, knowledge: dict = None) -> dict:
    """Use AI to classify org_type (and optionally country) for each row.

    Processes rows in batches and returns a row_overrides dict:
        {row_index_str: {"org_type": "...", "country": "..."}}
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    mapping = import_session.column_mapping or {}
    # Find the column mapped to 'name'
    name_col = None
    desc_col = None
    for col, target in mapping.items():
        if target == "name":
            name_col = col
        elif target == "description":
            desc_col = col

    if not name_col:
        return {}

    # Re-parse file to get all rows
    parsed = parse_spreadsheet(import_session.file_path, import_session.file_type)
    rows = parsed["rows"]

    # Determine which fields need per-row classification
    mapped_targets = set(mapping.values())
    needs_org_type = "org_type" not in mapped_targets
    needs_country = "country" not in mapped_targets

    if not needs_org_type and not needs_country:
        return {}

    classify_fields = []
    if needs_org_type:
        classify_fields.append("org_type")
    if needs_country:
        classify_fields.append("country")

    row_overrides = {}

    # Process in batches of 20
    batch_size = 20
    for batch_start in range(0, len(rows), batch_size):
        batch = rows[batch_start:batch_start + batch_size]

        orgs_list = []
        for i, row in enumerate(batch):
            idx = batch_start + i
            name = str(row.get(name_col, "")).strip()
            desc = str(row.get(desc_col, "")).strip() if desc_col else ""
            if name:
                entry = {"idx": idx, "name": name}
                if desc:
                    entry["desc"] = desc[:200]
                orgs_list.append(entry)

        if not orgs_list:
            continue

        # Build known types from knowledge
        all_org_types = list(SUGGESTED_ORG_TYPES)
        if knowledge and knowledge.get("known_org_types"):
            for ot in knowledge["known_org_types"]:
                if ot and ot not in all_org_types:
                    all_org_types.append(ot)

        field_instructions = ""
        if needs_org_type:
            field_instructions += f"""
- "org_type": Classify using one of these known types: {json.dumps(all_org_types)}
  You can also create new types if none fit well (e.g. "student_newspaper", "community_radio", "think_tank"). Use snake_case.
  Use your knowledge of the media landscape. For example:
  - BBC, CNN, RTE = broadcaster
  - The Guardian, Irish Times = newspaper
  - BuzzFeed, HuffPost = digital
  - Reuters, AP = agency
  - Time, Vogue = magazine
  If unsure, use "digital" as fallback."""
        if needs_country:
            field_instructions += """
- "country": The country where the organization is headquartered.
  Use your knowledge. For example: BBC = "United Kingdom", CNN = "United States".
  If you genuinely don't know, omit the country field for that row."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a media industry expert. Classify media organizations. Return ONLY valid JSON, no markdown.",
                    },
                    {
                        "role": "user",
                        "content": f"""Classify these media organizations. For each, provide:{field_instructions}

Organizations:
{json.dumps(orgs_list)}

Return a JSON array where each element has "idx" (the original index) and the classification fields.
Example: [{{"idx": 0, "org_type": "newspaper", "country": "Ireland"}}]""",
                    },
                ],
                max_tokens=2000,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
            classifications = json.loads(content)

            for item in classifications:
                idx = str(item.get("idx", ""))
                overrides = {}
                if needs_org_type and item.get("org_type"):
                    ot = item["org_type"].lower().strip().replace(" ", "_")
                    overrides["org_type"] = ot
                if needs_country and item.get("country"):
                    overrides["country"] = item["country"]
                if overrides:
                    row_overrides[idx] = overrides

        except Exception:
            # If a batch fails, skip it — rows without overrides will use defaults
            continue

    return row_overrides


def generate_chat_response(import_session: SpreadsheetImport, user_message: str, knowledge: dict = None) -> dict:
    """Generate an AI chat response about missing data, updating field_defaults.

    Returns:
        dict with keys: response, chat_history, field_defaults, is_complete
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    mapping = import_session.column_mapping or {}
    field_defaults = import_session.field_defaults or {}
    mapped_targets = set(mapping.values())

    missing_fields = [
        f for f in TARGET_FIELDS
        if f not in mapped_targets and f not in field_defaults
    ]
    missing_required = [f for f in missing_fields if TARGET_FIELDS[f]["required"]]
    missing_optional = [f for f in missing_fields if not TARGET_FIELDS[f]["required"]]

    # Build a rich context about what we actually know
    mapped_summary = {col: target for col, target in mapping.items()}
    sample_data_summary = ""
    if import_session.sample_rows:
        for i, row in enumerate(import_session.sample_rows[:3]):
            # Only show mapped columns' values
            relevant = {mapping.get(k, k): v for k, v in row.items() if k in mapping and v}
            if relevant:
                sample_data_summary += f"\nRow {i+1}: {json.dumps(relevant)}"

    chat_history = list(import_session.chat_history or [])
    chat_history.append({"role": "user", "content": user_message})

    # Check if row_overrides already exist (AI classification already ran)
    has_row_overrides = bool(import_session.row_overrides)

    # Build knowledge context
    knowledge_section = ""
    if knowledge:
        all_org_types = list(SUGGESTED_ORG_TYPES)
        if knowledge.get("known_org_types"):
            for ot in knowledge["known_org_types"]:
                if ot and ot not in all_org_types:
                    all_org_types.append(ot)
            knowledge_section += f"\n**Org types already in the database** (with counts): {json.dumps(knowledge['known_org_types'])}"

        if knowledge.get("known_countries"):
            top_countries = dict(list(knowledge["known_countries"].items())[:10])
            knowledge_section += f"\n**Countries already in the database** (with counts): {json.dumps(top_countries)}"

        if knowledge.get("past_import_summaries"):
            knowledge_section += "\n**Recent past imports:**"
            for s in knowledge["past_import_summaries"][:3]:
                knowledge_section += f"\n- {s['filename']}: {s['rows']} rows, {s.get('created', 0)} created"
                if s.get("defaults_used"):
                    knowledge_section += f", defaults: {json.dumps(s['defaults_used'])}"

        if knowledge.get("org_count"):
            knowledge_section += f"\n**Total organizations in database:** {knowledge['org_count']}"

    system_prompt = f"""You are a helpful assistant guiding an admin through importing media organizations from a spreadsheet into the Grounded platform.

**Context about this import:**
- Filename: {import_session.filename}
- Total rows: {import_session.row_count}
- Columns mapped: {json.dumps(mapped_summary)}
- Sample data from mapped columns:{sample_data_summary or " (no sample data available)"}

**Fields still needing values:**
- Required missing: {json.dumps(missing_required) if missing_required else "None — all covered!"}
- Optional missing: {json.dumps(missing_optional) if missing_optional else "None"}
- Currently set defaults: {json.dumps(field_defaults) if field_defaults else "None yet"}
- AI per-row classification done: {"Yes" if has_row_overrides else "No"}
{knowledge_section}

**CRITICAL — understand which fields are per-row vs blanket defaults:**
- **org_type** varies per organization (BBC is a broadcaster, The Guardian is a newspaper). NEVER ask for a single org_type default for all rows. Instead, tell the admin the system can auto-classify each organization's type using AI. If the user says "yes" or agrees to auto-classify, respond with exactly: `[CLASSIFY_ROWS]` on its own line. This triggers the auto-classification system. After classification is done, the system will update you.
- **org_type is FLEXIBLE** — the admin can define completely new types (e.g. "student_newspaper", "community_radio", "ngo", "think_tank"). If the admin suggests a new type, ACCEPT IT enthusiastically. Convert to snake_case. Never refuse a custom type.
- **country** CAN be a blanket default if all orgs are from the same country, but could also vary. Ask if the organizations are all from one country or if they vary. If they vary, suggest auto-classification. Use the known countries from the database as context for suggestions.
- **name** always comes from the spreadsheet column — never needs a default.
- **website**, **description**, **notes** are optional and per-row. Don't suggest placeholder defaults for these — just skip them.

**Your approach:**
- Be conversational, warm, and concise. ONE question at a time.
- Look at the filename and sample data for clues. E.g. "DNTF - Grantee_overview.xlsx" suggests these are grantee organizations.
- **Use knowledge from past imports** to make smarter suggestions. If similar spreadsheets were imported before, reference that. If certain defaults were commonly used, suggest them.
- If org_type is missing and hasn't been auto-classified yet, your FIRST question should offer to auto-classify. Explain briefly that each org will be individually classified.
- If country is missing, ask about it after org_type is handled. Look at the data for clues. If the database already has organizations from certain countries, mention that context.
- When all required fields are covered (by mapping, defaults, or per-row classification), tell the admin they're ready to proceed.
- Don't suggest "N/A" or empty placeholder values. If a field isn't relevant, just skip it.

**IMPORTANT:** At the end of every response, include a JSON block in <defaults>...</defaults> tags with any blanket default values extracted. Example:
<defaults>{{"country": "Ireland"}}</defaults>

If no new blanket defaults, use: <defaults>{{}}</defaults>"""

    messages = [{"role": "system", "content": system_prompt}]
    # Include recent chat history (last 10 exchanges)
    for msg in chat_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600,
            temperature=0.4,
        )
        content = response.choices[0].message.content
    except Exception as e:
        content = f"Sorry, I had trouble processing that. Error: {str(e)}\n<defaults>{{}}</defaults>"

    # Extract defaults from response
    new_defaults = {}
    if "<defaults>" in content and "</defaults>" in content:
        try:
            defaults_str = content.split("<defaults>")[1].split("</defaults>")[0]
            new_defaults = json.loads(defaults_str)
        except (json.JSONDecodeError, IndexError):
            pass
        # Clean the visible response
        display_content = content.split("<defaults>")[0].strip()
    else:
        display_content = content

    # Update field_defaults
    updated_defaults = dict(field_defaults)
    updated_defaults.update(new_defaults)

    # Check if we're complete (all required fields covered)
    # Row overrides count as covering per-row fields like org_type
    has_row_overrides = bool(import_session.row_overrides)
    all_required_covered = all(
        f in mapped_targets or f in updated_defaults or (f == "org_type" and has_row_overrides)
        for f, info in TARGET_FIELDS.items()
        if info["required"]
    )

    chat_history.append({"role": "assistant", "content": display_content})

    return {
        "response": display_content,
        "chat_history": chat_history,
        "field_defaults": updated_defaults,
        "is_complete": all_required_covered,
    }


def validate_and_preview(import_session: SpreadsheetImport) -> list:
    """Validate all rows against the mapping and defaults.

    Returns:
        list of dicts: [{row_num, data, status, errors}]
    """
    mapping = import_session.column_mapping or {}
    defaults = import_session.field_defaults or {}

    # Re-parse the file to get all rows
    parsed = parse_spreadsheet(import_session.file_path, import_session.file_type)
    rows = parsed["rows"]

    row_overrides = import_session.row_overrides or {}

    # Collect all mapped field names (standard + custom) for display
    all_mapped_fields = set(mapping.values())
    all_mapped_fields.discard(None)

    preview = []
    for i, row in enumerate(rows):
        record = dict(defaults)  # Start with defaults

        # Apply per-row AI classifications
        overrides = row_overrides.get(str(i), {})
        record.update(overrides)

        # Apply mapping (spreadsheet data takes priority)
        for col, target in mapping.items():
            if target and col in row and str(row[col]).strip():
                record[target] = str(row[col]).strip()

        # Also preserve ALL original row data as _raw for reference
        record["_raw"] = {col: str(row.get(col, "")).strip() for col in row if str(row.get(col, "")).strip()}

        # Validate
        errors = []
        if not record.get("name"):
            errors.append("Missing required field: name")
        if not record.get("org_type"):
            errors.append("Missing required field: org_type")
        else:
            # Normalize to lowercase snake_case
            record["org_type"] = record["org_type"].lower().strip().replace(" ", "_")

        status = "error" if errors else "valid"
        if not errors and not record.get("country"):
            status = "warning"

        preview.append({
            "row_num": i + 1,
            "data": record,
            "status": status,
            "errors": errors,
        })

    return preview


def _normalize_org_type(value: str) -> Optional[str]:
    """Try to normalize an org_type string to a valid value."""
    v = value.lower().strip()
    aliases = {
        "newspaper": ["newspaper", "paper", "print", "daily", "weekly"],
        "broadcaster": ["broadcaster", "broadcast", "tv", "television", "radio"],
        "digital": ["digital", "online", "web", "internet"],
        "agency": ["agency", "news agency", "wire", "wire service"],
        "magazine": ["magazine", "mag", "periodical"],
        "freelance_collective": ["freelance", "collective", "freelance_collective", "independent"],
    }
    for org_type, keywords in aliases.items():
        if v in keywords or any(kw in v for kw in keywords):
            return org_type
    return None


def execute_import(db: Session, import_session: SpreadsheetImport) -> dict:
    """Execute the actual import, creating/updating MediaOrganization records.

    Returns:
        dict with keys: created, updated, skipped, errors
    """
    preview = validate_and_preview(import_session)

    created = 0
    updated = 0
    skipped = 0
    errors = []

    for item in preview:
        if item["status"] == "error":
            skipped += 1
            errors.append({
                "row": item["row_num"],
                "errors": item["errors"],
                "data": item["data"].get("name", "Unknown"),
            })
            continue

        data = item["data"]
        name = data.get("name", "").strip()
        if not name:
            skipped += 1
            continue

        # Standard MediaOrganization fields
        standard_fields = {"name", "org_type", "country", "website", "description", "notes", "_raw"}

        # Collect custom field data and append to notes
        custom_parts = []
        for key, val in data.items():
            if key not in standard_fields and val and str(val).strip():
                custom_parts.append(f"{key}: {val}")

        notes = data.get("notes", "") or ""
        if custom_parts:
            extra = "\n".join(custom_parts)
            notes = f"{notes}\n{extra}".strip() if notes else extra

        # Check for existing organization by name (case-insensitive)
        existing = db.query(MediaOrganization).filter(
            func.lower(MediaOrganization.name) == name.lower()
        ).first()

        if existing:
            # Update existing
            if data.get("org_type"):
                existing.org_type = data["org_type"]
            if data.get("country"):
                existing.country = data["country"]
            if data.get("website"):
                existing.website = data["website"]
            if data.get("description"):
                existing.description = data["description"]
            if notes:
                existing.notes = notes
            if import_session.client_id and not existing.client_id:
                existing.client_id = import_session.client_id
            updated += 1
        else:
            # Create new
            org = MediaOrganization(
                name=name,
                org_type=data.get("org_type", "digital"),
                country=data.get("country"),
                website=data.get("website"),
                description=data.get("description"),
                notes=notes or None,
                is_active=data.get("is_active", True),
                client_id=import_session.client_id,
            )
            db.add(org)
            created += 1

    db.flush()

    # Update import session
    import_session.records_created = created
    import_session.records_updated = updated
    import_session.records_skipped = skipped
    import_session.import_errors = errors
    import_session.status = "completed"
    import_session.completed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }
