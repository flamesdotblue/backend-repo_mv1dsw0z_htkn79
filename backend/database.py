import os
from datetime import datetime
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "appdb")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(DATABASE_URL)
        _db = _client[DATABASE_NAME]
    return _db


async def create_document(collection_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    db = get_db()
    now = datetime.utcnow()
    payload = {**data, "created_at": now}
    result = await db[collection_name].insert_one(payload)
    payload["_id"] = result.inserted_id
    return payload


async def get_documents(collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 50):
    db = get_db()
    filter_dict = filter_dict or {}
    cursor = db[collection_name].find(filter_dict).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


def to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(doc)
    if isinstance(d.get("_id"), ObjectId):
        d["id"] = str(d.pop("_id"))
    return d
