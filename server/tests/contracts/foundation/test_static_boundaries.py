"""The product serves runtime assets, not internal motion studies."""

import pytest
from fastapi.testclient import TestClient
from studio.main import create_app


@pytest.mark.parametrize(
    "path",
    [
        "/static/previews/handstand/index.html",
        "/static/previews/handstand/overview.gif",
        "/_previews/handstand/index.html",
    ],
)
def test_product_does_not_publish_motion_studies(path):
    with TestClient(create_app({"app_env": "test"})) as client:
        assert client.get(path).status_code == 404


def test_product_still_serves_its_loading_animation():
    with TestClient(create_app({"app_env": "test"})) as client:
        for path in ["/static/js/components/handstand-motion.js", "/static/css/handstand.css"]:
            assert client.get(path).status_code == 200
