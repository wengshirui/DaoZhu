"""Chat history session routes."""

from fastapi import APIRouter

router = APIRouter()


def _get_chat_db():
    """Get or create the chat history DB singleton."""
    if not hasattr(_get_chat_db, "_instance"):
        from accobot.db.chat_history import ChatHistoryDB
        _get_chat_db._instance = ChatHistoryDB()
    return _get_chat_db._instance


@router.get("/api/chat/sessions")
async def list_chat_sessions():
    """List recent chat sessions."""
    db = _get_chat_db()
    sessions = db.list_sessions()
    return {"sessions": sessions}


@router.post("/api/chat/sessions")
async def create_chat_session(request: dict = None):
    """Create a new chat session."""
    db = _get_chat_db()
    title = (request or {}).get("title", "新对话")
    session = db.create_session(title=title)
    return {"success": True, "session": session}


@router.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str):
    """Get messages for a chat session."""
    db = _get_chat_db()
    messages = db.get_messages(session_id)
    return {"messages": messages}


@router.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    db = _get_chat_db()
    db.delete_session(session_id)
    return {"success": True}


@router.post("/api/chat/sessions/{session_id}/messages")
async def add_chat_message(session_id: str, request: dict):
    """Add a message to a chat session."""
    db = _get_chat_db()
    role = request.get("role", "user")
    content = request.get("content", "")
    msg_id = db.add_message(session_id, role, content)
    return {"success": True, "message_id": msg_id}


@router.patch("/api/chat/sessions/{session_id}")
async def update_chat_session(session_id: str, request: dict):
    """Update a chat session (e.g., title)."""
    db = _get_chat_db()
    title = request.get("title")
    if title:
        db.update_session_title(session_id, title)
    return {"success": True}
