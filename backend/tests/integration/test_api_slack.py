import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.services.auth import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_admin = False
    user.is_active = True
    user.slack_webhook_url = None
    return user


@pytest.fixture
def mock_user_with_slack():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "slack@example.com"
    user.is_admin = False
    user.is_active = True
    user.slack_webhook_url = "https://hooks.slack.com/services/T12345678/B12345678/abcdefghijklmnop"
    return user


@pytest.fixture
def auth_headers(mock_user):
    access_token = create_access_token(mock_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def slack_auth_headers(mock_user_with_slack):
    access_token = create_access_token(mock_user_with_slack.id)
    return {"Authorization": f"Bearer {access_token}"}


class TestGetSlackStatus:
    def test_get_status_unauthorized(self, client):
        response = client.get("/api/v1/settings/slack")
        assert response.status_code == 401


class TestSaveSlackWebhook:
    def test_save_webhook_unauthorized(self, client):
        response = client.post(
            "/api/v1/settings/slack",
            json={"webhook_url": "https://hooks.slack.com/services/T12345678/B12345678/abc"},
        )
        assert response.status_code == 401


class TestTestSlackWebhook:
    def test_test_webhook_unauthorized(self, client):
        response = client.post("/api/v1/settings/slack/test")
        assert response.status_code == 401


class TestDeleteSlackWebhook:
    def test_delete_webhook_unauthorized(self, client):
        response = client.delete("/api/v1/settings/slack")
        assert response.status_code == 401
