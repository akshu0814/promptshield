"""
Tests for custom rules API and scanning.
Run with: cd api && pytest tests/test_custom_rules.py -v
"""
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_custom_rules.db"
os.environ["API_SECRET_KEY"] = ""

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, get_db
from main import app

TEST_DB_URL = "sqlite:///./test_custom_rules.db"
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


VALID_RULE = {
    "name": "Block test phrase",
    "category": "prompt_injection",
    "severity": "high",
    "pattern": "do not test me",
    "description": "Blocks a test phrase",
}


class TestCreateRule:
    def test_create_returns_201(self, client):
        res = client.post("/rules", json=VALID_RULE)
        assert res.status_code == 201

    def test_create_returns_rule_id(self, client):
        res = client.post("/rules", json=VALID_RULE)
        data = res.json()
        assert "rule_id" in data
        assert data["rule_id"].startswith("CST-")

    def test_source_is_custom(self, client):
        res = client.post("/rules", json=VALID_RULE)
        assert res.json()["source"] == "custom"

    def test_enabled_by_default(self, client):
        res = client.post("/rules", json=VALID_RULE)
        assert res.json()["enabled"] is True

    def test_invalid_category_rejected(self, client):
        rule = {**VALID_RULE, "category": "bad_category"}
        res = client.post("/rules", json=rule)
        assert res.status_code == 422

    def test_invalid_severity_rejected(self, client):
        rule = {**VALID_RULE, "severity": "super_critical"}
        res = client.post("/rules", json=rule)
        assert res.status_code == 422

    def test_invalid_regex_rejected(self, client):
        rule = {**VALID_RULE, "pattern": "[unclosed"}
        res = client.post("/rules", json=rule)
        assert res.status_code == 422

    def test_empty_name_rejected(self, client):
        rule = {**VALID_RULE, "name": ""}
        res = client.post("/rules", json=rule)
        assert res.status_code == 422


class TestListRules:
    def test_yaml_rules_always_present(self, client):
        res = client.get("/rules")
        assert res.status_code == 200
        yaml_rules = [r for r in res.json() if r["source"] == "yaml"]
        assert len(yaml_rules) >= 26

    def test_custom_rule_appears_in_list(self, client):
        client.post("/rules", json=VALID_RULE)
        res = client.get("/rules")
        custom = [r for r in res.json() if r["source"] == "custom"]
        assert len(custom) == 1

    def test_source_field_present(self, client):
        res = client.get("/rules")
        for rule in res.json():
            assert "source" in rule


class TestToggleRule:
    def test_disable_rule(self, client):
        created = client.post("/rules", json=VALID_RULE).json()
        res = client.patch(f"/rules/{created['rule_id']}", json={"enabled": False})
        assert res.status_code == 200
        assert res.json()["enabled"] is False

    def test_re_enable_rule(self, client):
        created = client.post("/rules", json=VALID_RULE).json()
        client.patch(f"/rules/{created['rule_id']}", json={"enabled": False})
        res = client.patch(f"/rules/{created['rule_id']}", json={"enabled": True})
        assert res.json()["enabled"] is True

    def test_toggle_yaml_rule_returns_404(self, client):
        res = client.patch("/rules/INJ001", json={"enabled": False})
        assert res.status_code == 404

    def test_toggle_nonexistent_returns_404(self, client):
        res = client.patch("/rules/CST-DOESNOTEXIST", json={"enabled": False})
        assert res.status_code == 404


class TestDeleteRule:
    def test_delete_returns_204(self, client):
        created = client.post("/rules", json=VALID_RULE).json()
        res = client.delete(f"/rules/{created['rule_id']}")
        assert res.status_code == 204

    def test_deleted_rule_not_in_list(self, client):
        created = client.post("/rules", json=VALID_RULE).json()
        client.delete(f"/rules/{created['rule_id']}")
        res = client.get("/rules")
        custom = [r for r in res.json() if r["source"] == "custom"]
        assert len(custom) == 0

    def test_delete_yaml_rule_returns_404(self, client):
        res = client.delete("/rules/INJ001")
        assert res.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        res = client.delete("/rules/CST-DOESNOTEXIST")
        assert res.status_code == 404


class TestCustomRuleScanning:
    def test_custom_rule_blocks_matching_prompt(self, client):
        client.post("/rules", json={**VALID_RULE, "pattern": "xyzzy-secret-phrase"})
        res = client.post("/scan", json={"prompt": "please xyzzy-secret-phrase now"})
        assert res.status_code == 200
        assert res.json()["verdict"] == "BLOCK"

    def test_disabled_custom_rule_does_not_block(self, client):
        created = client.post("/rules", json={**VALID_RULE, "pattern": "xyzzy-secret-phrase"}).json()
        client.patch(f"/rules/{created['rule_id']}", json={"enabled": False})
        res = client.post("/scan", json={"prompt": "please xyzzy-secret-phrase now"})
        assert res.json()["verdict"] == "ALLOW"

    def test_deleted_custom_rule_does_not_block(self, client):
        created = client.post("/rules", json={**VALID_RULE, "pattern": "xyzzy-secret-phrase"}).json()
        client.delete(f"/rules/{created['rule_id']}")
        res = client.post("/scan", json={"prompt": "please xyzzy-secret-phrase now"})
        assert res.json()["verdict"] == "ALLOW"
