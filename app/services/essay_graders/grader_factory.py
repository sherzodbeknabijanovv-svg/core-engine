"""
Grader factory — `app/config.py` dagi `essay_grader` sozlamasiga qarab
qaysi EssayGrader implementatsiyasi ishlatilishini tanlaydi.

Bu yerga qo'l urish shart emas: OpenAI kalitini qo'shgach, .env faylda
`ESSAY_GRADER=openai` deb qo'ysangiz kifoya.
"""
from __future__ import annotations

from app.config import get_settings
from app.services.essay_graders.base import EssayGrader
from app.services.essay_graders.heuristic import HeuristicEssayGrader

_grader_singleton: EssayGrader | None = None


def get_essay_grader() -> EssayGrader:
    global _grader_singleton
    if _grader_singleton is not None:
        return _grader_singleton

    settings = get_settings()
    if settings.essay_grader == "openai":
        from app.services.essay_graders.openai_grader import OpenAIEssayGrader
        _grader_singleton = OpenAIEssayGrader()
    else:
        _grader_singleton = HeuristicEssayGrader()
    return _grader_singleton


def reset_grader_cache() -> None:
    """Testlar uchun — sozlama o'zgarganda keshni tozalash."""
    global _grader_singleton
    _grader_singleton = None
