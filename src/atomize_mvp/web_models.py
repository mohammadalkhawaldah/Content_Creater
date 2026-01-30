from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    client: str
    title: str
    created_at: str


class JobStatusResponse(BaseModel):
    id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    client: str
    title: str
    created_at: str
    current_step: Optional[str] = None
    percent: int = 0
    error: Optional[str] = None
    job_path: str


class JobResultsResponse(BaseModel):
    id: str
    client: str
    title: str
    job_path: str
    drafts: dict = Field(default_factory=dict)
    posters: dict = Field(default_factory=dict)
    docs: list[dict] = Field(default_factory=list)
    cards: list[dict] = Field(default_factory=list)
    manifest: Optional[dict] = None
