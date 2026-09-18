"""
Placement test oqimini boshqaradi: sessiya boshlash, javobni qabul qilib
keyingi (moslashuvchan) savolni tanlash, bo'limlar orasida o'tish.
"""
from __future__ import annotations

from app.models.schemas import (
    AnswerIn, Difficulty, NextStepOut, QuestionOut, Section, StartSessionOut,
)
from app.services.question_bank import (
    SECTION_LENGTHS, SECTION_ORDER, build_progress, get_question_bank, next_difficulty,
)
from app.services.session_store import AnsweredQuestion, SessionState, get_session_store


class SessionNotFoundError(Exception):
    pass


class QuestionMismatchError(Exception):
    """Client boshqa (joriy bo'lmagan) savolga javob yubormoqchi bo'lganda."""


def start_session() -> StartSessionOut:
    store = get_session_store()
    state = store.create()
    bank = get_question_bank()

    item = bank.pick(state.current_section, state.current_difficulty, state.asked_ids)
    assert item is not None, "Savollar banki bo'sh — bu holat yuzaga kelmasligi kerak"
    state.current_question_id = item["id"]
    state.asked_ids.add(item["id"])

    index_in_section = len(state.answers.get(state.current_section, [])) + 1
    question_out = bank.to_question_out(item, index_in_section)

    return StartSessionOut(
        session_id=state.session_id,
        first_question=question_out,
        progress=build_progress(state),
    )


def _advance_to_next_section(state: SessionState) -> Section | None:
    idx = SECTION_ORDER.index(state.current_section)
    if idx + 1 < len(SECTION_ORDER):
        return SECTION_ORDER[idx + 1]
    return None


def submit_answer(payload: AnswerIn) -> NextStepOut:
    store = get_session_store()
    state = store.get(payload.session_id)
    if state is None:
        raise SessionNotFoundError(payload.session_id)
    if state.finished:
        raise QuestionMismatchError("Sessiya allaqachon yakunlangan")
    if state.current_question_id != payload.question_id:
        raise QuestionMismatchError(
            f"Kutilgan savol {state.current_question_id!r}, lekin {payload.question_id!r} yuborildi"
        )

    bank = get_question_bank()
    item = bank.get(payload.question_id)
    correct_index = item["correct"]
    was_correct = payload.selected_index == correct_index
    section = Section(item["section"])

    state.record_answer(section, AnsweredQuestion(
        question_id=item["id"],
        difficulty=Difficulty(item["difficulty"]),
        selected_index=payload.selected_index,
        correct=was_correct,
    ))

    section_done = len(state.answers.get(section, []))
    section_total = SECTION_LENGTHS[section]

    if section_done >= section_total:
        # Shu bo'lim tugadi — keyingi bo'limga o'tamiz (yoki test tugadi)
        next_section = _advance_to_next_section(state)
        if next_section is None:
            state.finished = True
            state.current_question_id = None
            return NextStepOut(
                session_id=state.session_id,
                finished=True,
                section_finished=section,
                next_question=None,
                progress=build_progress(state),
            )
        state.current_section = next_section
        state.current_difficulty = Difficulty.medium  # har bir bo'lim 'medium'dan boshlanadi
        next_item = bank.pick(next_section, state.current_difficulty, state.asked_ids)
        assert next_item is not None
        state.current_question_id = next_item["id"]
        state.asked_ids.add(next_item["id"])
        index_in_section = 1
        return NextStepOut(
            session_id=state.session_id,
            finished=False,
            section_finished=section,
            next_question=bank.to_question_out(next_item, index_in_section),
            progress=build_progress(state),
        )

    # Shu bo'lim ichida davom etamiz — qiyinlikni moslashtiramiz
    state.current_difficulty = next_difficulty(Difficulty(item["difficulty"]), was_correct)
    next_item = bank.pick(section, state.current_difficulty, state.asked_ids)
    assert next_item is not None
    state.current_question_id = next_item["id"]
    state.asked_ids.add(next_item["id"])
    index_in_section = section_done + 1

    return NextStepOut(
        session_id=state.session_id,
        finished=False,
        section_finished=None,
        next_question=bank.to_question_out(next_item, index_in_section),
        progress=build_progress(state),
    )
