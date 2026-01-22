"""Toolkit chat UI routes."""
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import UUID

from app.db import get_db
from app.models.auth import User
from app.models.toolkit import ChatLog, Feedback
from app.dependencies import require_auth_page
from app.services.rag import rag_answer


router = APIRouter(prefix="/toolkit", tags=["toolkit"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def toolkit_page(
    request: Request,
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db)
):
    """Toolkit chat page (requires authentication)."""

    # Get user's recent chat logs
    recent_logs = (
        db.query(ChatLog)
        .filter(ChatLog.user_id == user.id)
        .order_by(ChatLog.created_at.desc())
        .limit(10)
        .all()
    )

    # Attach feedback to each log if exists
    for log in recent_logs:
        feedback = db.query(Feedback).filter(
            Feedback.chat_log_id == log.id
        ).first()
        log.feedback = feedback

    return templates.TemplateResponse(
        "toolkit/chat.html",
        {
            "request": request,
            "user": user,
            "recent_logs": recent_logs
        }
    )


@router.post("/ask", response_class=HTMLResponse)
async def ask_question(
    request: Request,
    query: str = Form(...),
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db)
):
    """
    Handle chat question with HTMX.

    Returns HTML fragment with the new Q&A.
    """

    # Generate answer using RAG
    result = rag_answer(
        db=db,
        query=query,
        user_id=str(user.id)  # Pass user_id for logging
    )

    # Get the chat log that was just created
    chat_log = (
        db.query(ChatLog)
        .filter(ChatLog.user_id == user.id)
        .order_by(ChatLog.created_at.desc())
        .first()
    )

    # Build HTML response
    html = f"""
    <div class="bg-white rounded-lg shadow">
        <!-- Question -->
        <div class="p-4 border-b border-gray-200">
            <div class="text-sm font-medium text-gray-500 mb-1">You asked:</div>
            <div class="text-gray-900">{query}</div>
            <div class="text-xs text-gray-500 mt-1">Just now</div>
        </div>

        <!-- Answer -->
        <div class="p-4">
            <div class="text-sm font-medium text-gray-700 mb-2">Answer:</div>
            <div class="text-gray-900 whitespace-pre-wrap">{result['answer']}</div>
    """

    # Add citations if present
    if result['citations']:
        html += """
            <div class="mt-4">
                <div class="text-sm font-medium text-gray-700 mb-2">Sources:</div>
                <div class="space-y-2">
        """
        for citation in result['citations']:
            heading = citation.get('heading') or 'Section'
            score = citation.get('similarity_score', 0)
            snippet = citation.get('snippet', '')
            html += f"""
                    <div class="text-sm border-l-2 border-blue-500 pl-3 py-1">
                        <div class="font-medium text-gray-900">
                            {heading}
                            <span class="text-xs text-gray-500">(similarity: {score:.2f})</span>
                        </div>
                        <div class="text-gray-600 text-xs mt-1">{snippet}</div>
                    </div>
            """
        html += """
                </div>
            </div>
        """

    # Add feedback form
    if not result['refusal']:
        html += f"""
            <div class="mt-4 pt-4 border-t border-gray-200">
                <form
                    hx-post="/toolkit/feedback/{chat_log.id}"
                    hx-target="#feedback-{chat_log.id}"
                    class="space-y-3"
                >
                    <div class="text-sm font-medium text-gray-700">Rate this answer:</div>

                    <!-- Rating -->
                    <div class="flex space-x-2">
        """
        for i in range(1, 6):
            html += f"""
                        <label class="flex items-center">
                            <input type="radio" name="rating" value="{i}" required class="mr-1">
                            <span class="text-sm">{i}</span>
                        </label>
            """
        html += """
                    </div>

                    <!-- Issue Type -->
                    <div>
                        <select name="issue_type" class="text-sm border border-gray-300 rounded px-2 py-1">
                            <option value="">No issues</option>
                            <option value="hallucination">Hallucination</option>
                            <option value="irrelevant">Irrelevant</option>
                            <option value="too_vague">Too vague</option>
                            <option value="security_concern">Security concern</option>
                            <option value="cost_concern">Cost concern</option>
                            <option value="other">Other</option>
                        </select>
                    </div>

                    <!-- Comment -->
                    <div>
                        <textarea
                            name="comment"
                            rows="2"
                            placeholder="Optional comment..."
                            class="w-full text-sm border border-gray-300 rounded px-2 py-1"
                        ></textarea>
                    </div>

                    <button
                        type="submit"
                        class="text-sm bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700"
                    >
                        Submit Feedback
                    </button>
                </form>
        """
        html += f"""
                <div id="feedback-{chat_log.id}"></div>
            </div>
        """

    html += """
        </div>
    </div>
    """

    return HTMLResponse(content=html)


@router.post("/feedback/{chat_log_id}", response_class=HTMLResponse)
async def submit_feedback(
    chat_log_id: str,
    rating: int = Form(...),
    issue_type: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a chat response.

    Returns HTML fragment confirming submission.
    """

    # Verify chat log belongs to user
    chat_log = db.query(ChatLog).filter(
        ChatLog.id == chat_log_id,
        ChatLog.user_id == user.id
    ).first()

    if not chat_log:
        raise HTTPException(status_code=404, detail="Chat log not found")

    # Check if feedback already exists
    existing = db.query(Feedback).filter(
        Feedback.chat_log_id == chat_log_id
    ).first()

    if existing:
        return HTMLResponse(
            content='<div class="text-sm text-red-600">Feedback already submitted</div>'
        )

    # Create feedback
    feedback = Feedback(
        chat_log_id=chat_log_id,
        user_id=user.id,
        rating=rating,
        issue_type=issue_type if issue_type else None,
        comment=comment if comment else None
    )

    db.add(feedback)
    db.commit()

    return HTMLResponse(
        content=f'<div class="text-sm text-green-600">✓ Feedback submitted (Rating: {rating}/5)</div>'
    )


@router.post("/ask-about", response_class=HTMLResponse)
async def ask_about_section(
    request: Request,
    question: str = Form(...),
    context: str = Form(...),
    full_text: str = Form(None),
    user: User = Depends(require_auth_page),
    db: Session = Depends(get_db)
):
    """
    Ask a question about a specific section from browse.

    Combines the user's question with section context for better answers.
    Redirects to toolkit page with the answer.
    """
    # Build query that includes context
    enhanced_query = f"{question}\n\n[Context: {context}]"

    # Generate answer
    result = rag_answer(
        db=db,
        query=enhanced_query,
        user_id=str(user.id)
    )

    # Redirect back to toolkit page where the answer will appear
    return RedirectResponse(url="/toolkit", status_code=303)
