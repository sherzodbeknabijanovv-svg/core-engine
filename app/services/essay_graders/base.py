"""
EssayGrader — abstrakt interfeys. Bu Strategy pattern: qaysi grader
ishlatilishidan qat'i nazar (heuristik yoki OpenAI GPT-4o), API qatlami
bir xil `EssayScoreOut` natijasini oladi. Kelajakda GPT-4o kalitini
qo'shganda faqat `app/config.py`dagi `essay_grader` sozlamasini
"openai" ga o'zgartirish kifoya — boshqa hech narsa o'zgarmaydi.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import EssayScoreOut


class EssayGrader(ABC):
    @abstractmethod
    def grade(self, session_id: str, essay_text: str, target_word_count: int) -> EssayScoreOut:
        raise NotImplementedError
