"""Quick environment diagnostics. Run from the project root after activating backend/.venv."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text
from app.core.config import settings
from app.db import engine

print("Invoice Validation AI Agent - setup check")
print("database URL configured:", bool(settings.database_url))
print("storage provider:", settings.storage_provider)
print("LLM provider:", settings.llm_provider)

try:
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    print("[OK] Database connection")
except Exception as exc:
    print("[FAIL] Database connection:", exc)

if settings.storage_provider.lower() == "supabase":
    try:
        settings.validate_supabase_storage()
        from app.services.storage import _supabase_client
        client = _supabase_client()
        client.storage.get_bucket(settings.supabase_storage_bucket)
        print("[OK] Supabase Storage bucket")
    except Exception as exc:
        print("[FAIL] Supabase Storage:", exc)
else:
    print("[OK] Local storage fallback")

if settings.llm_provider.lower() == "openai":
    print("[OK] OpenAI key present" if settings.openai_api_key else "[FAIL] OPENAI_API_KEY is empty")
else:
    print("[OK] Mock LLM mode (no API key required)")
