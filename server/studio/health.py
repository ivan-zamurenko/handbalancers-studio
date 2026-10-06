"""Process liveness; intentionally independent of database/provider readiness."""


def liveness() -> dict[str, str]:
    return {"status": "ok"}
