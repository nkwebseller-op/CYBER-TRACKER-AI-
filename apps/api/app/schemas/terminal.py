"""Pydantic contracts for the Terminal Engine API.

Deliberately narrow: a client can request a *session* and request that a
*reviewed action type* run in it — it can never hand the server raw argv
or an authorization verdict. See app/api/routes/terminal.py for how each
field is used and re-validated server-side.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from services.terminal.models import CommandStatus, SessionStatus
from services.terminal.platform_types import PlatformIdentifier


class CreateSessionRequest(BaseModel):
    task_id: str | None = Field(default=None, alias="taskId")
    working_directory: str | None = Field(default=None, alias="workingDirectory")

    model_config = ConfigDict(populate_by_name=True)


class SessionResponse(BaseModel):
    id: UUID
    platform: PlatformIdentifier
    status: SessionStatus
    created_at: datetime = Field(alias="createdAt")
    last_activity_at: datetime = Field(alias="lastActivityAt")
    working_directory: str | None = Field(default=None, alias="workingDirectory")
    task_id: str | None = Field(default=None, alias="taskId")

    model_config = ConfigDict(populate_by_name=True)


class ExecuteRequest(BaseModel):
    """`action_type` is looked up in a server-side, reviewed template
    registry (services/terminal/command_templates.py) — it is never raw
    command text, and the client cannot supply argv directly."""

    session_id: UUID = Field(alias="sessionId")
    task_id: str = Field(alias="taskId")
    target_id: UUID = Field(alias="targetId")
    action_type: str = Field(alias="actionType")
    approved: bool = False
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")

    model_config = ConfigDict(populate_by_name=True)


class CommandResultResponse(BaseModel):
    command_id: UUID = Field(alias="commandId")
    session_id: UUID = Field(alias="sessionId")
    status: CommandStatus
    platform: PlatformIdentifier
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")
    exit_code: int | None = Field(default=None, alias="exitCode")
    stdout: str | None = None
    stderr: str | None = None
    stdout_truncated: bool = Field(default=False, alias="stdoutTruncated")
    stderr_truncated: bool = Field(default=False, alias="stderrTruncated")
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(populate_by_name=True)
