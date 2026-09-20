"""Pydantic models for POST /api/chat/message.

Mirrors apps/web/src/types/chat.ts (ChatMessageRequest/ChatMessageResponse)
field-for-field via camelCase aliases so the two stay wire-compatible
without codegen — see packages/shared-types/README.md. The richer
AIResponse shape (see services/agent/schemas.py) is used internally by the
chat pipeline; this response flattens to exactly the 4 fields the Phase 3
frontend contract expects (authorization/risk/approval/missing-info are
already present inside `taskIntent`, so nothing is lost).
"""

from pydantic import BaseModel, ConfigDict, Field
from services.agent.schemas import TaskIntent, TaskPlan


class ChatMessageRequest(BaseModel):
    conversation_id: str = Field(alias="conversationId", min_length=1)
    message: str

    model_config = ConfigDict(populate_by_name=True)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    status: str


class ChatMessageResponse(BaseModel):
    message: ChatMessageOut
    task_intent: TaskIntent = Field(alias="taskIntent")
    task_plan: TaskPlan = Field(alias="taskPlan")
    status: str = "ok"

    model_config = ConfigDict(populate_by_name=True)
