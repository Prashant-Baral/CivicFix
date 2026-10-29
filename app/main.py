from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .database import close_client, ensure_collection, ensure_indexes, get_client
from .routes import analytics, issues
from .services.crud import InvalidIssueId, InvalidTransition, IssueNotFound


# Run collection validator and index creation on startup, clean up on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_collection()
    ensure_indexes()
    yield
    close_client()


app = FastAPI(
    title="CivicFix",
    description=(
        "Crowdsourced civic issue reporting and resolution tracking system. "
        "CSE494 MongoDB mini-project supporting SDG 11 (Sustainable Cities and Communities)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Register route modules
app.include_router(issues.router)
app.include_router(analytics.router)


# Custom exception handlers for clean HTTP responses
@app.exception_handler(IssueNotFound)
async def _not_found(_: Request, exc: IssueNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(InvalidIssueId)
async def _bad_id(_: Request, exc: InvalidIssueId):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(InvalidTransition)
async def _bad_transition(_: Request, exc: InvalidTransition):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# Health check: verifies FastAPI and MongoDB connectivity
@app.get("/health")
def health():
    get_client().admin.command("ping")
    return {"status": "ok", "database": "connected"}
