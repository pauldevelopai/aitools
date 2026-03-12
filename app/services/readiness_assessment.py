"""AI Readiness Assessment service.

Defines questions, calculates dimension scores, determines maturity level,
and generates personalised recommendations using Claude.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.readiness import ReadinessAssessment
from app.services.completion import get_completion_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------
DIMENSIONS = ["awareness", "policy", "tools", "governance", "skills"]

# ---------------------------------------------------------------------------
# Assessment questions — each maps to a dimension, options scored 1-5
# ---------------------------------------------------------------------------
ASSESSMENT_QUESTIONS = [
    # AWARENESS (3 questions)
    {
        "id": "a1",
        "dimension": "awareness",
        "text": "How would you describe your organisation's general awareness of AI capabilities and limitations?",
        "options": [
            {"value": 1, "label": "Very limited — most staff have no exposure to AI"},
            {"value": 2, "label": "Basic — a few individuals have explored AI tools"},
            {"value": 3, "label": "Moderate — several teams are aware and experimenting"},
            {"value": 4, "label": "Good — AI is a regular topic in leadership discussions"},
            {"value": 5, "label": "Excellent — organisation-wide understanding of AI opportunities and risks"},
        ],
    },
    {
        "id": "a2",
        "dimension": "awareness",
        "text": "Does your organisation have a shared understanding of where AI could add the most value?",
        "options": [
            {"value": 1, "label": "No — we haven't discussed this"},
            {"value": 2, "label": "Informally — some people have ideas"},
            {"value": 3, "label": "Partially — a few use cases have been identified"},
            {"value": 4, "label": "Yes — we have a prioritised list of AI opportunities"},
            {"value": 5, "label": "Yes — and we've already piloted several"},
        ],
    },
    {
        "id": "a3",
        "dimension": "awareness",
        "text": "How confident is your leadership team about making AI-related decisions?",
        "options": [
            {"value": 1, "label": "Not confident at all"},
            {"value": 2, "label": "Slightly confident — need significant guidance"},
            {"value": 3, "label": "Somewhat confident — can evaluate proposals with support"},
            {"value": 4, "label": "Confident — can lead AI initiatives"},
            {"value": 5, "label": "Very confident — leadership champions AI strategy"},
        ],
    },
    # POLICY (3 questions)
    {
        "id": "p1",
        "dimension": "policy",
        "text": "Does your organisation have an AI ethics policy or guidelines?",
        "options": [
            {"value": 1, "label": "No policy and no plans to create one"},
            {"value": 2, "label": "We've discussed the need but haven't started"},
            {"value": 3, "label": "We're currently developing one"},
            {"value": 4, "label": "Yes — we have a documented policy"},
            {"value": 5, "label": "Yes — it's actively enforced and regularly reviewed"},
        ],
    },
    {
        "id": "p2",
        "dimension": "policy",
        "text": "How does your organisation handle data privacy in relation to AI tools?",
        "options": [
            {"value": 1, "label": "No specific considerations for AI"},
            {"value": 2, "label": "Basic awareness — we know it's important"},
            {"value": 3, "label": "Some guidelines exist but aren't consistently applied"},
            {"value": 4, "label": "Clear data handling rules for AI tool usage"},
            {"value": 5, "label": "Comprehensive data governance framework covering AI"},
        ],
    },
    {
        "id": "p3",
        "dimension": "policy",
        "text": "Does your organisation have processes for evaluating AI tools before adoption?",
        "options": [
            {"value": 1, "label": "No — people use whatever they find"},
            {"value": 2, "label": "Informal — some discussion before adoption"},
            {"value": 3, "label": "Basic checklist or approval process exists"},
            {"value": 4, "label": "Structured evaluation covering cost, risk, and ethics"},
            {"value": 5, "label": "Comprehensive procurement framework with ongoing review"},
        ],
    },
    # TOOLS (3 questions)
    {
        "id": "t1",
        "dimension": "tools",
        "text": "Which best describes your organisation's current use of AI tools?",
        "options": [
            {"value": 1, "label": "We don't use any AI tools"},
            {"value": 2, "label": "A few individuals use AI tools on their own"},
            {"value": 3, "label": "Some teams have adopted specific AI tools"},
            {"value": 4, "label": "AI tools are integrated into several workflows"},
            {"value": 5, "label": "AI tools are deeply embedded across the organisation"},
        ],
    },
    {
        "id": "t2",
        "dimension": "tools",
        "text": "How does your organisation approach AI tool costs and budgeting?",
        "options": [
            {"value": 1, "label": "No budget allocated for AI tools"},
            {"value": 2, "label": "Ad-hoc spending — individuals expense tools"},
            {"value": 3, "label": "Some departmental budget for AI tools"},
            {"value": 4, "label": "Dedicated AI/technology budget"},
            {"value": 5, "label": "Strategic AI investment with ROI tracking"},
        ],
    },
    # GOVERNANCE (3 questions)
    {
        "id": "g1",
        "dimension": "governance",
        "text": "Who is responsible for AI-related decisions in your organisation?",
        "options": [
            {"value": 1, "label": "Nobody — it's not defined"},
            {"value": 2, "label": "Whoever happens to be interested"},
            {"value": 3, "label": "IT department handles it"},
            {"value": 4, "label": "A designated person or small team"},
            {"value": 5, "label": "Cross-functional AI governance committee"},
        ],
    },
    {
        "id": "g2",
        "dimension": "governance",
        "text": "Does your organisation monitor the outputs and impact of AI tools in use?",
        "options": [
            {"value": 1, "label": "No monitoring at all"},
            {"value": 2, "label": "Occasional informal checks"},
            {"value": 3, "label": "Some tracking of AI tool usage"},
            {"value": 4, "label": "Regular review of AI outputs and impact"},
            {"value": 5, "label": "Systematic monitoring with feedback loops and auditing"},
        ],
    },
    {
        "id": "g3",
        "dimension": "governance",
        "text": "How does your organisation handle AI-related risks (bias, errors, security)?",
        "options": [
            {"value": 1, "label": "We haven't considered these risks"},
            {"value": 2, "label": "Aware of risks but no mitigation plan"},
            {"value": 3, "label": "Some informal risk considerations"},
            {"value": 4, "label": "Documented risk assessment for AI initiatives"},
            {"value": 5, "label": "Comprehensive AI risk management framework"},
        ],
    },
    # SKILLS (3 questions)
    {
        "id": "s1",
        "dimension": "skills",
        "text": "What AI-related training has your organisation provided to staff?",
        "options": [
            {"value": 1, "label": "None"},
            {"value": 2, "label": "Self-directed — individuals learn on their own"},
            {"value": 3, "label": "Occasional workshops or presentations"},
            {"value": 4, "label": "Structured training programme for relevant staff"},
            {"value": 5, "label": "Ongoing AI literacy programme for all staff"},
        ],
    },
    {
        "id": "s2",
        "dimension": "skills",
        "text": "How would you rate your team's ability to critically evaluate AI outputs?",
        "options": [
            {"value": 1, "label": "Cannot distinguish good from bad AI outputs"},
            {"value": 2, "label": "Limited — accept most AI outputs at face value"},
            {"value": 3, "label": "Developing — some staff can spot issues"},
            {"value": 4, "label": "Good — most staff verify and edit AI outputs"},
            {"value": 5, "label": "Excellent — strong culture of AI output verification"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Maturity levels
# ---------------------------------------------------------------------------
MATURITY_LEVELS = [
    {"name": "Beginner", "min": 1.0, "max": 1.8, "description": "Your organisation is at the very start of the AI journey. Focus on building awareness and understanding what AI can do for your sector."},
    {"name": "Developing", "min": 1.8, "max": 2.6, "description": "You've started exploring AI but lack formal structures. Prioritise creating policies and identifying key use cases."},
    {"name": "Established", "min": 2.6, "max": 3.4, "description": "You have some AI foundations in place. Focus on strengthening governance, expanding tool adoption, and training staff."},
    {"name": "Advanced", "min": 3.4, "max": 4.2, "description": "Your organisation has solid AI practices. Look to optimise, scale successful initiatives, and lead in your sector."},
    {"name": "Leading", "min": 4.2, "max": 5.1, "description": "You're among the most AI-mature organisations. Focus on innovation, sharing best practices, and continuous improvement."},
]


def calculate_scores(answers: dict) -> dict:
    """Calculate dimension scores from answers.

    Args:
        answers: {question_id: selected_value, ...}

    Returns:
        {awareness: float, policy: float, tools: float, governance: float, skills: float, overall: float}
    """
    # Build question lookup
    q_map = {q["id"]: q for q in ASSESSMENT_QUESTIONS}

    # Group scores by dimension
    dim_scores: dict[str, list[float]] = {d: [] for d in DIMENSIONS}

    for qid, value in answers.items():
        q = q_map.get(qid)
        if q:
            dim_scores[q["dimension"]].append(float(value))

    # Average per dimension
    result = {}
    for dim in DIMENSIONS:
        scores = dim_scores[dim]
        result[dim] = round(sum(scores) / len(scores), 2) if scores else 1.0

    # Overall average
    result["overall"] = round(sum(result[d] for d in DIMENSIONS) / len(DIMENSIONS), 2)
    return result


def determine_maturity_level(overall_score: float) -> dict:
    """Map overall score to a maturity level.

    Returns:
        {name: str, description: str}
    """
    for level in MATURITY_LEVELS:
        if overall_score < level["max"]:
            return {"name": level["name"], "description": level["description"]}
    return {"name": MATURITY_LEVELS[-1]["name"], "description": MATURITY_LEVELS[-1]["description"]}


def generate_recommendations(
    dimension_scores: dict,
    maturity_level: str,
    org_type: Optional[str] = None,
) -> list[str]:
    """Generate targeted recommendations using Claude.

    Returns a list of 3-5 recommendation strings.
    """
    sector_label = org_type or "general"
    dim_summary = ", ".join(f"{d}: {dimension_scores.get(d, 0)}/5" for d in DIMENSIONS)

    prompt = f"""An organisation ({sector_label} sector) completed an AI readiness assessment.
Their maturity level is: {maturity_level}
Dimension scores: {dim_summary}

Give exactly 4 specific, actionable recommendations for this organisation to improve their AI readiness.
Focus on their weakest dimensions first. Each recommendation should be 1-2 sentences.
Return ONLY the numbered recommendations, no preamble."""

    try:
        client = get_completion_client()
        text = client.complete(
            prompt=prompt,
            max_tokens=512,
            temperature=0.7,
            system="You are Grounded AI, an expert in organisational AI readiness. Give practical, sector-appropriate advice.",
        )
        # Parse numbered lines
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        recommendations = []
        for line in lines:
            # Strip leading number/bullet
            cleaned = line.lstrip("0123456789.-) ").strip()
            if cleaned:
                recommendations.append(cleaned)
        return recommendations[:5]
    except Exception as e:
        logger.warning(f"Failed to generate recommendations: {e}")
        # Fallback static recommendations based on weakest dimension
        weakest = min(DIMENSIONS, key=lambda d: dimension_scores.get(d, 5))
        return [
            f"Focus on improving your {weakest} — this is your weakest area.",
            "Consider creating a formal AI ethics policy to guide adoption.",
            "Invest in AI literacy training for your team.",
            "Establish clear governance structures for AI decision-making.",
        ]


def save_assessment(
    db: Session,
    answers: dict,
    dimension_scores: dict,
    overall_score: float,
    maturity_level: str,
    recommendations: list[str],
    user_id=None,
    organisation_type: Optional[str] = None,
) -> ReadinessAssessment:
    """Save an assessment result to the database."""
    assessment = ReadinessAssessment(
        user_id=user_id,
        organisation_type=organisation_type,
        answers=answers,
        dimension_scores=dimension_scores,
        overall_score=overall_score,
        maturity_level=maturity_level,
        recommendations=recommendations,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment
