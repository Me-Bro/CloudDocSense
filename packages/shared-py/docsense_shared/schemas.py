from pydantic import BaseModel


class Citation(BaseModel):
    source: str
    page: int | None = None
    chunk_id: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool
    workspace_id: str
