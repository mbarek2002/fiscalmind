from pathlib import Path
import sys
import os
import asyncio

import pytest
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./backend/test_fiscalmind.db")

from backend.app.main import app
from backend.app.db.init_db import init_db


@pytest.fixture()
def client() -> TestClient:
	with TestClient(app) as test_client:
		yield test_client


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
	test_db_path = REPO_ROOT / "backend" / "test_fiscalmind.db"
	if test_db_path.exists():
		test_db_path.unlink()
	asyncio.run(init_db())
