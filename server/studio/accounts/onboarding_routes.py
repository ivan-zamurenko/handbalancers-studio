"""Validate a guest draft before navigation; storage is bounded to the browser tab.

No identity, subscription or database write is inferred from these answers.
Pre-auth CSRF uses the same strict Origin check as register/login/OAuth start.
"""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from studio.accounts.onboarding import OnboardingChoices
from studio.auth.csrf import same_origin

router = APIRouter(prefix="/api/onboarding")


@router.post("/draft")
async def validate_draft(request: Request, data: OnboardingChoices) -> JSONResponse:
    same_origin(request)
    return JSONResponse(data.model_dump(), headers={"Cache-Control": "no-store"})
