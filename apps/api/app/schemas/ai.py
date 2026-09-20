from pydantic import BaseModel


class AIProviderHealthResponse(BaseModel):
    provider: str
    status: str
    model: str | None = None
    detail: str | None = None
