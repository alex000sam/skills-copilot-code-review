"""
Announcements endpoints - CRUD for announcements and public read of active ones
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from datetime import date
import uuid

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "text": doc.get("text"),
        "start_date": doc.get("start_date"),
        "expiration_date": doc.get("expiration_date"),
        "created_by": doc.get("created_by")
    }


@router.get("", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Return announcements that are currently active (not expired and started)."""
    today = date.today().isoformat()

    # expiration_date >= today
    # and (start_date <= today or start_date not set)
    query = {
        "expiration_date": {"$gte": today},
        "$or": [
            {"start_date": {"$lte": today}},
            {"start_date": None},
            {"start_date": {"$exists": False}}
        ]
    }

    results = []
    for doc in announcements_collection.find(query).sort("expiration_date", 1):
        results.append(_serialize(doc))

    return results


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements() -> List[Dict[str, Any]]:
    """Return all announcements (for management UI)."""
    results = []
    for doc in announcements_collection.find().sort("expiration_date", 1):
        results.append(_serialize(doc))
    return results


@router.post("", response_model=Dict[str, Any])
def create_announcement(payload: Dict[str, Any] = Body(...), teacher_username: Optional[str] = None) -> Dict[str, Any]:
    """Create a new announcement. Requires teacher_username to manage."""
    # Auth check
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required to create announcements")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    text = payload.get("text")
    expiration_date = payload.get("expiration_date")
    start_date = payload.get("start_date")

    # Basic validation: expiration_date required
    if not expiration_date:
        raise HTTPException(status_code=400, detail="expiration_date is required")

    new_doc = {
        "_id": str(uuid.uuid4()),
        "text": text,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": teacher_username
    }

    announcements_collection.insert_one(new_doc)

    return _serialize(new_doc)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(announcement_id: str, payload: Dict[str, Any] = Body(...), teacher_username: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing announcement. Requires teacher_username."""
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required to update announcements")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    doc = announcements_collection.find_one({"_id": announcement_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Announcement not found")

    update_fields = {}
    text = payload.get("text")
    start_date = payload.get("start_date")
    expiration_date = payload.get("expiration_date")

    if text is not None:
        update_fields["text"] = text
    if start_date is not None:
        update_fields["start_date"] = start_date
    if expiration_date is not None:
        update_fields["expiration_date"] = expiration_date

    if not update_fields:
        raise HTTPException(status_code=400, detail="No update fields provided")

    announcements_collection.update_one({"_id": announcement_id}, {"$set": update_fields})
    updated = announcements_collection.find_one({"_id": announcement_id})
    return _serialize(updated)


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, teacher_username: Optional[str] = None) -> Dict[str, Any]:
    """Delete an announcement. Requires teacher_username."""
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required to delete announcements")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
