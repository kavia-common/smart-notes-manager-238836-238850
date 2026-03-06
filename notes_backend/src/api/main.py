from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import auth as auth_router
from src.api.routers import notes as notes_router
from src.api.routers import tags as tags_router

openapi_tags = [
    {"name": "system", "description": "Health and system endpoints."},
    {"name": "auth", "description": "Email/password authentication (JWT Bearer tokens)."},
    {"name": "notes", "description": "Create, read, update, delete and search notes."},
    {"name": "tags", "description": "Tag management."},
]

app = FastAPI(
    title="Smart Notes Manager API",
    description=(
        "Backend API for a notes application.\n\n"
        "Authentication:\n"
        "- Register via `POST /auth/register`\n"
        "- Login via `POST /auth/login` to obtain a JWT\n"
        "- Send `Authorization: Bearer <token>` on protected endpoints\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS configuration:
# - For production, set CORS_ALLOW_ORIGINS to a comma-separated allowlist (no spaces).
import os  # noqa: E402  (keep near usage; avoids reordering in template)

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = ["*"] if cors_origins.strip() == "*" else [o for o in cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    tags=["system"],
    summary="Health check",
    description="Basic health check endpoint.",
    operation_id="health_check",
)
def health_check():
    # PUBLIC_INTERFACE
    """Health check endpoint."""
    return {"message": "Healthy"}


@app.get(
    "/docs/authentication",
    tags=["system"],
    summary="Authentication usage",
    description="Shows how to authenticate against this API using JWT Bearer tokens.",
    operation_id="docs_authentication_help",
)
def authentication_help():
    # PUBLIC_INTERFACE
    """Return API authentication instructions for clients."""
    return {
        "register": {"method": "POST", "path": "/auth/register", "body": {"email": "user@example.com", "password": "********"}},
        "login": {"method": "POST", "path": "/auth/login", "body": {"email": "user@example.com", "password": "********"}},
        "use_token": {"header": "Authorization", "value": "Bearer <access_token>"},
    }


app.include_router(auth_router.router)
app.include_router(notes_router.router)
app.include_router(tags_router.router)
