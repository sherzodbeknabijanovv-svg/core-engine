from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.models.schemas import (
    AnswerIn, EssayScoreOut, EssaySubmitIn, NextStepOut, RoadmapOut, StartSessionOut,
)
from app.services import test_scorer
from app.services.essay_graders.grader_factory import get_essay_grader
from app.services.pdf_generator import build_roadmap_pdf
from app.services.roadmap_generator import generate_roadmap
from app.services.session_store import get_session_store

router = APIRouter(prefix="/api/v1/placement", tags=["placement"])


@router.post("/start", response_model=StartSessionOut)
def start_placement_test() -> StartSessionOut:
    return test_scorer.start_session()


@router.post("/answer", response_model=NextStepOut)
def submit_answer(payload: AnswerIn) -> NextStepOut:
    try:
        return test_scorer.submit_answer(payload)
    except test_scorer.SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    except test_scorer.QuestionMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/essay", response_model=EssayScoreOut)
def submit_essay(payload: EssaySubmitIn) -> EssayScoreOut:
    store = get_session_store()
    state = store.get(payload.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    settings = get_settings()
    grader = get_essay_grader()
    result = grader.grade(payload.session_id, payload.essay_text, settings.essay_target_word_count)

    state.essay_text = payload.essay_text
    state.essay_result = result.model_dump()
    return result


@router.get("/roadmap/{session_id}", response_model=RoadmapOut)
def get_roadmap(session_id: str) -> RoadmapOut:
    store = get_session_store()
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    return generate_roadmap(state)


@router.get("/roadmap/{session_id}/pdf")
def get_roadmap_pdf(session_id: str) -> Response:
    store = get_session_store()
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    roadmap = generate_roadmap(state)
    pdf_bytes = build_roadmap_pdf(roadmap)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="edustimul-roadmap-{session_id[:8]}.pdf"'},
    )
