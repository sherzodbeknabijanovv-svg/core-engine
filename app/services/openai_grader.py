"""
OpenAIEssayGrader — GPT-4o orqali Structured JSON Output yordamida
insho baholaydi.

DIQQAT: bu klass ishlashi uchun `OPENAI_API_KEY` muhit o'zgaruvchisi
kerak (.env faylga qo'shing) va `ESSAY_GRADER=openai` qilib sozlash
kerak (app/config.py). Kalitsiz bu klass chaqirilmaydi — standart
grader `HeuristicEssayGrader` (heuristic.py) bo'lib qoladi.

Muhim: bu kodni men (Claude) o'z muhitimda API'ga chiqa olmaganim
uchun jonli chaqiruv bilan sinamadim — tuzilishi OpenAI'ning rasmiy
Structured Outputs (`beta.chat.completions.parse`) andozasiga mos
yozilgan. Kalitingizni qo'shgach, `tests/test_openai_grader_smoke.py`
(pytest bilan emas, qo'lda) orqali bitta haqiqiy chaqiruv qilib
tekshirib ko'rishni tavsiya qilaman.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.schemas import CEFRLevel, EssayFeedbackItem, EssayScoreOut
from app.services.essay_graders.base import EssayGrader


class _LLMSubScores(BaseModel):
    vocabulary_richness: float = Field(ge=0, le=100)
    grammar_accuracy: float = Field(ge=0, le=100)
    coherence: float = Field(ge=0, le=100)
    readability: float = Field(ge=0, le=100)


class _LLMFeedbackItem(BaseModel):
    category: str
    comment: str
    severity: str


class _LLMEssayGrade(BaseModel):
    """GPT-4o dan kutilayotgan structured-output sxemasi."""
    overall_score: float = Field(ge=0, le=100)
    estimated_cefr: CEFRLevel
    sub_scores: _LLMSubScores
    strengths: list[str]
    weaknesses: list[str]
    feedback: list[_LLMFeedbackItem]


_SYSTEM_PROMPT = (
    "You are an expert IELTS/SAT English essay examiner. Grade the given "
    "300-word essay strictly and consistently, the way a US university "
    "admissions writing evaluator would. Score each sub-criterion from 0 to "
    "100. Be constructive but honest in feedback. Respond only in the given "
    "structured schema."
)


class OpenAIEssayGrader(EssayGrader):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY topilmadi. .env fayliga qo'shing yoki "
                "ESSAY_GRADER=heuristic qilib qoldiring."
            )
        # Import shu yerda — kalit bo'lmaganda openai paketi umuman chaqirilmasin deb
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    def grade(self, session_id: str, essay_text: str, target_word_count: int) -> EssayScoreOut:
        completion = self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Target length: {target_word_count} words.\n\nEssay:\n{essay_text}"},
            ],
            response_format=_LLMEssayGrade,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("OpenAI structured output bo'sh qaytdi")

        word_count = len(essay_text.split())
        return EssayScoreOut(
            session_id=session_id,
            word_count=word_count,
            target_word_count=target_word_count,
            overall_score=parsed.overall_score,
            estimated_cefr=parsed.estimated_cefr,
            sub_scores=parsed.sub_scores.model_dump(),
            strengths=parsed.strengths,
            weaknesses=parsed.weaknesses,
            feedback=[
                EssayFeedbackItem(category=f.category, comment=f.comment, severity=f.severity)
                for f in parsed.feedback
            ],
            graded_by="openai-gpt4o",
        )
