"""Mission configurations for the Grounded Brain.

Each mission defines a system prompt supplement, allowed tools,
parameter schema, and user message builder. Missions are broader
than the original journalism-only focus — covering newsrooms,
NGOs, law firms, and businesses.
"""

from typing import Any


def _build_media_directory_message(params: dict[str, Any]) -> str:
    region = params.get("region", "the specified region")
    focus = params.get("focus", "")
    msg = f"Research and catalog media organizations in {region}."
    if focus:
        msg += f" Focus on: {focus}."
    msg += (
        " Use your knowledge to identify current media organizations."
        " For each organization, first search existing records to check for duplicates, "
        "then create a record if it doesn't exist. Aim for the major established outlets."
    )
    return msg


def _build_tool_discovery_message(params: dict[str, Any]) -> str:
    category = params.get("category", "the specified category")
    focus = params.get("focus", "")
    msg = f"Discover AI tools relevant to organisations in the '{category}' category."
    if focus:
        msg += f" Focus on: {focus}."
    msg += (
        " Identify current tools and verify their URLs."
        " For each tool, first search existing records to check for duplicates, "
        "then create a record if it doesn't exist. Include accurate URLs and descriptions."
    )
    return msg


def _build_use_case_message(params: dict[str, Any]) -> str:
    topic = params.get("topic", "ethical AI implementation")
    region = params.get("region", "")
    msg = f"Research real-world AI use cases related to '{topic}'."
    if region:
        msg += f" Focus on organizations in {region}."
    msg += (
        " Find documented case studies from newsrooms, NGOs, law firms, "
        "and businesses implementing AI ethically."
        " For each use case, first search existing records (record_type='use_case') "
        "to check for duplicates, then create a record with the challenge, solution, and outcome."
    )
    return msg


def _build_legal_framework_message(params: dict[str, Any]) -> str:
    jurisdiction = params.get("jurisdiction", "the specified jurisdiction")
    focus = params.get("focus", "")
    msg = (
        f"Research AI regulations and legal frameworks in the '{jurisdiction}' "
        "jurisdiction that are relevant to organisations implementing AI."
    )
    if focus:
        msg += f" Focus on: {focus}."
    msg += (
        " Identify current regulatory information."
        " For each regulation, first search existing records (record_type='content') "
        "to check for duplicates, then create a content item with a clear explanation "
        "of requirements and implications for organisations."
    )
    return msg


def _build_ethics_policy_message(params: dict[str, Any]) -> str:
    focus = params.get("focus", "AI ethics in organisations")
    region = params.get("region", "")
    msg = f"Research published AI ethics policies and guidelines related to '{focus}'."
    if region:
        msg += f" Focus on organizations in {region}."
    msg += (
        " Find current published policies from organisations "
        "across newsrooms, NGOs, law firms, and businesses."
        " For each policy, first search existing records (record_type='content') "
        "to check for duplicates, then create a content item documenting the key "
        "principles, allowed uses, and disclosure requirements."
    )
    return msg


def _build_lesson_generation_message(params: dict[str, Any]) -> str:
    module_slug = params.get("module_slug", "")
    topic = params.get("topic", "AI skills")
    sector = params.get("sector", "")
    gap_topics = params.get("gap_topics", "")
    count = params.get("count", 3)

    msg = (
        f"Generate {count} practical micro-lessons for the module '{module_slug}' "
        f"focused on the topic: '{topic}'."
    )
    if sector:
        msg += f" Tailor content for the '{sector}' sector."
    if gap_topics:
        msg += f" Address these knowledge gaps in particular: {gap_topics}."
    msg += (
        " For each lesson: search existing lessons first to avoid duplicates, "
        "then create a lesson with rich markdown content, clear learning objectives, "
        "and a specific practical task. "
        "Use ai_review verification for tasks requiring written reflection, "
        "self_report for action-based tasks."
    )
    return msg


MISSIONS: dict[str, dict[str, Any]] = {
    "media_directory_research": {
        "label": "Media Directory Research",
        "description": "Research media organizations in a given region and add them to the directory.",
        "system_prompt_supplement": (
            "Your task is to research media organizations in the specified region "
            "and create records for them.\n\n"
            "Guidelines:\n"
            "- Focus on established news organizations (newspapers, broadcasters, "
            "digital-native outlets, news agencies).\n"
            "- ALWAYS search existing records first to avoid duplicates.\n"
            "- Include the organization's website URL, country, and a brief description.\n"
            "- Set org_type to one of: newspaper, broadcaster, digital, agency, freelance_collective.\n"
            "- Add useful context in the notes field (ownership, notable coverage areas).\n"
            "- Aim for accuracy over quantity.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_media_organization"],
        "params": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Geographic region to research (e.g. 'Ireland', 'United Kingdom')",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus area (e.g. 'national newspapers')",
                    "default": "",
                },
            },
            "required": ["region"],
        },
        "build_user_message": _build_media_directory_message,
    },
    "tool_discovery": {
        "label": "AI Tool Discovery",
        "description": "Discover AI tools in a specific category relevant to organisations.",
        "system_prompt_supplement": (
            "Your task is to discover relevant AI tools in the specified category "
            "for organisations implementing AI ethically.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records first to avoid duplicates.\n"
            "- Focus on tools relevant to newsrooms, NGOs, law firms, and businesses.\n"
            "- Include the tool's URL, a clear description, and categorize it.\n"
            "- Set pricing_model to one of: free, freemium, paid, open_source, enterprise.\n"
            "- Aim for accuracy. Only create records for tools you can verify exist.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_discovered_tool"],
        "params": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Tool category (e.g. 'fact-checking', 'transcription', 'AI writing')",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional narrowing focus (e.g. 'open source only')",
                    "default": "",
                },
            },
            "required": ["category"],
        },
        "build_user_message": _build_tool_discovery_message,
    },
    "use_case_research": {
        "label": "Use Case Research",
        "description": "Research real-world AI use cases across organisations.",
        "system_prompt_supplement": (
            "Your task is to find and document real-world AI implementation "
            "case studies from organisations across sectors.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records (record_type='use_case') first.\n"
            "- Focus on documented, verifiable AI implementations.\n"
            "- Look for case studies from industry sources, research institutes, "
            "and org tech blogs.\n"
            "- For each use case, describe the challenge, solution, and outcome clearly.\n"
            "- Include the source URL where the case study was published.\n"
            "- Set organization_type appropriately (newspaper, broadcaster, "
            "digital native, agency, ngo, law_firm, business).\n"
            "- Include tools mentioned in the tools_mentioned field.\n"
            "- Aim for accuracy. Only document real implementations.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_use_case"],
        "params": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic (e.g. 'fact-checking', 'automated reporting')",
                },
                "region": {
                    "type": "string",
                    "description": "Optional geographic focus",
                    "default": "",
                },
            },
            "required": ["topic"],
        },
        "build_user_message": _build_use_case_message,
    },
    "legal_framework_research": {
        "label": "Legal Framework Research",
        "description": "Research AI regulations and legal frameworks relevant to organisations.",
        "system_prompt_supplement": (
            "Your task is to research and document AI regulations, laws, and "
            "legal frameworks relevant to organisations implementing AI.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records (record_type='content') first.\n"
            "- Cover: scope, requirements, compliance obligations, penalties, timelines.\n"
            "- Write in clear, accessible markdown suitable for non-lawyers.\n"
            "- Include practical implications for different types of organisations.\n"
            "- Set jurisdiction to the relevant region (e.g. 'eu', 'uk', 'us_federal').\n"
            "- Include the official source URL for the regulation.\n"
            "- Aim for accuracy. Only document actual regulations.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_legal_framework_content"],
        "params": {
            "type": "object",
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "description": "Jurisdiction (e.g. 'eu', 'uk', 'us_federal', 'global')",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus area (e.g. 'data protection', 'copyright')",
                    "default": "",
                },
            },
            "required": ["jurisdiction"],
        },
        "build_user_message": _build_legal_framework_message,
    },
    "ethics_policy_research": {
        "label": "Ethics Policy Research",
        "description": "Research AI ethics policies and guidelines from organisations.",
        "system_prompt_supplement": (
            "Your task is to research and document AI ethics policies, "
            "guidelines, and principles published by organisations and industry bodies.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records (record_type='content') first.\n"
            "- Document key principles, allowed uses, prohibited uses, disclosure requirements.\n"
            "- Write in clear, accessible markdown.\n"
            "- Include who published the policy, when, and the source URL.\n"
            "- Highlight notable or innovative approaches to AI ethics.\n"
            "- Aim for accuracy. Only document actual published policies.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_ethics_policy_content"],
        "params": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Focus area (e.g. 'major news agencies', 'generative AI policies')",
                },
                "region": {
                    "type": "string",
                    "description": "Optional geographic focus",
                    "default": "",
                },
            },
            "required": ["focus"],
        },
        "build_user_message": _build_ethics_policy_message,
    },
    "lesson_generation": {
        "label": "Lesson Generation",
        "description": "Generate practical micro-lessons for a module based on knowledge gaps and user data.",
        "system_prompt_supplement": (
            "Your task is to create high-quality educational micro-lessons for the Grounded platform.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing lessons first to avoid duplicates.\n"
            "- Each lesson should cover ONE clear concept or skill.\n"
            "- Content should be practical and grounded in real scenarios from the sector.\n"
            "- Learning objectives must be specific and actionable (start with a verb: 'Identify', 'Draft', 'Explain').\n"
            "- Task prompts must be specific enough that a user knows exactly what to produce.\n"
            "- For ai_review lessons: the task must require a written response that Claude can meaningfully evaluate.\n"
            "- For self_report lessons: the task must be a concrete action the user can confirm completing.\n"
            "- Content markdown should be at least 200 words with headers, bullet points, and examples.\n"
            "- Estimated time: 5-20 minutes per lesson.\n"
            "- All created lessons have status='draft' and require admin review before publishing.\n"
        ),
        "allowed_tools": ["search_existing_lessons", "create_lesson"],
        "params": {
            "type": "object",
            "properties": {
                "module_slug": {
                    "type": "string",
                    "description": "Slug of the target module (e.g. 'ai-foundations').",
                },
                "topic": {
                    "type": "string",
                    "description": "Topic focus (e.g. 'prompt engineering', 'AI in HR').",
                },
                "sector": {
                    "type": "string",
                    "description": "Optional sector for tailoring (newsroom/ngo/law_firm/business).",
                    "default": "",
                },
                "gap_topics": {
                    "type": "string",
                    "description": "Optional comma-separated knowledge gap topics to address.",
                    "default": "",
                },
                "count": {
                    "type": "integer",
                    "description": "Target number of lessons to generate (default: 3).",
                    "default": 3,
                },
            },
            "required": ["module_slug", "topic"],
        },
        "build_user_message": _build_lesson_generation_message,
    },
}
