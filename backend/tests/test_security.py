"""Tests for the HTTP hardening middleware (app/security.py)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.session import init_db
from app.main import app

init_db()
client = TestClient(app)


def test_security_headers_present() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    h = r.headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Referrer-Policy"] == "no-referrer"
    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["Cross-Origin-Opener-Policy"] == "same-origin"
    assert h["Server"] == "openfpa"


def test_hsts_absent_over_plain_http_by_default() -> None:
    # HSTS must not be emitted over plain HTTP unless explicitly enabled.
    assert settings.enable_hsts is False
    r = client.get("/health")
    assert "Strict-Transport-Security" not in r.headers


def test_untrusted_host_is_rejected() -> None:
    r = client.get("/health", headers={"host": "evil.example.com"})
    assert r.status_code == 400


def test_oversized_body_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_request_bytes", 16)
    r = client.post("/api/accounts", json={"account_code": "9999", "account_name": "x" * 200,
                                           "account_type": "OPEX"})
    assert r.status_code == 413
    assert r.json()["limit_bytes"] == 16


def test_rate_limiter_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    # A fresh client gives the limiter a clean per-IP bucket for this app instance.
    local = TestClient(app)
    seen_429 = False
    for _ in range(12):
        resp = local.get("/health")
        if resp.status_code == 429:
            seen_429 = True
            assert "Retry-After" in resp.headers
            break
    assert seen_429
