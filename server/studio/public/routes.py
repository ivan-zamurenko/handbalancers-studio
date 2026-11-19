"""Read-only public pages, rendered from approved copy with explicit locale."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, RedirectResponse

from studio.accounts.entry import entry_destination
from studio.auth.oauth_routes import session_name
from studio.shared.i18n import get_locale

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")
# Presentation prices in EUR minor units; never an entitlement or checkout source.
PLANS = (
    (
        "essential",
        "Essential",
        1999,
        "Власний ритм. Зрозумілий прогрес.",
        "Your own rhythm. Clear progress.",
        ("Конструктор програм", "Журнал занять", "Історія й метрики"),
        ("Program builder", "Training journal", "History and metrics"),
    ),
    (
        "plus",
        "Plus",
        4999,
        "Особистий напрям із підтримкою.",
        "Personal direction with support.",
        (
            "Усе з Essential, а також",
            "План за вашими цілями",
            "Контрольні відео та звіти",
            "Адаптація тижня",
        ),
        (
            "Everything in Essential, plus",
            "A plan for your goals",
            "Check-in videos and reports",
            "Weekly adaptation",
        ),
    ),
    (
        "pro",
        "Pro",
        17999,
        "Структура програми. Увага тренера.",
        "A structured program. A coach’s attention.",
        ("Усе з Plus, а також", "Особиста щотижнева перевірка", "Відео й коментарі тренера"),
        ("Everything in Plus, plus", "Personal weekly review", "Coach video feedback and comments"),
    ),
    (
        "pro-plus",
        "Pro+",
        29999,
        "Ближчий контакт. Глибша робота.",
        "Closer contact. Deeper work.",
        (
            "Усе з Pro, а також",
            "Два дзвінки по 30 хв на місяць",
            "Особистий чат у погоджених межах",
            "Детальне обговорення практики",
        ),
        (
            "Everything in Pro, plus",
            "Two 30-minute calls per month",
            "Personal chat within agreed limits",
            "In-depth practice discussions",
        ),
    ),
)


def render(request: Request, template: str) -> HTMLResponse:
    language = get_locale(request.query_params.get("lang"))

    translations: list[tuple[str, str]] = [
        ("Завантажуємо сторінку…", "Loading page…"),
        ("Завантажуємо…", "Loading…"),
    ]

    def copy(uk: str, en: str) -> str:
        pair = (uk, en)
        if pair not in translations:
            translations.append(pair)
        return uk if language == "uk" else en

    oauth = getattr(request.app.state, "oauth_service", None)
    providers: frozenset[str] = getattr(oauth, "providers", frozenset())
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "language": language,
            "copy": copy,
            "translations": translations,
            "plans": PLANS,
            "page_path": request.url.path,
            "oauth_providers": providers,
            "email_auth_enabled": request.app.state.settings.auth_email_enabled,
            "oauth_feedback": request.query_params.get("oauth", ""),
            # Cookie presence only; the browser still confirms the session via /api/session.
            "signed_in": bool(request.cookies.get(session_name(request))),
        },
        headers={
            "Cache-Control": "no-store",
        },
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    destination = await public_entry_destination(request)
    if destination != "/login":
        return member_redirect(request, destination)
    return render(request, "public/index.html")


@router.get("/plans", response_class=HTMLResponse, include_in_schema=False)
async def plans_page(request: Request):
    destination = await public_entry_destination(request)
    if destination != "/login":
        return member_redirect(request, destination)
    return render(request, "public/plans.html")


async def public_entry_destination(request: Request) -> str:
    # Public copy stays available during auth outages. This fallback grants no
    # member access: dashboard/progress still use the fail-closed entry guard.
    try:
        return await entry_destination(request)
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        return "/login"


@router.get("/onboarding", response_class=HTMLResponse, include_in_schema=False)
async def onboarding_page(request: Request):
    destination = await entry_destination(request)
    if destination != "/login":
        return member_redirect(request, destination)
    return render(request, "public/onboarding.html")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request) -> HTMLResponse:
    return render(request, "auth/login.html")


@router.get("/recovery", response_class=HTMLResponse, include_in_schema=False)
async def recovery_page(request: Request) -> HTMLResponse:
    return render(request, "auth/recovery.html")


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request) -> HTMLResponse:
    return render(request, "auth/register.html")


@router.get("/profile", response_class=HTMLResponse, include_in_schema=False)
async def profile_page(request: Request) -> HTMLResponse:
    return render(request, "member/profile.html")


@router.get("/verify-email", response_class=HTMLResponse, include_in_schema=False)
async def verify_page(request: Request) -> HTMLResponse:
    return render(request, "auth/verify.html")


def member_redirect(request: Request, destination: str) -> RedirectResponse:
    suffix = (
        f"?lang={get_locale(request.query_params['lang'])}"
        if "lang" in request.query_params
        else ""
    )
    return RedirectResponse(
        f"{destination}{suffix}", status_code=303, headers={"Cache-Control": "no-store"}
    )


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    destination = await entry_destination(request)
    if destination != "/dashboard":
        return member_redirect(request, destination)
    return render(request, "member/dashboard.html")


@router.get("/progress", response_class=HTMLResponse, include_in_schema=False)
async def progress_page(request: Request):
    destination = await entry_destination(request)
    if destination != "/dashboard":
        return member_redirect(request, destination)
    return render(request, "member/progress.html")
