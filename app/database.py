from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient

from .config import settings
from .models import Category, Priority, Status

COLLECTION_NAME = "issues"
_client: MongoClient | None = None


# Shared MongoClient connection (singleton)
def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    return _client


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db():
    return get_client()[settings.mongodb_database]


def get_issues():
    return get_db()[COLLECTION_NAME]


def _enum(cls):
    return [e.value for e in cls]


# MongoDB server-side validator: rejects documents failing schema rules (error 121)
ISSUE_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["title", "category", "description", "priority", "status",
                     "location", "status_history", "created_at", "updated_at"],
        "properties": {
            "title":       {"bsonType": "string", "minLength": 3,  "maxLength": 120},
            "category":    {"enum": _enum(Category)},
            "description": {"bsonType": "string", "minLength": 10, "maxLength": 2000},
            "priority":    {"enum": _enum(Priority)},
            "status":      {"enum": _enum(Status)},
            "location": {
                "bsonType": "object",
                "required": ["area", "city"],
                "properties": {
                    "area":      {"bsonType": "string", "minLength": 2},
                    "city":      {"bsonType": "string", "minLength": 2},
                    "latitude":  {"bsonType": ["double", "null"], "minimum": -90,  "maximum": 90},
                    "longitude": {"bsonType": ["double", "null"], "minimum": -180, "maximum": 180},
                },
            },
            "status_history": {
                "bsonType": "array",
                "minItems": 1,
                "items": {
                    "bsonType": "object",
                    "required": ["status", "changed_at"],
                    "properties": {
                        "status":     {"enum": _enum(Status)},
                        "changed_at": {"bsonType": "date"},
                        "note":       {"bsonType": ["string", "null"]},
                    },
                },
            },
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}


# Create issues collection with validator if missing, or update validator
def ensure_collection():
    db = get_db()
    if COLLECTION_NAME not in db.list_collection_names():
        db.create_collection(COLLECTION_NAME, validator=ISSUE_VALIDATOR,
                             validationLevel="strict", validationAction="error")
    else:
        db.command("collMod", COLLECTION_NAME, validator=ISSUE_VALIDATOR,
                   validationLevel="strict", validationAction="error")


# Compound indexes matching filter + sort queries, plus full-text index
def ensure_indexes():
    col = get_issues()
    col.create_index([("status",        ASCENDING), ("created_at", DESCENDING)], name="status_created_at")
    col.create_index([("category",      ASCENDING), ("created_at", DESCENDING)], name="category_created_at")
    col.create_index([("priority",      ASCENDING), ("created_at", DESCENDING)], name="priority_created_at")
    col.create_index([("location.city", ASCENDING), ("created_at", DESCENDING)], name="city_created_at")
    col.create_index([("created_at",    DESCENDING)],                             name="created_at_desc")
    col.create_index([("title", TEXT), ("description", TEXT)],
                     name="text_search", weights={"title": 3, "description": 1})
