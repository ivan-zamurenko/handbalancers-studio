"""Auth helper sends only an official Firecrawl credential to the configured MCP."""

import importlib
import json

import pytest


def test_credential_file_reused_without_copying(tmp_path):
    helper = importlib.import_module("tools.firecrawl_mcp_headers")
    path = tmp_path / "credentials.json"
    path.write_text(
        json.dumps({"apiKey": "fc-synthetic-test", "apiUrl": "https://api.firecrawl.dev"})
    )
    before = path.read_bytes()
    assert helper.auth_headers({}, path) == {"Authorization": "Bearer fc-synthetic-test"}
    assert path.read_bytes() == before


def test_missing_auth_does_not_invent_a_key(tmp_path):
    helper = importlib.import_module("tools.firecrawl_mcp_headers")
    assert helper.auth_headers({}, tmp_path / "missing.json") == {}


@pytest.mark.parametrize(
    "values",
    [
        {"apiKey": "fc-synthetic-test", "apiUrl": "https://self-hosted.example"},
        {"apiKey": "fc-synthetic\r\nInjected: yes", "apiUrl": "https://api.firecrawl.dev"},
    ],
)
def test_unrelated_or_malformed_credentials_rejected(tmp_path, values):
    helper = importlib.import_module("tools.firecrawl_mcp_headers")
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps(values))
    with pytest.raises(ValueError, match="Invalid Firecrawl credential configuration"):
        helper.auth_headers({}, path)


def test_environment_key_takes_precedence(tmp_path):
    helper = importlib.import_module("tools.firecrawl_mcp_headers")
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"apiKey": "fc-unrelated", "apiUrl": "https://self-hosted.example"}))
    assert helper.auth_headers({"FIRECRAWL_API_KEY": "fc-synthetic-env"}, path) == {
        "Authorization": "Bearer fc-synthetic-env"
    }


def test_configured_helper_works_from_project_subdirectory():
    import os
    import subprocess
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / ".codex/config.toml").read_text())
    result = subprocess.run(
        config["mcp_servers"]["firecrawl"]["http_headers_helper"],
        shell=True,
        check=False,
        cwd=root / "server",
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "FIRECRAWL_API_KEY": "fc-synthetic-subdir",
            "FIRECRAWL_API_URL": "https://api.firecrawl.dev",
        },
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"Authorization": "Bearer fc-synthetic-subdir"}
