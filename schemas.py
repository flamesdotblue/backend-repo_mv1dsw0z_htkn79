"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user"
- Resume -> "resume"
- Application -> "application"
"""
from typing import Optional, List
from pydantic import BaseModel, Field

class Resume(BaseModel):
    """Stored resumes uploaded by users
    Collection: "resume"
    """
    original_name: str = Field(..., description="Original file name provided by the user")
    content_type: str = Field(..., description="MIME type of the uploaded file")
    size: int = Field(..., ge=1, description="File size in bytes")
    data_b64: str = Field(..., description="Base64-encoded file bytes")

class Application(BaseModel):
    """Planned or sent job applications
    Collection: "application"
    """
    board: str = Field(..., description="Target job board, e.g., LinkedIn, Naukri")
    job_title: Optional[str] = Field(None, description="Job title if known")
    company: Optional[str] = Field(None, description="Company name if known")
    resume_id: str = Field(..., description="Reference to the resume document ID")
    match_score: Optional[int] = Field(None, ge=0, le=100, description="Match score for this job")
    paraphrase_level: Optional[int] = Field(50, ge=0, le=100, description="Degree of paraphrasing to humanize text")
    planned_time: Optional[str] = Field(None, description="Local time planned for sending, e.g., 14:35")
    status: str = Field('planned', description="Status: planned | sent | failed")

class ApplyRequest(BaseModel):
    boards: List[str] = Field(..., description="Boards to apply to")
    resume_id: str = Field(..., description="Uploaded resume ID to attach")
    min_score: Optional[int] = Field(0, ge=0, le=100)
    paraphrase_level: Optional[int] = Field(50, ge=0, le=100)
    daily_cap: Optional[int] = Field(10, ge=1, le=100)
    time_window_start: Optional[int] = Field(9, ge=0, le=23)
    time_window_end: Optional[int] = Field(19, ge=0, le=23)
