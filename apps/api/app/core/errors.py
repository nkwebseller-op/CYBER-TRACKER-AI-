"""Application-wide error hierarchy and FastAPI exception handlers.

Every raised domain error maps to a stable error code + HTTP status, so the
frontend can branch on `error.code` instead of parsing message strings.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class CyberAIError(Exception):
    """Base class for all domain errors raised by the application."""

    code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(CyberAIError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND


class ValidationFailedError(CyberAIError):
    code = "validation_failed"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class PolicyDeniedError(CyberAIError):
    """Raised when the Policy Engine denies an action outright."""

    code = "policy_denied"
    status_code = status.HTTP_403_FORBIDDEN


class ApprovalRequiredError(CyberAIError):
    """Raised when an action is valid but is queued pending human approval."""

    code = "approval_required"
    status_code = status.HTTP_202_ACCEPTED


class OutOfScopeError(CyberAIError):
    """Raised when a target/action falls outside any authorized scope."""

    code = "out_of_scope"
    status_code = status.HTTP_403_FORBIDDEN


async def cyberai_error_handler(_: Request, exc: CyberAIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
