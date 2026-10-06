"""Explicit local test configuration; never load machine or production secrets."""

import pytest


@pytest.fixture
def test_settings():
    return {"app_env": "test"}
