"""Registration creates an account only after a one-use, browser-bound verification."""

from datetime import timedelta

from sqlalchemy import func, select

from studio.authentication import hash_password, verify_password
from studio.models import EmailVerification, User, utcnow
from tests.conftest import csrf_headers

REGISTRATION = {
    "first_name": "Іван",
    "last_name": "Тест",
    "email": "ivan@example.org",
    "password": "unique-long-test-password",
}


def pending_registration(client, monkeypatch):
    captured = []
    monkeypatch.setattr(
        "studio.authentication.send_verification",
        lambda settings, recipient, code: captured.append(code),
    )
    headers = csrf_headers(client)
    result = client.post("/api/auth/register", json=REGISTRATION, headers=headers)
    assert result.status_code == 200
    assert result.json() == {"verification_required": True}
    return headers, captured[0]


def test_password_hash_is_salted_and_verifies():
    encoded = hash_password("a sufficiently long password")
    assert encoded != hash_password("a sufficiently long password")
    assert verify_password("a sufficiently long password", encoded)
    assert not verify_password("wrong password", encoded)
    assert not verify_password("anything", "invalid")


def test_account_requires_code_and_rotates_session(client, db_factory, monkeypatch, answers):
    headers = csrf_headers(client)
    client.post("/api/onboarding", json=answers, headers=headers)
    headers, code = pending_registration(client, monkeypatch)
    old_cookie = client.cookies.get("studio_session")
    with db_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        pending = db.scalar(select(EmailVerification))
        assert pending.code_hash != code
        assert REGISTRATION["password"] not in pending.password_hash
    result = client.post("/api/auth/verify", json={"code": code}, headers=headers)
    assert result.status_code == 200
    assert client.cookies.get("studio_session") != old_cookie
    state = client.get("/api/session").json()
    assert state["user"]["name"] == "Іван Тест"
    assert state["onboarding"]["minutes"] == answers["minutes"]
    assert (
        client.post(
            "/api/auth/verify", json={"code": code}, headers=csrf_headers(client)
        ).status_code
        == 400
    )


def test_verification_attempt_budget_and_expiry(client, monkeypatch, db_factory):
    headers, code = pending_registration(client, monkeypatch)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert (
            client.post("/api/auth/verify", json={"code": wrong}, headers=headers).status_code
            == 400
        )
    assert client.post("/api/auth/verify", json={"code": code}, headers=headers).status_code == 400
    with db_factory() as db:
        pending = db.scalar(select(EmailVerification))
        pending.attempts = 0
        pending.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post("/api/auth/verify", json={"code": code}, headers=headers).status_code == 400


def test_profile_and_login(client, monkeypatch):
    headers, code = pending_registration(client, monkeypatch)
    assert client.post("/api/auth/verify", json={"code": code}, headers=headers).status_code == 200
    headers = csrf_headers(client)
    result = client.patch(
        "/api/profile", json={"first_name": "Олег", "last_name": "Тест"}, headers=headers
    )
    assert result.status_code == 200
    assert result.json()["email"] == REGISTRATION["email"]
    assert result.json()["name"] == "Олег Тест"
    client.cookies.clear()
    headers = csrf_headers(client)
    invalid = {"email": REGISTRATION["email"], "password": "a wrong long password"}
    assert client.post("/api/auth/login", json=invalid, headers=headers).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={key: REGISTRATION[key] for key in ("email", "password")},
            headers=headers,
        ).status_code
        == 200
    )


def test_csrf_and_browser_binding(client, monkeypatch):
    headers, code = pending_registration(client, monkeypatch)
    assert client.post("/api/auth/verify", json={"code": code}).status_code == 403
    client.cookies.clear()
    assert (
        client.post(
            "/api/auth/verify", json={"code": code}, headers=csrf_headers(client)
        ).status_code
        == 400
    )
    assert (
        client.patch(
            "/api/profile",
            json={"first_name": "Олег", "last_name": "Тест"},
            headers=csrf_headers(client),
        ).status_code
        == 401
    )


def test_registration_rate_limit(client, monkeypatch):
    monkeypatch.setattr("studio.authentication.send_verification", lambda *args: None)
    headers = csrf_headers(client)
    for _ in range(5):
        assert (
            client.post("/api/auth/register", json=REGISTRATION, headers=headers).status_code == 200
        )
    assert client.post("/api/auth/register", json=REGISTRATION, headers=headers).status_code == 429


def test_delivery_unavailable_creates_no_account(client, db_factory, monkeypatch):
    from studio.mailer import MailUnavailable

    def unavailable(*args):
        raise MailUnavailable()

    monkeypatch.setattr("studio.authentication.send_verification", unavailable)
    result = client.post("/api/auth/register", json=REGISTRATION, headers=csrf_headers(client))
    assert result.status_code == 503
    with db_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(EmailVerification)) == 0


def test_private_mail_delivery(settings, tmp_path, monkeypatch):
    from studio.mailer import send_verification

    monkeypatch.setattr("studio.mailer.SERVER_DIR", tmp_path / "server")
    send_verification(settings, "recipient@example.org", "123456")
    files = list((tmp_path / ".local-tools/mail-inbox").glob("*.eml"))
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    assert files[0].parent.stat().st_mode & 0o777 == 0o700


def test_password_whitespace_is_preserved():
    from studio.schemas import EmailRegistration

    body = EmailRegistration(**{**REGISTRATION, "password": "  deliberate spaces  "})
    assert body.password == "  deliberate spaces  "
    assert "deliberate" not in repr(body)


def test_parallel_code_reuse_creates_only_one_account(client, monkeypatch, db_factory):
    from concurrent.futures import ThreadPoolExecutor

    headers, code = pending_registration(client, monkeypatch)
    cookie = client.cookies.get("studio_session")

    def confirm():
        return client.post(
            "/api/auth/verify",
            json={"code": code},
            headers={**headers, "Cookie": f"studio_session={cookie}"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: confirm(), range(2)))
    assert results.count(200) == 1
    assert all(status in {200, 400, 403} for status in results)
    with db_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
