"""
Matnni tahlil qilish uchun yordamchi funksiyalar — insho baholashning
"tayanch o'lchovlari". Bularning barchasi tashqi AI xizmatisiz, faqat
statistik/lingvistik hisob-kitoblar asosida ishlaydi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from spellchecker import SpellChecker
import textstat

_spell = SpellChecker(distance=1)  # distance=1 -> tezroq, insholar uchun yetarli


_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")


@dataclass
class TextMetrics:
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    unique_word_ratio: float  # type-token ratio (lug'at boyligi)
    long_word_ratio: float  # 7+ harfli so'zlar ulushi (lug'at murakkabligi belgisi)
    misspelled_words: list[str]
    spelling_error_rate: float  # xato so'zlar / jami so'zlar
    flesch_reading_ease: float
    flesch_kincaid_grade: float


def _split_words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return parts


def analyze_text(text: str) -> TextMetrics:
    words = _split_words(text)
    word_count = len(words)
    sentences = _split_sentences(text)
    sentence_count = max(len(sentences), 1)
    avg_sentence_length = round(word_count / sentence_count, 2)

    lower_words = [w.lower() for w in words]
    unique_ratio = round(len(set(lower_words)) / word_count, 3) if word_count else 0.0
    long_words = [w for w in words if len(w) >= 7]
    long_word_ratio = round(len(long_words) / word_count, 3) if word_count else 0.0

    # Imlo tekshiruvi — juda qisqa yoki apostrofli so'zlarni chetlab o'tamiz (soxta xato bermasin)
    candidates = {w.lower() for w in words if len(w) > 2 and w.isalpha()}
    misspelled = sorted(_spell.unknown(candidates)) if candidates else []
    spelling_error_rate = round(len(misspelled) / word_count, 3) if word_count else 0.0

    try:
        flesch_ease = float(textstat.flesch_reading_ease(text))
        flesch_grade = float(textstat.flesch_kincaid_grade(text))
    except Exception:
        flesch_ease, flesch_grade = 50.0, 8.0

    return TextMetrics(
        word_count=word_count,
        sentence_count=sentence_count,
        avg_sentence_length=avg_sentence_length,
        unique_word_ratio=unique_ratio,
        long_word_ratio=long_word_ratio,
        misspelled_words=misspelled,
        spelling_error_rate=spelling_error_rate,
        flesch_reading_ease=round(flesch_ease, 1),
        flesch_kincaid_grade=round(flesch_grade, 1),
    )
