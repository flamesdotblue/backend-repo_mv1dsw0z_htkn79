import base64
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

from database import get_db, create_document, get_documents, to_str_id
from schemas import (
    ResumeOut,
    ApplyRequest,
    ApplicationPlan,
    ApplicationPlanOut,
    Submission,
    SubmissionOut,
)

app = FastAPI(title="AutoApply Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
async def test():
    # Ensure DB accessible by listing collections
    db = get_db()
    cols = await db.list_collection_names()
    return {"ok": True, "collections": cols}


@app.post("/resume/upload", response_model=ResumeOut)
async def upload_resume(file: UploadFile = File(...)):
    try:
        content = await file.read()  # no artificial limit here
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    encoded = base64.b64encode(content).decode("utf-8")
    doc = await create_document(
        "resume",
        {
            "original_name": file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "size": len(content),
            "data_base64": encoded,
        },
    )
    out = {
        "id": str(doc["_id"]),
        "original_name": doc["original_name"],
        "content_type": doc["content_type"],
        "size": doc["size"],
        "created_at": doc.get("created_at"),
    }
    return out


@app.get("/resume", response_model=List[ResumeOut])
async def list_resumes():
    docs = await get_documents("resume", {}, limit=500)
    items = []
    for d in docs:
        d = to_str_id(d)
        items.append(
            {
                "id": d["id"],
                "original_name": d["original_name"],
                "content_type": d.get("content_type", "application/octet-stream"),
                "size": d.get("size", 0),
                "created_at": d.get("created_at"),
            }
        )
    return items


@app.get("/resume/{resume_id}")
async def download_resume(resume_id: str):
    db = get_db()
    try:
        _id = ObjectId(resume_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume id")

    doc = await db["resume"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    raw = base64.b64decode(doc["data_base64"]) if doc.get("data_base64") else b""
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        iter([raw]),
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename={doc.get('original_name', 'resume')}"
        },
    )


@app.post("/apply/plan", response_model=List[ApplicationPlanOut])
async def plan_apply(req: ApplyRequest):
    # Basic scheduler: one application per selected board within the time window
    start = max(0, min(23, req.time_window_start))
    end = max(start + 1, min(23, req.time_window_end))
    window_hours = list(range(start, end + 1))

    plans: List[ApplicationPlanOut] = []
    created_ids: List[str] = []
    db = get_db()

    cap = max(1, min(100, req.daily_cap))
    count = 0
    for b in req.boards:
        if count >= cap:
            break
        hour = window_hours[count % len(window_hours)]
        planned_time = f"{hour:02d}:{0:02d}"
        payload = ApplicationPlan(
            resume_id=req.resume_id,
            board=b,
            planned_time=planned_time,
            match_score=req.min_score,
            paraphrase_level=req.paraphrase_level,
        ).dict()
        doc = await create_document("applicationplan", payload)
        created_ids.append(str(doc["_id"]))
        plans.append(
            ApplicationPlanOut(
                id=str(doc["_id"]),
                resume_id=req.resume_id,
                board=b,
                planned_time=planned_time,
                match_score=req.min_score,
                paraphrase_level=req.paraphrase_level,
            )
        )
        count += 1

    return plans


@app.post("/apply/send", response_model=List[SubmissionOut])
async def apply_send(application_ids: dict):
    ids = application_ids.get("application_ids") or []
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="application_ids must be a list")

    db = get_db()
    out: List[SubmissionOut] = []
    for sid in ids:
        try:
            oid = ObjectId(sid)
        except Exception:
            # skip invalid ids
            continue
        plan = await db["applicationplan"].find_one({"_id": oid})
        if not plan:
            continue
        sub = Submission(
            application_id=str(oid),
            board=plan.get("board", "unknown"),
            sent_at=datetime.utcnow(),
        ).dict()
        doc = await create_document("submission", sub)
        out.append(
            SubmissionOut(
                id=str(doc["_id"]),
                application_id=sub["application_id"],
                board=sub["board"],
                sent_at=sub["sent_at"],
            )
        )
    return out


@app.get("/apply/sent", response_model=List[SubmissionOut])
async def list_sent():
    docs = await get_documents("submission", {}, limit=1000)
    out: List[SubmissionOut] = []
    for d in docs:
        d = to_str_id(d)
        out.append(
            SubmissionOut(
                id=d["id"],
                application_id=d.get("application_id", ""),
                board=d.get("board", ""),
                sent_at=d.get("sent_at", datetime.utcnow()),
            )
        )
    return out
