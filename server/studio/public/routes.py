"""Read-only public pages, rendered from approved copy with explicit locale."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

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

    def copy(uk: str, en: str) -> str:
        return uk if language == "uk" else en

    oauth = getattr(request.app.state, "oauth_service", None)
    providers: frozenset[str] = getattr(oauth, "providers", frozenset())
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "language": language,
            "copy": copy,
            "plans": PLANS,
            "page_path": request.url.path,
            "oauth_providers": providers,
            "oauth_feedback": request.query_params.get("oauth", ""),
            # Cookie presence only; the browser still confirms the session via /api/session.
            "signed_in": bool(request.cookies.get(session_name(request))),
        },
        headers={
            "Cache-Control": "no-store",
        },
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    return render(request, "public/index.html")


@router.get("/plans", response_class=HTMLResponse, include_in_schema=False)
async def plans_page(request: Request) -> HTMLResponse:
    return render(request, "public/plans.html")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request) -> HTMLResponse:
    return render(request, "public/login.html")
