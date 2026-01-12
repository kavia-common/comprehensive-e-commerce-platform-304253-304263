from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.session import db_healthcheck

openapi_tags = [
    {"name": "Health", "description": "Service and dependency health checks."},
]

app = FastAPI(
    title="E-Commerce Backend API",
    description="Backend service for the e-commerce platform (catalog, cart, orders, payments).",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"], summary="Service health check")
def health_check():
    """Basic health check for the backend service (no external dependencies)."""
    return {"message": "Healthy"}


@app.get("/health/db", tags=["Health"], summary="Database health check")
def health_db_check():
    """
    Check database connectivity.

    Returns a JSON payload indicating whether PostgreSQL is reachable.
    """
    ok = db_healthcheck()
    return {"database": "ok" if ok else "unreachable", "ok": ok}
