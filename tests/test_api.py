"""
API-layer tests: the approval gate and email dispatch outcomes.

The mailer is monkeypatched — no SMTP server, no network. What's under
test is the contract: approval always succeeds and the dispatch outcome
(sent / skipped / failed) is always stated on the record.
"""

import pytest
from fastapi.testclient import TestClient

from auralis import mailer
from auralis.api.app import app
from auralis.models import CustomerProfile, EmailStatus, FollowUpEmail
from auralis.store import db

CUSTOMER = CustomerProfile(
    name="Laura Chen", company="TechNova", role="Ops Lead", email="laura@technova.io"
)
FOLLOWUP = FollowUpEmail(
    email_subject="Great talking today",
    email_body="Hi Laura...",
    receiver_email="laura@technova.io",
)


@pytest.fixture(autouse=True)
def fresh_db():
    db.reset_for_tests(":memory:")
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _call_with_draft() -> str:
    call_id = db.create_call("Rep: hello... Laura: we need help with visibility.", CUSTOMER)
    db.save_result(call_id, "followup_json", FOLLOWUP)
    return call_id


def test_approve_without_mailer_is_skipped_not_silent(client, monkeypatch):
    monkeypatch.setattr(mailer, "is_configured", lambda: False)
    call_id = _call_with_draft()

    resp = client.post(f"/calls/{call_id}/approve-followup")

    assert resp.status_code == 200
    assert resp.json()["email_status"] == "skipped"
    record = db.get_call(call_id)
    assert record.followup_approved is True
    assert record.email_status == EmailStatus.SKIPPED


def test_approve_with_mailer_sends_the_draft(client, monkeypatch):
    sent = {}

    def fake_send(followup):
        sent["to"] = followup.receiver_email
        sent["subject"] = followup.email_subject

    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(mailer, "send_followup", fake_send)
    call_id = _call_with_draft()

    resp = client.post(f"/calls/{call_id}/approve-followup")

    assert resp.status_code == 200
    assert resp.json()["email_status"] == "sent"
    assert sent == {"to": "laura@technova.io", "subject": "Great talking today"}
    assert db.get_call(call_id).email_status == EmailStatus.SENT


def test_smtp_failure_is_stated_but_approval_stands(client, monkeypatch):
    def broken_send(followup):
        raise RuntimeError("SMTP AUTH rejected")

    monkeypatch.setattr(mailer, "is_configured", lambda: True)
    monkeypatch.setattr(mailer, "send_followup", broken_send)
    call_id = _call_with_draft()

    resp = client.post(f"/calls/{call_id}/approve-followup")

    assert resp.status_code == 200
    body = resp.json()
    assert body["email_status"] == "failed"
    assert body["followup_approved"] is True
    record = db.get_call(call_id)
    assert record.followup_approved is True          # the human's decision stands
    assert record.email_status == EmailStatus.FAILED  # the failure is loud


def test_approve_without_draft_is_409(client):
    call_id = db.create_call("Rep: hello... Laura: we need help with visibility.", CUSTOMER)
    resp = client.post(f"/calls/{call_id}/approve-followup")
    assert resp.status_code == 409


def test_ui_page_serves(client):
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "Auralis" in resp.text


def test_basic_auth_locks_everything_but_health(client):
    from auralis.config import get_settings

    settings = get_settings()
    settings.basic_auth = "demo:s3cret"
    try:
        assert client.get("/calls").status_code == 401
        assert client.get("/ui").status_code == 401
        assert client.get("/health").status_code == 200  # platform health checks
        assert client.get("/calls", auth=("demo", "s3cret")).status_code == 200
        assert client.get("/calls", auth=("demo", "wrong")).status_code == 401
    finally:
        settings.basic_auth = ""
