"""
Moslashuvchan (adaptive) savol tanlash mantiqi.

Qoida oddiy va tushunarli: har bir bo'lim 'medium' qiyinlikdan boshlanadi.
Agar student oxirgi savolga TO'G'RI javob bersa — keyingi savol bir pog'ona
qiyinroq tanlanadi (easy->medium->hard). Agar NOTO'G'RI javob bersa — bir
pog'ona osonroq tanlanadi (hard->medium->easy). Agar tanlangan qiyinlik
darajasida savol qolmagan bo'lsa (pool tugagan), eng yaqin mavjud
darajaga muqobil ravishda o'tiladi (graceful fallback) — bu servis hech
qachon "savol qolmadi" deb yiqilib tushmaydi.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING

from app.models.schemas import Difficulty, Section, QuestionOut, SessionProgress

if TYPE_CHECKING:  # faqat tip tekshirish uchun — aylanma import (circular import) yuzaga kelmasligi uchun
    from app.services.session_store import SessionState

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "question_bank.json"

SECTION_LENGTHS: dict[Section, int] = {
    Section.grammar_vocab: 15,
    Section.listening: 10,
    Section.reading: 15,
}

_DIFFICULTY_ORDER = [Difficulty.easy, Difficulty.medium, Difficulty.hard]


def _load_bank() -> dict:
    with open(_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    # Har bir itemga section/difficulty maydonlarini biriktirib, tekis lug'atga yig'amiz: id -> item
    bank: dict[str, dict] = {}
    for section_key, tiers in raw.items():
        for tier_key, items in tiers.items():
            for item in items:
                item = dict(item)
                item["section"] = section_key
                item["difficulty"] = tier_key
                bank[item["id"]] = item
    return bank


class QuestionBank:
    """Butun savollar to'plamini xotirada saqlaydi (fayldan bir marta o'qiladi)."""

    def __init__(self) -> None:
        self._by_id = _load_bank()
        self._by_section_tier: dict[tuple[Section, Difficulty], list[str]] = {}
        for qid, item in self._by_id.items():
            key = (Section(item["section"]), Difficulty(item["difficulty"]))
            self._by_section_tier.setdefault(key, []).append(qid)

    def get(self, question_id: str) -> dict:
        return self._by_id[question_id]

    def pick(self, section: Section, difficulty: Difficulty, exclude_ids: set[str]) -> dict | None:
        """Berilgan bo'lim+qiyinlikdan tasodifiy savol tanlaydi; agar shu darajada
        (allaqachon so'ralmagan) savol qolmasa, eng yaqin darajaga o'tadi."""
        tier_index = _DIFFICULTY_ORDER.index(difficulty)
        # Qidiruv tartibi: aynan shu daraja, keyin yaqinroq darajalar
        search_order = sorted(
            range(len(_DIFFICULTY_ORDER)),
            key=lambda i: abs(i - tier_index),
        )
        for i in search_order:
            tier = _DIFFICULTY_ORDER[i]
            candidates = [
                qid for qid in self._by_section_tier.get((section, tier), [])
                if qid not in exclude_ids
            ]
            if candidates:
                chosen_id = random.choice(candidates)
                return self._by_id[chosen_id]
        return None  # Butun bo'lim tugagan (amalda bo'lim uzunligidan oshib ketmasa yuz bermaydi)

    def to_question_out(self, item: dict, index_in_section: int) -> QuestionOut:
        section = Section(item["section"])
        return QuestionOut(
            id=item["id"],
            section=section,
            difficulty=Difficulty(item["difficulty"]),
            prompt=item["prompt"],
            options=item["options"],
            audio_transcript=item.get("audio_transcript"),
            passage=item.get("passage"),
            index_in_section=index_in_section,
            total_in_section=SECTION_LENGTHS[section],
        )


_bank_singleton: QuestionBank | None = None


def get_question_bank() -> QuestionBank:
    global _bank_singleton
    if _bank_singleton is None:
        _bank_singleton = QuestionBank()
    return _bank_singleton


def next_difficulty(current: Difficulty, was_correct: bool) -> Difficulty:
    idx = _DIFFICULTY_ORDER.index(current)
    if was_correct:
        idx = min(idx + 1, len(_DIFFICULTY_ORDER) - 1)
    else:
        idx = max(idx - 1, 0)
    return _DIFFICULTY_ORDER[idx]


SECTION_ORDER = [Section.grammar_vocab, Section.listening, Section.reading]


def build_progress(state: "SessionState") -> SessionProgress:
    return SessionProgress(
        grammar_vocab_done=len(state.answers.get(Section.grammar_vocab, [])),
        grammar_vocab_total=SECTION_LENGTHS[Section.grammar_vocab],
        listening_done=len(state.answers.get(Section.listening, [])),
        listening_total=SECTION_LENGTHS[Section.listening],
        reading_done=len(state.answers.get(Section.reading, [])),
        reading_total=SECTION_LENGTHS[Section.reading],
    )
