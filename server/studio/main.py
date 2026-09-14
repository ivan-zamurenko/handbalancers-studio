"""Application assembly. Run with uvicorn studio.main:app from server/."""

from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from studio.api import router as api_router
from studio.authentication import profile_router
from studio.authentication import router as auth_router
from studio.db import make_engine, make_session_factory
from studio.oauth import router as oauth_router
from studio.settings import SERVER_DIR, Settings


class BodyLimitMiddleware:
    """Bound streamed bodies too; Content-Length alone is not a trustworthy limit."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            return await self.app(scope, receive, send)
        limit = 1024 * 1024 if scope["path"] == "/api/webhooks/stripe" else 32 * 1024
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > limit:
                return await JSONResponse({"detail": "Request is too large"}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(body)
            if not message.get("more_body", False):
                break
        consumed = False

        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


def create_app(settings: Settings | None = None, session_factory=None) -> FastAPI:
    settings = settings or Settings()
    engine = None if session_factory else make_engine(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if engine:
            engine.dispose()

    app = FastAPI(
        title="Handbalancer's Studio",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(engine)
    allowed_hosts = [urlsplit(settings.base_url).hostname]
    if settings.app_env != "production":
        allowed_hosts += ["localhost", "127.0.0.1", "[::1]"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    app.add_middleware(BodyLimitMiddleware)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self' https://accounts.google.com https://appleid.apple.com"
        )
        # Mutable script/style URLs must revalidate, including imported JS modules.
        if request.url.path.startswith("/static/") and request.url.path.endswith((".js", ".css")):
            response.headers["Cache-Control"] = "no-cache"
        elif not request.url.path.startswith(("/static/", "/assets/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Validation responses intentionally omit submitted values and exception internals.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse({"detail": "Storage is temporarily unavailable"}, status_code=503)

    @app.get("/health/live", include_in_schema=False)
    def live():
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    def ready():
        try:
            with app.state.session_factory() as db:
                db.execute(text("SELECT 1 FROM alembic_version LIMIT 1"))
                db.execute(text("SELECT 1 FROM browser_sessions LIMIT 0"))
        except SQLAlchemyError:
            raise HTTPException(503, "Database is not ready") from None
        return {"status": "ok"}

    app.include_router(api_router)
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(oauth_router)
    app.mount(
        "/static", StaticFiles(directory=SERVER_DIR / "static", check_dir=False), name="static"
    )
    app.mount(
        "/assets", StaticFiles(directory=SERVER_DIR / "static", check_dir=False), name="assets"
    )
    templates = Jinja2Templates(directory=SERVER_DIR / "templates")

    def shell(request: Request):
        return templates.TemplateResponse(request=request, name="index.html", context={})

    for path in (
        "/",
        "/onboarding",
        "/register",
        "/login",
        "/plans",
        "/checkout",
        "/dashboard",
        "/privacy",
        "/terms",
    ):
        app.add_api_route(path, shell, methods=["GET"], include_in_schema=False)
    return app


app = create_app()
