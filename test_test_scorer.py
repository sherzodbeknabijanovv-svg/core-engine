import json
from pathlib import Path

import pytest

from app.models.schemas import AnswerIn
from app.services import test_scorer
from app.services.session_store import get_session_store

_BANK_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "question_bank.json"


def _answer_key() -> dict[str, int]:
    raw = json.loads(_BANK_PATH.read_text(encoding="utf-8"))
    key = {}
    for section, tiers in raw.items():
        for tier, items in tiers.items():
            for item in items:
                key[item["id"]] = item["correct"]
    return key


def _run_full_session(all_correct: bool = True) -> tuple[str, int]:
    """To'liq 40 ta savolli sessiyani yakunlaydi. Return: (session_id, total_answered)."""
    key = _answer_key()
    start = test_scorer.start_session()
    session_id = start.session_id
    q = start.first_question
    total = 0
    finished = False
    while not finished:
        correct_idx = key[q.id]
        selected = correct_idx if all_correct else (correct_idx + 1) % len(q.options)
        step = test_scorer.submit_answer(AnswerIn(session_id=session_id, question_id=q.id, selected_index=selected))
        total += 1
        finished = step.finished
        if not finished:
            q = step.next_question
    return session_id, total


def test_full_session_answers_exactly_40_questions():
    session_id, total = _run_full_session(all_correct=True)
    assert total == 40


def test_full_session_all_correct_yields_perfect_section_scores():
    session_id, _ = _run_full_session(all_correct=True)
    state = get_session_store().get(session_id)
    from app.models.schemas import Section
    assert state.section_score_percent(Section.grammar_vocab) == 100.0
    assert state.section_score_percent(Section.listening) == 100.0
    assert state.section_score_percent(Section.reading) == 100.0


def test_full_session_mixed_answers_completes_without_error():
    # all_correct=False -> har doim NOTO'G'RI javob beradi -> qiyinlik doim pasayadi (easy'da qotib qoladi)
    session_id, total = _run_full_session(all_correct=False)
    assert total == 40  # baribir tugashi kerak — pool tugab qolmasligi kerak


def test_answer_to_wrong_question_id_raises_mismatch():
    start = test_scorer.start_session()
    with pytest.raises(test_scorer.QuestionMismatchError):
        test_scorer.submit_answer(AnswerIn(
            session_id=start.session_id, question_id="not-the-current-question", selected_index=0,
        ))


def test_answer_with_unknown_session_raises_not_found():
    with pytest.raises(test_scorer.SessionNotFoundError):
        test_scorer.submit_answer(AnswerIn(session_id="does-not-exist", question_id="gv-e1", selected_index=0))


def test_cannot_answer_after_session_finished():
    key = _answer_key()
    start = test_scorer.start_session()
    session_id = start.session_id
    q = start.first_question
    finished = False
    while not finished:
        step = test_scorer.submit_answer(AnswerIn(session_id=session_id, question_id=q.id, selected_index=key[q.id]))
        finished = step.finished
        if not finished:
            q = step.next_question
    with pytest.raises(test_scorer.QuestionMismatchError):
        test_scorer.submit_answer(AnswerIn(session_id=session_id, question_id="gv-e1", selected_index=0))
