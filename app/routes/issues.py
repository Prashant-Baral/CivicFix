from fastapi import APIRouter, HTTPException, Query, Response
from fastapi import status as http_status

from ..models import Category, IssueCreate, IssueList, IssueOut, IssueUpdate, Priority, SortOrder, Status, StatusChange
from ..services import crud

router = APIRouter(prefix="/issues", tags=["Issues"])


# Create a new civic report
@router.post("", response_model=IssueOut, status_code=201)
def create_issue(payload: IssueCreate):
    return crud.create_issue(payload)


# List issues with optional filters, search, and pagination
@router.get("", response_model=IssueList)
def list_issues(
    category:  Category | None = None,
    status:    Status   | None = None,
    priority:  Priority | None = None,
    city:      str      | None = Query(None),
    q:         str      | None = Query(None, min_length=2),
    sort:      SortOrder       = SortOrder.newest,
    page:      int             = Query(1,  ge=1),
    page_size: int             = Query(10, ge=1, le=100),
):
    return crud.list_issues(crud.build_filter(category, status, priority, city, q), sort, page, page_size)


# Retrieve a single issue by ID
@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(issue_id: str):
    return crud.get_issue(issue_id)


# Partial update of issue details
@router.patch("/{issue_id}", response_model=IssueOut)
def update_issue(issue_id: str, payload: IssueUpdate):
    if not any(v is not None for v in payload.model_dump(exclude_unset=True).values()):
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    return crud.update_issue(issue_id, payload)


# Advance lifecycle status (submitted -> in_progress -> resolved)
@router.patch("/{issue_id}/status", response_model=IssueOut)
def change_status(issue_id: str, payload: StatusChange):
    return crud.change_status(issue_id, payload.status.value, payload.note)


# Delete an issue permanently
@router.delete("/{issue_id}", status_code=204)
def delete_issue(issue_id: str):
    crud.delete_issue(issue_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
