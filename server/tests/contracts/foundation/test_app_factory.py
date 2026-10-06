"""The initial HTTP application must work without any external service."""

import importlib.util
import subprocess
import sys
import textwrap


def factory():
    assert importlib.util.find_spec("studio.main") is not None, "App factory is not implemented"
    from studio.main import create_app

    return create_app


def test_liveness_without_database(test_settings, monkeypatch):
    create_app = factory()
    from fastapi.testclient import TestClient

    def deny_network(*args, **kwargs):
        raise AssertionError("Liveness attempted a network/database connection")

    monkeypatch.setattr("socket.socket.connect", deny_network)
    monkeypatch.setattr("socket.socket.connect_ex", deny_network)
    monkeypatch.setattr("socket.getaddrinfo", deny_network)
    with TestClient(create_app(test_settings)) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["content-type"] == "application/json"


def test_isolated_app_instances(test_settings):
    create_app = factory()
    from fastapi.testclient import TestClient

    first = create_app(test_settings)
    second = create_app(test_settings)
    assert first is not second
    first.state.settings["app_env"] = "changed"
    first.state.only_first = []
    assert second.state.settings == {"app_env": "test"}
    assert test_settings == {"app_env": "test"}
    assert not hasattr(second.state, "only_first")
    first.dependency_overrides[object()] = lambda: None
    assert second.dependency_overrides == {}
    first.add_api_route("/only-first", lambda: {"only": "first"})
    with TestClient(first) as first_client, TestClient(second) as second_client:
        assert first_client.get("/only-first").status_code == 200
        assert second_client.get("/only-first").status_code == 404
        assert second_client.get("/health/live").json() == {"status": "ok"}


def test_no_startup_network(tmp_path):
    factory()
    # A fresh process proves import-time behavior, not a cached module import.
    script = textwrap.dedent("""
        import sys
        attempted = []
        def guard(event, args):
            if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname",
                         "socket.gethostbyaddr", "socket.sendto"}:
                attempted.append(event)
                raise AssertionError("Startup attempted external network: " + event)
        sys.addaudithook(guard)
        import studio
        from studio.main import create_app
        from fastapi.testclient import TestClient
        with TestClient(create_app()) as client:
            response = client.get("/health/live")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        assert attempted == [], attempted
    """)
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
