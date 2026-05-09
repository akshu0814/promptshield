"""
Tests for analytics and app management routes.
Run with: cd api && pytest tests/ -v
"""
import os
import sys
from pathlib import Path

# Must set these before any app imports — both are read at module level
TEST_DB_URL = "sqlite:///./test_analytics.db"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["API_SECRET_KEY"] = ""  # disable auth in tests

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, get_db
from main import app

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ── Analytics ──────────────────────────────────────────────────────────────

class TestTimeseries:
    def test_empty_returns_empty_buckets(self, client):
        res = client.get("/stats/timeseries?hours=24")
        assert res.status_code == 200
        data = res.json()
        assert data["hours"] == 24
        assert data["buckets"] == []

    def test_default_hours_is_24(self, client):
        res = client.get("/stats/timeseries")
        assert res.status_code == 200
        assert res.json()["hours"] == 24

    def test_hours_param_max_168(self, client):
        res = client.get("/stats/timeseries?hours=168")
        assert res.status_code == 200

    def test_hours_param_too_large(self, client):
        res = client.get("/stats/timeseries?hours=999")
        assert res.status_code == 422

    def test_hours_param_zero(self, client):
        res = client.get("/stats/timeseries?hours=0")
        assert res.status_code == 422


class TestBreakdown:
    def test_empty_db_returns_zeros(self, client):
        res = client.get("/stats/breakdown")
        assert res.status_code == 200
        data = res.json()
        assert data["total_blocked"] == 0
        assert data["by_category"] == {}
        assert data["by_severity"] == {}

    def test_response_shape(self, client):
        res = client.get("/stats/breakdown")
        data = res.json()
        assert "by_category" in data
        assert "by_severity" in data
        assert "total_blocked" in data


# ── App Management ──────────────────────────────────────────────────────────

class TestCreateApp:
    def test_create_returns_201(self, client):
        res = client.post("/apps", json={"name": "my-bot"})
        assert res.status_code == 201

    def test_create_returns_api_key(self, client):
        res = client.post("/apps", json={"name": "my-bot"})
        data = res.json()
        assert "api_key" in data
        assert len(data["api_key"]) > 10

    def test_create_returns_app_id(self, client):
        res = client.post("/apps", json={"name": "my-bot"})
        data = res.json()
        assert "app_id" in data

    def test_block_mode_default_true(self, client):
        res = client.post("/apps", json={"name": "my-bot"})
        assert res.json()["block_mode"] is True

    def test_block_mode_false(self, client):
        res = client.post("/apps", json={"name": "monitor-bot", "block_mode": False})
        assert res.json()["block_mode"] is False

    def test_empty_name_rejected(self, client):
        res = client.post("/apps", json={"name": ""})
        assert res.status_code == 422


class TestListApps:
    def test_empty_list(self, client):
        res = client.get("/apps")
        assert res.status_code == 200
        assert res.json() == []

    def test_created_app_appears_in_list(self, client):
        client.post("/apps", json={"name": "bot-a"})
        res = client.get("/apps")
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "bot-a"

    def test_multiple_apps(self, client):
        client.post("/apps", json={"name": "bot-a"})
        client.post("/apps", json={"name": "bot-b"})
        res = client.get("/apps")
        assert len(res.json()) == 2

    def test_list_includes_total_scans(self, client):
        client.post("/apps", json={"name": "bot-a"})
        res = client.get("/apps")
        assert "total_scans" in res.json()[0]


class TestGetApp:
    def test_get_existing_app(self, client):
        created = client.post("/apps", json={"name": "bot-x"}).json()
        res = client.get(f"/apps/{created['app_id']}")
        assert res.status_code == 200
        assert res.json()["name"] == "bot-x"

    def test_get_nonexistent_returns_404(self, client):
        res = client.get("/apps/nonexistent-id")
        assert res.status_code == 404


class TestDeleteApp:
    def test_delete_returns_204(self, client):
        created = client.post("/apps", json={"name": "temp-bot"}).json()
        res = client.delete(f"/apps/{created['app_id']}")
        assert res.status_code == 204

    def test_deleted_app_not_in_list(self, client):
        created = client.post("/apps", json={"name": "temp-bot"}).json()
        client.delete(f"/apps/{created['app_id']}")
        res = client.get("/apps")
        assert res.json() == []

    def test_delete_nonexistent_returns_404(self, client):
        res = client.delete("/apps/nonexistent-id")
        assert res.status_code == 404
