"""
app/api/v1/router.py
─────────────────────
Central router — imported once in main.py.
Add every new route module here.
"""
from fastapi import APIRouter

from app.api.v1 import auth, care_plan, chat, onboarding, patient, vision

api_router = APIRouter()

# ── Auth ──────────────────────────────────────────────────────────────────────
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

# ── Chat ──────────────────────────────────────────────────────────────────────
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"],
)

# ── Onboarding ────────────────────────────────────────────────────────────────
api_router.include_router(
    onboarding.router,
    prefix="/onboarding",
    tags=["Onboarding"],
)

# ── Patient ───────────────────────────────────────────────────────────────────
api_router.include_router(
    patient.router,
    prefix="/patient",
    tags=["Patient"],
)

# ── Care Plan ─────────────────────────────────────────────────────────────────
api_router.include_router(
    care_plan.router,
    prefix="/care-plan",
    tags=["Care Plan"],
)

# ── Vision ────────────────────────────────────────────────────────────────────
api_router.include_router(
    vision.router,
    prefix="/vision",
    tags=["Vision"],
)
