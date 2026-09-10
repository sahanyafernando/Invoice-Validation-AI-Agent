from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Invoice Validation AI Agent"
    api_prefix: str = "/api/v1"

    # Database: local SQLite is the zero-credential fallback. For the normal
    # hackathon setup, put a Supabase PostgreSQL URL in DATABASE_URL.
    database_url: str = "sqlite:///./invoice_ai.db"

    # File storage: local keeps development/tests simple; "supabase" stores
    # original invoices in a private Supabase Storage bucket.
    storage_provider: str = "local"
    supabase_url: str = ""
    # Current Supabase server key. Legacy service_role is accepted as a fallback.
    supabase_secret_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "invoices"
    upload_dir: str = str(PROJECT_ROOT / "uploads")

    # AI: mock works without credentials. OpenAI uses structured extraction
    # plus AI-generated exception explanations.
    llm_provider: str = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"

    max_upload_mb: int = 12
    cors_origins: str = "http://localhost:3000"
    price_tolerance_percent: float = 0.0
    quantity_tolerance_percent: float = 0.0
    auto_approve_max_risk: int = 19

    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        # Supabase shows postgresql:// URLs. Explicitly select psycopg v3,
        # which is the driver installed by this project.
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


    @property
    def supabase_server_key(self) -> str:
        return self.supabase_secret_key or self.supabase_service_role_key

    def validate_supabase_storage(self) -> None:
        if self.storage_provider.lower() != "supabase":
            return
        missing = []
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not (self.supabase_secret_key or self.supabase_service_role_key):
            missing.append("SUPABASE_SECRET_KEY")
        if missing:
            raise RuntimeError(
                "STORAGE_PROVIDER=supabase requires: " + ", ".join(missing)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
