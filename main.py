import os
import base64
import random
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Resume, Application, ApplyRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "AutoApply Backend Running"}

@app.get("/test")
def test_database():
    status = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
    }
    try:
        if db is not None:
            status["database"] = "✅ Connected"
            status["database_url"] = "✅ Set"
            status["database_name"] = db.name
    except Exception as e:
        status["database"] = f"❌ Error: {e}"
    return status

# -------- Resume Upload & Retrieval --------
@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # No artificial size cap here; allow large payloads as infra permits
    resume_doc = Resume(
        original_name=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        data_b64=base64.b64encode(content).decode("utf-8"),
    )
    resume_id = create_document("resume", resume_doc)
    return {"id": resume_id, "original_name": resume_doc.original_name, "content_type": resume_doc.content_type, "size": resume_doc.size}

@app.get("/resume")
def list_resumes():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = get_documents("resume")
    out = []
    for d in docs:
        out.append({
            "id": str(d.get("_id")),
            "original_name": d.get("original_name"),
            "content_type": d.get("content_type"),
            "size": d.get("size"),
            "created_at": d.get("created_at"),
        })
    return out

@app.get("/resume/{resume_id}")
def download_resume(resume_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        doc = db["resume"].find_one({"_id": ObjectId(resume_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume id")
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    data = base64.b64decode(doc.get("data_b64") or b"")
    return StreamingResponse(iter([data]), media_type=doc.get("content_type") or "application/octet-stream", headers={"Content-Disposition": f"attachment; filename={doc.get('original_name', 'resume')}"})

# -------- Application Planning / Sending (simulated) --------
@app.post("/apply/plan")
def plan_applications(req: ApplyRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    # Validate resume exists
    try:
        _ = db["resume"].find_one({"_id": ObjectId(req.resume_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume id")

    planned: List[dict] = []
    cap = max(1, min((req.daily_cap or 10), 100))
    window_start = req.time_window_start or 9
    window_end = req.time_window_end or 19
    for i, board in enumerate(req.boards[:cap]):
        hour = random.randint(window_start, max(window_start, window_end))
        minute = random.randint(0, 59)
        app_doc = Application(
            board=board,
            job_title=None,
            company=None,
            resume_id=req.resume_id,
            match_score=max(0, min(req.min_score or 70, 100)),
            paraphrase_level=req.paraphrase_level or 50,
            planned_time=f"{hour:02d}:{minute:02d}",
            status="planned",
        )
        app_id = create_document("application", app_doc)
        planned.append({"id": app_id, **app_doc.model_dump()})
    return planned

class SendRequest(BaseModel):
    application_ids: List[str]

@app.post("/apply/send")
def send_applications(req: SendRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    sent = []
    for app_id in req.application_ids:
        try:
            doc = db["application"].find_one({"_id": ObjectId(app_id)})
            if not doc:
                continue
            record = {
                "application_id": app_id,
                "board": doc.get("board"),
                "resume_id": doc.get("resume_id"),
                "status": "sent",
                "sent_at": datetime.utcnow(),
            }
            new_id = create_document("submission", record)
            sent.append({"submission_id": new_id, **record})
        except Exception:
            continue
    return sent

@app.get("/apply/sent")
def list_sent():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = get_documents("submission")
    return [{
        "id": str(d.get("_id")),
        "application_id": d.get("application_id"),
        "board": d.get("board"),
        "resume_id": d.get("resume_id"),
        "status": d.get("status"),
        "sent_at": d.get("sent_at"),
    } for d in docs]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
