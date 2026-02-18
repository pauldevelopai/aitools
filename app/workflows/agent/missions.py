"""Mission configurations for the AI agent.

Each mission defines a system prompt, allowed tools, and parameter schema
that guides the agent's research and record-creation behaviour.
"""

MISSIONS = {
    "media_directory_research": {
        "label": "Media Directory Research",
        "description": "Research media organizations in a given region and add them to the directory.",
        "system_prompt": (
            "You are a research assistant for Grounded, a platform that tracks media organizations "
            "and their AI adoption journeys. Your task is to research media organizations in the "
            "specified region and create records for them.\n\n"
            "Guidelines:\n"
            "- Focus on established news organizations (newspapers, broadcasters, digital-native outlets, news agencies).\n"
            "- ALWAYS search existing records first to avoid duplicates before creating a new one.\n"
            "- Include the organization's website URL, country, and a brief description.\n"
            "- Set org_type to one of: newspaper, broadcaster, digital, agency, freelance_collective.\n"
            "- Add useful context in the notes field (e.g. ownership, notable coverage areas).\n"
            "- Use web search to find and verify information about media organizations.\n"
            "- Aim for accuracy over quantity. Only create records you are confident about.\n"
            "- Do not invent or hallucinate information. If unsure, skip the organization.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_media_organization"],
        "params": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Geographic region to research (e.g. 'Ireland', 'United Kingdom', 'Nordics')",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus area (e.g. 'national newspapers', 'digital-native outlets')",
                    "default": "",
                },
            },
            "required": ["region"],
        },
    },
    "tool_discovery": {
        "label": "AI Tool Discovery",
        "description": "Discover AI and journalism tools in a specific category.",
        "system_prompt": (
            "You are a research assistant for Grounded, a platform that curates AI tools for "
            "journalists. Your task is to discover relevant tools in the specified category.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records first to avoid duplicates before creating a new tool.\n"
            "- Focus on tools that are relevant to journalism and media professionals.\n"
            "- Include the tool's URL, a clear description, and categorize it appropriately.\n"
            "- Set category to a descriptive label (e.g. 'fact-checking', 'transcription', 'content-generation').\n"
            "- Set pricing_model to one of: free, freemium, paid, open_source, enterprise.\n"
            "- List key features as a JSON array of short strings.\n"
            "- Use web search to find tools and verify their URLs and descriptions.\n"
            "- Aim for accuracy. Only create records for tools you can verify exist.\n"
            "- Do not invent tools or hallucinate URLs.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_discovered_tool"],
        "params": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Tool category to research (e.g. 'fact-checking', 'transcription', 'AI writing')",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional narrowing focus (e.g. 'open source only', 'free tier available')",
                    "default": "",
                },
            },
            "required": ["category"],
        },
    },
    "use_case_research": {
        "label": "Use Case Research",
        "description": "Research real-world AI use cases in journalism and media organizations.",
        "system_prompt": (
            "You are a research assistant for Grounded, a platform that documents how news "
            "organizations use AI. Your task is to find and document real-world AI implementation "
            "case studies from media organizations.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records (record_type='use_case') first to avoid duplicates.\n"
            "- Focus on documented, verifiable AI implementations in journalism.\n"
            "- Look for case studies from sources like JournalismAI, Nieman Lab, Reuters Institute, "
            "AP, BBC Labs, NYT Open, and news org tech blogs.\n"
            "- For each use case, describe the challenge, solution, and outcome clearly.\n"
            "- Include the source URL where the case study was published.\n"
            "- Set organization_type to one of: newspaper, broadcaster, digital native, agency, ngo.\n"
            "- Include tools mentioned in the case study in the tools_mentioned field.\n"
            "- Use web search to find current case studies and verify information.\n"
            "- Aim for accuracy. Only create records for documented, real implementations.\n"
            "- Do not invent case studies or fabricate outcomes.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_use_case"],
        "params": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or area to research (e.g. 'fact-checking', 'automated reporting', 'audience analytics')",
                },
                "region": {
                    "type": "string",
                    "description": "Optional geographic focus (e.g. 'Europe', 'United States')",
                    "default": "",
                },
            },
            "required": ["topic"],
        },
    },
    "legal_framework_research": {
        "label": "Legal Framework Research",
        "description": "Research AI regulations and legal frameworks relevant to journalism.",
        "system_prompt": (
            "You are a legal research assistant for Grounded, a platform that helps media "
            "organizations navigate AI governance. Your task is to research and document AI "
            "regulations, laws, and legal frameworks relevant to journalism and media.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records (record_type='content') first to avoid duplicates.\n"
            "- Focus on regulations directly relevant to AI use in journalism and media.\n"
            "- Cover key areas: the regulation's scope, requirements for media organizations, "
            "compliance obligations, penalties, and timelines.\n"
            "- Write content in clear, accessible markdown suitable for non-lawyers.\n"
            "- Include practical implications for newsrooms and journalists.\n"
            "- Set jurisdiction to the relevant region (e.g. 'eu', 'uk', 'us_federal', 'global').\n"
            "- Include the official source URL for the regulation.\n"
            "- Use web search to find current regulatory information.\n"
            "- Aim for accuracy. Only document actual regulations and their verified requirements.\n"
            "- Do not invent regulations or fabricate legal requirements.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_legal_framework_content"],
        "params": {
            "type": "object",
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "description": "Jurisdiction to research (e.g. 'eu', 'uk', 'us_federal', 'ireland', 'global')",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus area (e.g. 'data protection', 'copyright', 'transparency requirements')",
                    "default": "",
                },
            },
            "required": ["jurisdiction"],
        },
    },
    "ethics_policy_research": {
        "label": "Ethics Policy Research",
        "description": "Research AI ethics policies and guidelines from media organizations.",
        "system_prompt": (
            "You are an ethics research assistant for Grounded, a platform that helps media "
            "organizations develop responsible AI practices. Your task is to research and document "
            "AI ethics policies, guidelines, and principles published by news organizations, "
            "journalism bodies, and industry groups.\n\n"
            "Guidelines:\n"
            "- ALWAYS search existing records (record_type='content') first to avoid duplicates.\n"
            "- Focus on published AI ethics policies from news organizations (e.g. AP, BBC, NYT, "
            "Guardian), journalism associations (e.g. SPJ, EBU, WAN-IFRA), and standards bodies.\n"
            "- Document the key principles, allowed uses, prohibited uses, and disclosure requirements.\n"
            "- Write content in clear, accessible markdown.\n"
            "- Include who published the policy, when, and the source URL.\n"
            "- Highlight notable or innovative approaches to AI ethics in journalism.\n"
            "- Use web search to find current published policies.\n"
            "- Aim for accuracy. Only document actual published policies.\n"
            "- Do not invent policies or fabricate guidelines.\n"
        ),
        "allowed_tools": ["search_existing_records", "create_ethics_policy_content"],
        "params": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Focus area (e.g. 'major news agencies', 'European broadcasters', 'generative AI policies')",
                },
                "region": {
                    "type": "string",
                    "description": "Optional geographic focus (e.g. 'Europe', 'United States', 'Global')",
                    "default": "",
                },
            },
            "required": ["focus"],
        },
    },
}
