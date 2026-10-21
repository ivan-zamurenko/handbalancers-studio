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