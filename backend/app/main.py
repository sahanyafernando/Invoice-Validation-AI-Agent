from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db import Base, engine
from app import models  # noqa: F401 - registers SQLAlchemy models
from app.api import router

# For a hackathon-sized app this keeps setup simple. The included Supabase SQL
# can also be run manually if you prefer explicit schema creation.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Explainable invoice-to-PO validation API with Supabase support",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    database = "supabase-postgresql" if "supabase" in settings.database_url else (
        "postgresql" if settings.database_url.startswith("postgresql") else "sqlite"
    )
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "database": database,
        "storage_provider": settings.storage_provider,
    }
