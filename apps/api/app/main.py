from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 - registers ORM models with SQLAlchemy metadata
from app.db import Base, engine
from app.routers.auth import router as auth_router
from app.routers.projects import router as projects_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Convenient for the starter app. Use Alembic migrations for production deployments.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ClipView API",
    version="0.3.0",
    description="API foundation for the ClipView video clipping platform.",
    lifespan=lifespan,
)

# Restrict this list to the deployed frontend origins before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(projects_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "clipview-api", "version": "0.3.0"}
