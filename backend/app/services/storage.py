"""Storage abstraction for original invoice files.

The application uses a private Supabase bucket in normal cloud mode. A local
provider is kept for offline development and tests. The database stores only an
opaque storage reference, never a public URL.
"""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import mimetypes

from app.core.config import settings


def _extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if ext in {".pdf", ".png", ".jpg", ".jpeg"} else ".bin"


def _new_object_name(filename: str) -> str:
    now = datetime.now(timezone.utc)
    return f"{now:%Y/%m/%d}/{uuid4().hex}{_extension(filename)}"


def _supabase_client():
    settings.validate_supabase_storage()
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "Supabase storage selected but the 'supabase' Python package is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc
    return create_client(settings.supabase_url, settings.supabase_server_key)


def save_file(filename: str, content: bytes) -> str:
    provider = settings.storage_provider.lower().strip()
    object_name = _new_object_name(filename)

    if provider == "supabase":
        client = _supabase_client()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        client.storage.from_(settings.supabase_storage_bucket).upload(
            path=object_name,
            file=content,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )
        return f"supabase://{settings.supabase_storage_bucket}/{object_name}"

    upload_dir = Path(settings.upload_dir)
    local_path = upload_dir / object_name
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)
    return f"local://{object_name}"


def read_file(reference: str) -> bytes:
    if reference.startswith("supabase://"):
        rest = reference.removeprefix("supabase://")
        bucket, object_name = rest.split("/", 1)
        client = _supabase_client()
        return client.storage.from_(bucket).download(object_name)

    object_name = reference.removeprefix("local://")
    path = Path(settings.upload_dir) / object_name
    if not path.exists():
        raise FileNotFoundError("Stored invoice file was not found")
    return path.read_bytes()


def delete_file(reference: str) -> None:
    if not reference:
        return
    try:
        if reference.startswith("supabase://"):
            rest = reference.removeprefix("supabase://")
            bucket, object_name = rest.split("/", 1)
            _supabase_client().storage.from_(bucket).remove([object_name])
            return

        object_name = reference.removeprefix("local://")
        (Path(settings.upload_dir) / object_name).unlink(missing_ok=True)
    except Exception:
        # Cleanup must never hide the original processing error.
        pass
