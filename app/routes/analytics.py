from fastapi import APIRouter, Query

from ..models import Category, Priority, Status
from ..services import analytics, crud

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# Multi-facet dashboard summary
@router.get("/summary")
def summary():
    return analytics.summary()

# Counts grouped by category
@router.get("/by-category")
def by_category():
    return analytics.count_by_field("category")

# Counts grouped by status
@router.get("/by-status")
def by_status():
    return analytics.count_by_field("status")

# Counts grouped by priority
@router.get("/by-priority")
def by_priority():
    return analytics.count_by_field("priority")

# Average resolution time in hours per category
@router.get("/resolution-time")
def resolution_time():
    return analytics.resolution_time()

# Query plan inspection and performance metrics (explain)
@router.get("/explain")
def explain(
    category: Category | None = None,
    status:   Status   | None = None,
    priority: Priority | None = None,
    city:     str      | None = None,
    force_collection_scan: bool = Query(False),
):
    return analytics.explain_query(crud.build_filter(category, status, priority, city), force_collection_scan)
