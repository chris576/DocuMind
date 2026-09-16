from pydantic import BaseModel


class ExtractRequest(BaseModel):
    """Optional trigger for a synchronous extraction batch."""

    limit: int | None = None


class ExtractResponse(BaseModel):
    processed: int
    failed: int
    pending_total: int
