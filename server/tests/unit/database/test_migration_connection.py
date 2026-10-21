import pytest
from studio.migration_connection import migration_owner_username_matches


@pytest.mark.parametrize(
    ("username", "project_ref", "expected"),
    [
        ("migration_owner", "dwckvtuhgelhsbjyhpks", True),
        ("migration_owner.dwckvtuhgelhsbjyhpks", "dwckvtuhgelhsbjyhpks", True),
        ("migration_owner.otherprojectref", "dwckvtuhgelhsbjyhpks", False),
        ("postgres.dwckvtuhgelhsbjyhpks", "dwckvtuhgelhsbjyhpks", False),
        ("migration_owner.dwckvtuhgelhsbjyhpks", None, False),
        (None, "dwckvtuhgelhsbjyhpks", False),
    ],
)
def test_migration_owner_username_matches_project(username, project_ref, expected):
    assert migration_owner_username_matches(username, project_ref) is expected


@pytest.mark.parametrize("root_certificate", ["system", "test-ca.crt"])
def test_cloud_command_requires_verified_tls(monkeypatch, root_certificate):
    from tools import migrate_cloud

    def capture_connection(url, **kwargs):
        assert url.host == "aws-1-eu-west-1.pooler.supabase.com"
        assert url.username == "postgres.dwckvtuhgelhsbjyhpks"
        assert url.port == 5432
        assert url.query["sslmode"] == "verify-full"
        assert url.query["sslrootcert"] == root_certificate
        assert kwargs["hide_parameters"] is True
        raise RuntimeError("connection captured")

    monkeypatch.setattr("sys.argv", ["migrate_cloud", "--ssl-root-cert", root_certificate])
    monkeypatch.setattr(migrate_cloud.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(migrate_cloud.getpass, "getpass", lambda prompt: "test-only-password")
    monkeypatch.setattr(migrate_cloud, "create_engine", capture_connection)
    with pytest.raises(RuntimeError, match="connection captured"):
        migrate_cloud.main()


def test_cloud_failure_reports_sqlstate_without_private_details(monkeypatch, capsys):
    from types import SimpleNamespace

    from psycopg.errors import InsufficientPrivilege
    from sqlalchemy.exc import ProgrammingError

    from tools import migrate_cloud

    def fail_transaction():
        raise ProgrammingError("private-statement", {}, InsufficientPrivilege("private-detail"))

    monkeypatch.setattr("sys.argv", ["migrate_cloud"])
    monkeypatch.setattr(migrate_cloud.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(migrate_cloud.getpass, "getpass", lambda prompt: "test-only-password")
    monkeypatch.setattr(migrate_cloud, "create_engine", lambda *args, **kwargs: SimpleNamespace(
        begin=fail_transaction, dispose=lambda: None,
    ))
    assert migrate_cloud.main() == 1
    output = capsys.readouterr().out
    assert "42501" in output
    assert "private-statement" not in output
    assert "private-detail" not in output
    assert "test-only-password" not in output


def test_cloud_command_refuses_noninteractive_password_entry(monkeypatch, capsys):
    from tools import migrate_cloud

    monkeypatch.setattr("sys.argv", ["migrate_cloud", "--adopt-bootstrap"])
    monkeypatch.setattr(migrate_cloud.sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit) as failure:
        migrate_cloud.main()
    assert failure.value.code == 2
    assert "local interactive terminal" in capsys.readouterr().err


@pytest.mark.parametrize(("private_message", "expected"), [
    ('FATAL: password authentication failed for user "private-user"', "authentication_rejected"),
    ('connection failed: SSL error: certificate verify failed private-path', "tls_verification"),
    ('root certificate file "private-path" does not exist', "tls_verification"),
    ('SSL error: decryption failed or bad record mac private-host', "tls_connection_error"),
    ('could not translate host name "private-host" to address', "dns_resolution"),
    ('connection timeout expired private-host', "connection_timeout"),
    ('FATAL: Tenant or user not found private-user', "pooler_routing"),
    ('FATAL: Circuit breaker open: Too many authentication errors private-user', "pooler_auth_throttled"),
    ('connection refused private-host', "connection_refused"),
    ('unexpected provider detail private-secret', "unclassified_connection_error"),
])
def test_cloud_connection_failure_has_safe_actionable_reason(
    monkeypatch, capsys, private_message, expected,
):
    from types import SimpleNamespace

    from psycopg import OperationalError as PsycopgOperationalError
    from sqlalchemy.exc import OperationalError

    from tools import migrate_cloud

    def fail_connection():
        raise OperationalError("private-statement", {}, PsycopgOperationalError(private_message))

    monkeypatch.setattr("sys.argv", ["migrate_cloud", "--adopt-bootstrap", "--apply"])
    monkeypatch.setattr(migrate_cloud.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(migrate_cloud.getpass, "getpass", lambda prompt: "private-password")
    monkeypatch.setattr(migrate_cloud, "create_engine", lambda *args, **kwargs: SimpleNamespace(
        begin=fail_connection, dispose=lambda: None,
    ))
    assert migrate_cloud.main() == 1
    output = capsys.readouterr().out
    assert "phase=connect" in output
    assert f"reason={expected}" in output
    assert "private-" not in output
