"""
Sessiya holatini saqlash.

DIQQAT (production eslatmasi): bu — xotirada (in-memory dict) ishlaydigan
soddalashtirilgan implementatsiya, portfolio/demo maqsadida yetarli.
Ishlab chiqarish muhitida bu Redis yoki ma'lumotlar bazasiga
ko'chirilishi kerak (bir nechta server instance yoki restart bo'lganda
sessiyalar yo'qolib qolmasligi uchun) — README'da alohida qayd etilgan.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.models.schemas import Difficulty, Section


@dataclass
class AnsweredQuestion:
    question_id: str
    difficulty: Difficulty
    selected_index: int
    correct: bool


@dataclass
class SessionState:
    session_id: str
    current_section: Section = Section.grammar_vocab
    current_difficulty: Difficulty = Difficulty.medium
    current_question_id: str | None = None
    asked_ids: set[str] = field(default_factory=set)
    answers: dict[Section, list[AnsweredQuestion]] = field(default_factory=dict)
    essay_text: str | None = None
    essay_result: dict | None = None
    finished: bool = False

    def record_answer(self, section: Section, answered: AnsweredQuestion) -> None:
        self.answers.setdefault(section, []).append(answered)

    def section_score_percent(self, section: Section) -> float:
        items = self.answers.get(section, [])
        if not items:
            return 0.0
        correct = sum(1 for a in items if a.correct)
        return round(100 * correct / len(items), 1)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self) -> SessionState:
        session_id = uuid.uuid4().hex
        state = SessionState(session_id=session_id)
        self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def all(self) -> dict[str, SessionState]:
        return self._sessions


_store_singleton: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = SessionStore()
    return _store_singleton
