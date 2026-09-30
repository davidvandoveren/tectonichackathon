"""Hardening against the classes of issue a code audit (Aikido) looks for: resource exhaustion,
ReDoS, spoofed client IPs, unbounded per-customer state and business-rule bypasses."""

import logging
import time
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import Settings
from app.domain.bank import Bank, TransferError, TransferRequest
from app.domain.seed import seed_bank
from app.kate.context import CustomerContext
from app.kate.llm import ChatTurn, MockChat
from app.main import create_app
from app.security.body_limit import DEFAULT_MAX_BODY_BYTES
from app.security.client_ip import client_ip
from app.security.sessions import MAX_SESSIONS_PER_USER, SessionStore
from app.skills.holdings import MAX_GOALS
from app.skills.registry import default_registry
from app.skills.service import (
    MAX_ACTIVITY,
    MAX_KEPT_PROPOSALS,
    MAX_OPEN_PROPOSALS,
    NotEligibleError,
    SkillsService,
)
from tests.conftest import DEMO_PASSWORD

TODAY = date(2026, 9, 30)


# --- request size ------------------------------------------------------------------------------
def test_oversized_body_is_refused_before_parsing(client: TestClient) -> None:
    body = b'{"username": "' + b"a" * DEFAULT_MAX_BODY_BYTES + b'", "password": "x"}'
    response = client.post(
        "/api/v1/auth/login", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413


def test_oversized_chunked_body_without_content_length_is_refused(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        yield b'{"username": "'
        for _ in range(10):
            yield b"a" * (DEFAULT_MAX_BODY_BYTES // 8)
        yield b'", "password": "x"}'

    response = client.post(
        "/api/v1/auth/login", content=chunks(), headers={"content-type": "application/json"}
    )
    assert response.status_code in (400, 413)  # refused mid-stream, see security/body_limit.py


def test_speech_upload_may_be_larger_than_the_default(emma: TestClient) -> None:
    body = b'{"audio_base64": "' + b"A" * (DEFAULT_MAX_BODY_BYTES * 2) + b'", "mime_type": "x"}'
    response = emma.post(
        "/api/v1/kate/transcribe", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code != 413


# --- client IP / login rate limiting -----------------------------------------------------------
def _request(peer: str, forwarded_for: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_client_ip_trusts_only_what_the_proxy_appended() -> None:
    spoofed = _request("10.0.0.1", "6.6.6.6, 203.0.113.7")
    assert client_ip(spoofed, trusted_proxy_hops=1) == "203.0.113.7"
    assert client_ip(spoofed, trusted_proxy_hops=0) == "10.0.0.1"
    assert client_ip(_request("10.0.0.1", None), trusted_proxy_hops=1) == "10.0.0.1"


def test_login_limiter_cannot_be_dodged_with_a_fake_forwarded_for(settings: Settings) -> None:
    behind_proxy = settings.model_copy(update={"trusted_proxy_hops": 1})
    with TestClient(create_app(behind_proxy)) as client:
        for i in range(settings.login_max_failures):
            client.post(
                "/api/v1/auth/login",
                json={"username": f"ghost{i}", "password": "wrong-pass"},
                headers={"x-forwarded-for": f"198.51.100.{i}, 203.0.113.7"},
            )
        blocked = client.post(
            "/api/v1/auth/login",
            json={"username": "emma", "password": DEMO_PASSWORD},
            headers={"x-forwarded-for": "192.0.2.99, 203.0.113.7"},
        )
    assert blocked.status_code == 429


def test_failed_login_is_logged_without_password_or_log_injection(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="kbc_poc.security"):
        client.post("/api/v1/auth/login", json={"username": "ev\nil", "password": "s3cret-attempt"})
    messages = [r.getMessage() for r in caplog.records if r.name == "kbc_poc.security"]
    assert messages
    assert all("\n" not in m and "s3cret-attempt" not in m for m in messages)


# --- sessions ----------------------------------------------------------------------------------
def test_sessions_per_user_are_capped_oldest_first() -> None:
    store = SessionStore(ttl_seconds=3600)
    other = store.create("u_jan")
    tokens = [store.create("u_emma") for _ in range(MAX_SESSIONS_PER_USER + 1)]
    assert store.resolve(tokens[0]) is None
    assert store.resolve(tokens[-1]) == "u_emma"
    assert store.resolve(other) == "u_jan"


# --- ReDoS -------------------------------------------------------------------------------------
def test_mock_chat_is_linear_on_hostile_whitespace() -> None:
    context = CustomerContext("Emma", "p", TODAY, [], {}, [])
    hostile = "stuur" + " " * 994 + "x"
    started = time.perf_counter()
    MockChat().complete("", [ChatTurn("user", hostile)], context)
    assert time.perf_counter() - started < 0.25


# --- business rules at the domain layer --------------------------------------------------------
@pytest.fixture
def bank() -> Bank:
    bank = Bank()
    seed_bank(bank, "pw", TODAY)
    return bank


@pytest.mark.parametrize("amount", ["0", "-5.00", "10000.01", "1.005", "NaN"])
def test_bank_rejects_invalid_amounts_from_any_caller(bank: Bank, amount: str) -> None:
    source = next(a for a in bank.accounts_for("u_emma") if a.type == "current")
    before = source.balance
    request = TransferRequest(source.id, "BE68539007547034", "X", Decimal(amount), "")
    with pytest.raises(TransferError):
        bank.transfer("u_emma", request, TODAY)
    assert source.balance == before


# --- unbounded per-customer state --------------------------------------------------------------
def test_unknown_moment_type_cannot_be_dismissed(emma: TestClient) -> None:
    response = emma.post("/api/v1/kate/feed/" + "x" * 50 + "/dismiss", json={})
    assert response.status_code == 404


@pytest.fixture
def service(bank: Bank) -> SkillsService:
    return SkillsService(bank, default_registry())


def _propose_call(service: SkillsService, n: int) -> str:
    return service.propose(
        "u_emma", "advisor.book_call", {"topic": f"vraag {n}"}, "ui", "test", TODAY
    ).id


def test_open_proposals_are_capped(service: SkillsService) -> None:
    for n in range(MAX_OPEN_PROPOSALS):
        _propose_call(service, n)
    with pytest.raises(NotEligibleError):
        _propose_call(service, MAX_OPEN_PROPOSALS)


def test_finished_proposals_and_activity_do_not_grow_without_bound(
    service: SkillsService,
) -> None:
    for n in range(MAX_KEPT_PROPOSALS + 30):
        service.decline("u_emma", _propose_call(service, n))
    assert len(service.proposals("u_emma")) <= MAX_KEPT_PROPOSALS
    assert len(service.activity("u_emma")) <= MAX_ACTIVITY


def test_savings_goals_are_capped(service: SkillsService) -> None:
    params = {"name": "Reis", "target": "500.00"}
    for _ in range(MAX_GOALS):
        proposal = service.propose("u_emma", "savings.create_goal", params, "ui", "t", TODAY)
        service.approve("u_emma", proposal.id, TODAY)
    with pytest.raises(NotEligibleError):
        service.propose("u_emma", "savings.create_goal", params, "ui", "t", TODAY)


# --- disclosure --------------------------------------------------------------------------------
def test_security_txt_and_noindex(client: TestClient) -> None:
    response = client.get("/.well-known/security.txt")
    assert response.status_code == 200
    assert "Contact:" in response.text and "Expires:" in response.text
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


# --- static files ------------------------------------------------------------------------------
@pytest.fixture
def spa_client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    (tmp_path / "index.html").write_text("<!doctype html><title>spa</title>")
    (tmp_path / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    settings.static_dir = tmp_path
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "path", ["/.env", "/.git/config", "/.git/HEAD", "/.htaccess", "/.svn/entries", "/a/.env"]
)
def test_dotfiles_are_not_served_as_the_spa(spa_client: TestClient, path: str) -> None:
    # The SPA fallback used to answer 200 + index.html, which scanners report as an exposed file.
    response = spa_client.get(path)
    assert response.status_code == 404
    assert "spa" not in response.text


def test_spa_routes_and_files_still_work(spa_client: TestClient) -> None:
    assert spa_client.get("/privacy").status_code == 200
    assert spa_client.get("/robots.txt").text.startswith("User-agent")
    assert spa_client.get("/.well-known/security.txt").status_code == 200


def test_head_is_allowed_on_the_spa(spa_client: TestClient) -> None:
    assert spa_client.head("/").status_code == 200
