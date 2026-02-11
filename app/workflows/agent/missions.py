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
}
