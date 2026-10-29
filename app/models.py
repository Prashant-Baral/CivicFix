from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# Enums for restricted choices
class Category(str, Enum):
    pothole         = "pothole"
    garbage         = "garbage"
    streetlight     = "streetlight"
    water_supply    = "water_supply"
    drainage        = "drainage"
    public_facility = "public_facility"
    other           = "other"


class Priority(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"
    urgent = "urgent"


class Status(str, Enum):
    submitted   = "submitted"
    in_progress = "in_progress"
    resolved    = "resolved"


class SortOrder(str, Enum):
    newest = "newest"
    oldest = "oldest"


# Embedded location object
class Location(BaseModel):
    area:      str          = Field(min_length=2, max_length=100)
    city:      str          = Field(min_length=2, max_length=100)
    latitude:  float | None = Field(default=None, ge=-90,  le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


# Request schemas
class IssueCreate(BaseModel):
    title:       str      = Field(min_length=3,  max_length=120)
    category:    Category
    description: str      = Field(min_length=10, max_length=2000)
    priority:    Priority = Priority.medium
    location:    Location


class IssueUpdate(BaseModel):
    title:       str | None      = Field(default=None, min_length=3,  max_length=120)
    category:    Category | None = None
    description: str | None      = Field(default=None, min_length=10, max_length=2000)
    priority:    Priority | None = None
    location:    Location | None = None


class StatusChange(BaseModel):
    status: Status
    note:   str | None = Field(default=None, max_length=500)


# Response schemas
class StatusHistoryEntry(BaseModel):
    status:     Status
    changed_at: datetime
    note:       str | None = None


class IssueOut(BaseModel):
    id:             str
    title:          str
    category:       Category
    description:    str
    priority:       Priority
    status:         Status
    location:       Location
    status_history: list[StatusHistoryEntry]
    created_at:     datetime
    updated_at:     datetime


class IssueList(BaseModel):
    items:       list[IssueOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
