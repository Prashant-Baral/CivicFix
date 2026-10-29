import math
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from ..database import get_issues
from ..models import IssueCreate, IssueUpdate, SortOrder


# Custom error types
class IssueNotFound(Exception):
    pass

class InvalidIssueId(Exception):
    pass

class InvalidTransition(Exception):
    def __init__(self, current: str, requested: str):
        allowed = sorted(ALLOWED_TRANSITIONS.get(current, set())) or ["none"]
        super().__init__(f"Cannot move from '{current}' to '{requested}'. Allowed: {', '.join(allowed)}.")


# Forward-only status workflow: submitted -> in_progress -> resolved
ALLOWED_TRANSITIONS = {
    "submitted":   {"in_progress"},
    "in_progress": {"resolved"},
    "resolved":    set(),
}


def _now():
    return datetime.now(timezone.utc)

# Convert string ID to MongoDB BSON ObjectId
def _oid(issue_id):
    try:
        return ObjectId(issue_id)
    except (InvalidId, TypeError):
        raise InvalidIssueId(f"'{issue_id}' is not a valid issue id.")

# Convert BSON _id to string id for JSON response
def serialize(doc):
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    return out


# Insert new issue with initial status_history entry
def create_issue(data: IssueCreate):
    now = _now()
    doc = data.model_dump(mode="json")
    doc["status"] = "submitted"
    doc["status_history"] = [{"status": "submitted", "changed_at": now, "note": "Report created"}]
    doc["created_at"] = now
    doc["updated_at"] = now
    result = get_issues().insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


# Retrieve single issue by ObjectId
def get_issue(issue_id):
    doc = get_issues().find_one({"_id": _oid(issue_id)})
    if doc is None:
        raise IssueNotFound(f"Issue '{issue_id}' not found.")
    return serialize(doc)


# Build MongoDB query filter dict from optional parameters
def build_filter(category=None, status=None, priority=None, city=None, q=None):
    f = {}
    if category: f["category"]      = category.value
    if status:   f["status"]        = status.value
    if priority: f["priority"]      = priority.value
    if city:     f["location.city"] = city
    if q:        f["$text"]         = {"$search": q}
    return f


# Paginated list query with sorting
def list_issues(filter_dict, sort, page, page_size):
    col = get_issues()
    direction = DESCENDING if sort == SortOrder.newest else ASCENDING
    total = col.count_documents(filter_dict)
    cursor = col.find(filter_dict).sort([("created_at", direction), ("_id", direction)]).skip((page - 1) * page_size).limit(page_size)
    return {
        "items":       [serialize(d) for d in cursor],
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


# Partial update of issue fields using $set
def update_issue(issue_id, data: IssueUpdate):
    changes = {k: v for k, v in data.model_dump(mode="json", exclude_unset=True).items() if v is not None}
    changes["updated_at"] = _now()
    doc = get_issues().find_one_and_update({"_id": _oid(issue_id)}, {"$set": changes}, return_document=ReturnDocument.AFTER)
    if doc is None:
        raise IssueNotFound(f"Issue '{issue_id}' not found.")
    return serialize(doc)


# Atomic status change: validates current status in filter and appends to history in one query
def change_status(issue_id, new_status, note):
    now = _now()
    allowed_from = [s for s, nxt in ALLOWED_TRANSITIONS.items() if new_status in nxt]
    doc = get_issues().find_one_and_update(
        {"_id": _oid(issue_id), "status": {"$in": allowed_from}},
        {
            "$set":  {"status": new_status, "updated_at": now},
            "$push": {"status_history": {"status": new_status, "changed_at": now, "note": note or f"Status changed to {new_status}"}},
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc is not None:
        return serialize(doc)
    existing = get_issues().find_one({"_id": _oid(issue_id)}, {"status": 1})
    if existing is None:
        raise IssueNotFound(f"Issue '{issue_id}' not found.")
    raise InvalidTransition(existing["status"], new_status)


# Remove issue by ObjectId
def delete_issue(issue_id):
    result = get_issues().delete_one({"_id": _oid(issue_id)})
    if result.deleted_count == 0:
        raise IssueNotFound(f"Issue '{issue_id}' not found.")
