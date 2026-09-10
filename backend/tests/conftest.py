import os, shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_invoice_ai.db"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["UPLOAD_DIR"] = "./test_uploads"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    shutil.rmtree("test_uploads", ignore_errors=True)
    yield
    Base.metadata.drop_all(bind=engine)
    shutil.rmtree("test_uploads", ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    engine.dispose()
    Path("test_invoice_ai.db").unlink(missing_ok=True)


@pytest.fixture
def client():
    return TestClient(app)
