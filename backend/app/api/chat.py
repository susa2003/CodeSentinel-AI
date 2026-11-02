from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from backend.app.schemas.schemas import ChatRequest, ChatResponse, SessionSummary
from backend.app.agent.orchestrator import orchestrator
from backend.app.database.repository import (
    list_sessions, get_session_messages, get_session
)

router = APIRouter(prefix="/chat", tags=["Agent Chat"])

@router.post("", response_model=ChatResponse)
async def chat_with_agent(req: ChatRequest):
    """
    Send a natural language inquiry or command to the GreenAir AI Agent.
    Orchestrates real tool calls, context management, and evidence-grounded synthesis.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="User message cannot be empty.")

    try:
        response = await orchestrator.process_message(
            message=req.message.strip(),
            session_id=req.session_id,
            active_dataset_id=req.active_dataset_id,
            latest_pollutants=req.latest_pollutants,
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent orchestration failed: {str(exc)}")

@router.get("/sessions", response_model=List[SessionSummary])
def get_sessions():
    """List all user conversation sessions."""
    sessions = list_sessions()
    result = []
    for s in sessions:
        result.append(SessionSummary(
            session_id=s["id"],
            title=s["title"],
            message_count=s.get("message_count", 0),
            created_at=s["created_at"],
            updated_at=s["updated_at"],
        ))
    return result

@router.get("/sessions/{session_id}")
def get_session_history(session_id: str):
    """Retrieve all messages and tool execution records for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session with ID '{session_id}' not found.")
    messages = get_session_messages(session_id, limit=100)
    return {
        "session": session,
        "messages": messages,
    }
