"""
Pydantic v2 sxemalari — API so'rov/javoblari va ichki ma'lumot
tuzilmalari shu yerda aniqlanadi. Structured Output talabiga mos
ravishda har bir javob qat'iy validatsiya qilinadigan shaklda.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Section(str, Enum):
    grammar_vocab = "grammar_vocab"
    listening = "listening"
    reading = "reading"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class CEFRLevel(str, Enum):
    a2 = "A2"
    b1 = "B1"
    b2 = "B2"
    c1 = "C1"


# ---------------------------------------------------------------- Questions

class QuestionOut(BaseModel):
    """Studentga yuboriladigan savol — to'g'ri javob maydoni YO'Q (fibrat
    qilinmasligi uchun)."""
    id: str
    section: Section
    difficulty: Difficulty
    prompt: str
    options: list[str]
    audio_transcript: str | None = Field(
        default=None,
        description="Listening bo'limida haqiqiy audio fayl o'rniga matn ko'rinishida "
                    "transkript (production versiyada audio URL bilan almashtiriladi).",
    )
    passage: str | None = Field(default=None, description="Reading bo'limi uchun matn.")
    index_in_section: int = Field(description="1-asosli, shu bo'lim ichidagi tartib raqami")
    total_in_section: int


class AnswerIn(BaseModel):
    session_id: str
    question_id: str
    selected_index: int = Field(ge=0, description="Tanlangan variantning indeksi (0-based)")


class NextStepOut(BaseModel):
    """Har bir javobdan keyingi server javobi: keyingi savol YOKI bo'lim/test tugadi."""
    session_id: str
    finished: bool
    section_finished: Section | None = None
    next_question: QuestionOut | None = None
    progress: "SessionProgress"


class SessionProgress(BaseModel):
    grammar_vocab_done: int
    grammar_vocab_total: int
    listening_done: int
    listening_total: int
    reading_done: int
    reading_total: int


NextStepOut.model_rebuild()


class StartSessionOut(BaseModel):
    session_id: str
    first_question: QuestionOut
    progress: SessionProgress


# ---------------------------------------------------------------- Essay

class EssaySubmitIn(BaseModel):
    session_id: str
    essay_text: str = Field(min_length=50, description="Kamida 50 belgi (juda qisqa insho baholanmaydi)")

    @field_validator("essay_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Insho matni bo'sh bo'lishi mumkin emas")
        return v


class EssayFeedbackItem(BaseModel):
    category: str
    comment: str
    severity: str = Field(description="'info' | 'warning' | 'critical'")


class EssayScoreOut(BaseModel):
    session_id: str
    word_count: int
    target_word_count: int
    overall_score: float = Field(ge=0, le=100)
    estimated_cefr: CEFRLevel
    sub_scores: dict[str, float] = Field(
        description="masalan: vocabulary_richness, grammar_accuracy, coherence, readability (har biri 0-100)"
    )
    strengths: list[str]
    weaknesses: list[str]
    feedback: list[EssayFeedbackItem]
    graded_by: str = Field(description="'heuristic-engine-v1' yoki 'openai-gpt4o'")


# ---------------------------------------------------------------- Roadmap

class WeakArea(BaseModel):
    section: str
    score_percent: float
    note: str


class StudyDayPlan(BaseModel):
    day_label: str
    focus: str
    tasks: list[str]
    duration_minutes: int


class RoadmapOut(BaseModel):
    session_id: str
    generated_at: datetime
    overall_level: CEFRLevel
    overall_score_percent: float
    section_scores: dict[str, float]
    essay_score: float | None = None
    weak_areas: list[WeakArea]
    daily_study_minutes: int
    weekly_plan: list[StudyDayPlan]
    summary: str
