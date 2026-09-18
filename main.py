from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import placement

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "EduStimul Core Engine — Level Placement Test & AI Roadmap microservice.\n\n"
        "40-question adaptive placement test (Grammar & Vocabulary, Listening, Reading) "
        "plus a 300-word essay, scored either by a built-in heuristic engine (no API key "
        "required) or by GPT-4o (when OPENAI_API_KEY is configured), producing a "
        "personalized study roadmap (JSON and PDF)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(placement.router)


@app.get("/api/v1/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}
