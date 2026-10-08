"""Allowlisted access records replace Uvicorn's raw URL access log."""

import logging


class _DropRawAccess(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return False


class _SafeAccessHandler(logging.StreamHandler):
    pass


def configure_access_logging() -> None:
    raw = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, _DropRawAccess) for item in raw.filters):
        raw.addFilter(_DropRawAccess())
    safe = logging.getLogger("studio.access")
    safe.setLevel(logging.INFO)
    if not any(isinstance(item, _SafeAccessHandler) for item in safe.handlers):
        handler = _SafeAccessHandler()
        handler.setFormatter(
            logging.Formatter("request_id=%(request_id)s status_code=%(status_code)s")
        )
        safe.addHandler(handler)


def record_access(request_id: str, status_code: int) -> None:
    logging.getLogger("studio.access").log(
        logging.ERROR if status_code >= 500 else logging.INFO,
        "request_complete",
        extra={"request_id": request_id, "status_code": status_code},
    )
