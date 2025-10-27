from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Each class corresponds to a collection: class name lowercased
class Resume(BaseModel):
    original_name: str
    content_type: str
    size: int
    data_base64: str
    created_at: Optional[datetime]


class ResumeOut(BaseModel):
    id: str = Field(..., alias="id")
    original_name: str
    content_type: str
    size: int
    created_at: Optional[datetime]

    class Config:
        allow_population_by_field_name = True


class ApplyRequest(BaseModel):
    boards: List[str]
    resume_id: str
    min_score: int = 70
    paraphrase_level: int = 1
    daily_cap: int = 10
    time_window_start: int = 9  # hour 0-23
    time_window_end: int = 18


class ApplicationPlan(BaseModel):
    resume_id: str
    board: str
    planned_time: str  # HH:MM
    match_score: int
    paraphrase_level: int
    created_at: Optional[datetime]


class ApplicationPlanOut(BaseModel):
    id: str
    resume_id: str
    board: str
    planned_time: str
    match_score: int
    paraphrase_level: int


class Submission(BaseModel):
    application_id: str
    board: str
    sent_at: datetime


class SubmissionOut(BaseModel):
    id: str
    application_id: str
    board: str
    sent_at: datetime
