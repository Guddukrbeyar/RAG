from typing import List, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    document: str
    page: Optional[int] = None
    section: Optional[str] = None
    snippet: str
    score: float


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000
    )


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=80
    )
    password: str = Field(
        min_length=1,
        max_length=120
    )


class LoginResponse(BaseModel):
    token: str
    username: str


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    sources: List[Source] = Field(default_factory=list)
    clarification: Optional[str] = None


class DocumentInfo(BaseModel):
    name: str
    chunks: int
