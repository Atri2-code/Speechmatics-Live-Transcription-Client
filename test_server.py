"""Unit tests for FastAPI REST endpoints — no live WebSocket connections."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

import src.python.server as srv
from src.python.session import SessionState


@pytest.fixture(autouse=True)
def reset_session():
    srv.session = __import__("src.python.session", fromlist=["Session"]).Session()
    srv.streaming_task = None
    yield


@pytest.fixture()
def client():
    return TestClient(srv.app)


def test_session_status_idle(client):
    res = client.get("/session/status")
    assert res.status_code == 200
    assert res.json()["state"] == "IDLE"


def test_start_session(client):
    with patch("src.python.server.asyncio.create_task", return_value=AsyncMock()):
        res = client.post("/session/start?language=en")
    assert res.status_code == 200
    assert res.json()["status"] == "started"
    assert srv.session.state == SessionState.ACTIVE


def test_start_session_conflict(client):
    with patch("src.python.server.asyncio.create_task", return_value=AsyncMock()):
        client.post("/session/start?language=en")
        res = client.post("/session/start?language=fr")
    assert res.status_code == 409


def test_stop_without_active_session(client):
    res = client.post("/session/stop")
    assert res.status_code == 409


def test_stop_active_session(client):
    with patch("src.python.server.asyncio.create_task", return_value=AsyncMock()):
        client.post("/session/start?language=en")
    res = client.post("/session/stop")
    assert res.status_code == 200
    assert res.json()["status"] == "stopped"


def test_export_empty_transcript(client):
    res = client.get("/transcript/export?fmt=text")
    assert res.status_code == 200
    assert res.json()["transcript"] == ""


def test_export_json_format(client):
    res = client.get("/transcript/export?fmt=json")
    assert res.status_code == 200
    data = res.json()
    assert "transcript" in data
    assert "analytics" in data
    assert isinstance(data["transcript"], list)
