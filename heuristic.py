"""
HeuristicEssayGrader — OpenAI kalitisiz ishlaydigan, haqiqiy statistik/
lingvistik o'lchovlarga asoslangan insho baholovchi.

Bu "soxta" yoki tasodifiy ball bermaydi: har bir sub-score aniq,
qayta hisoblanadigan formuladan chiqadi (quyida izohlangan), shuning
uchun bir xil insho har doim bir xil ballni oladi (deterministik) —
bu pytest orqali test qilinishi mumkinligini ta'minlaydi.

O'lchovlar:
  - vocabulary_richness : lug'at xilma-xilligi (type-token ratio) + uzun so'zlar ulushi
  - grammar_accuracy    : imlo xatolari darajasiga asoslangan proksi
  - coherence           : gap uzunligi barqarorligiga asoslangan proksi
  - readability         : Flesch Reading Ease formulasi
"""
from __future__ import annotations

from app.models.schemas import CEFRLevel, EssayFeedbackItem, EssayScoreOut
from app.services.essay_graders.base import EssayGrader
from app.utils.text_metrics import TextMetrics, analyze_text


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _vocabulary_score(m: TextMetrics) -> float:
    base = _clamp(m.unique_word_ratio / 0.55 * 70)
    bonus = _clamp(m.long_word_ratio / 0.25 * 30)
    return round(_clamp(base + bonus), 1)


def _grammar_score(m: TextMetrics) -> float:
    penalty = m.spelling_error_rate * 100 * 8
    return round(_clamp(100 - penalty), 1)


def _coherence_score(m: TextMetrics) -> float:
    ideal_min, ideal_max = 10.0, 25.0
    if ideal_min <= m.avg_sentence_length <= ideal_max:
        return 100.0
    if m.avg_sentence_length < ideal_min:
        deviation = ideal_min - m.avg_sentence_length
    else:
        deviation = m.avg_sentence_length - ideal_max
    return round(_clamp(100 - deviation * 4), 1)


def _readability_score(m: TextMetrics) -> float:
    return round(_clamp(m.flesch_reading_ease), 1)


def _word_count_multiplier(word_count: int, target: int) -> float:
    if target <= 0:
        return 1.0
    ratio = word_count / target
    if 0.85 <= ratio <= 1.3:
        return 1.0
    if ratio < 0.85:
        return max(0.5, ratio / 0.85)
    return max(0.85, 1 - (ratio - 1.3) * 0.3)


def _estimate_cefr(score: float) -> CEFRLevel:
    if score < 40:
        return CEFRLevel.a2
    if score < 65:
        return CEFRLevel.b1
    if score < 85:
        return CEFRLevel.b2
    return CEFRLevel.c1


class HeuristicEssayGrader(EssayGrader):
    def grade(self, session_id: str, essay_text: str, target_word_count: int) -> EssayScoreOut:
        metrics = analyze_text(essay_text)

        sub_scores = {
            "vocabulary_richness": _vocabulary_score(metrics),
            "grammar_accuracy": _grammar_score(metrics),
            "coherence": _coherence_score(metrics),
            "readability": _readability_score(metrics),
        }
        weighted = (
            sub_scores["vocabulary_richness"] * 0.30
            + sub_scores["grammar_accuracy"] * 0.35
            + sub_scores["coherence"] * 0.20
            + sub_scores["readability"] * 0.15
        )
        multiplier = _word_count_multiplier(metrics.word_count, target_word_count)
        overall = round(_clamp(weighted * multiplier), 1)

        strengths: list[str] = []
        weaknesses: list[str] = []
        feedback: list[EssayFeedbackItem] = []

        if sub_scores["vocabulary_richness"] >= 75:
            strengths.append("Lug'at boyligi va xilma-xilligi yaxshi darajada.")
        elif sub_scores["vocabulary_richness"] < 50:
            weaknesses.append("So'zlar ko'p takrorlanmoqda — sinonimlardan ko'proq foydalaning.")
            feedback.append(EssayFeedbackItem(
                category="Vocabulary", severity="warning",
                comment="Insho ichida bir xil so'zlar tez-tez takrorlanyapti. Har bir asosiy fikr uchun turli so'z va iboralardan foydalanishga harakat qiling.",
            ))

        if sub_scores["grammar_accuracy"] >= 85:
            strengths.append("Imlo xatolari deyarli yo'q.")
        elif sub_scores["grammar_accuracy"] < 60:
            weaknesses.append("Imlo xatolari soni ko'p — diqqat bilan qayta o'qib chiqing.")

        if metrics.misspelled_words:
            preview = ", ".join(metrics.misspelled_words[:6])
            feedback.append(EssayFeedbackItem(
                category="Spelling",
                severity="warning" if metrics.spelling_error_rate > 0.03 else "info",
                comment=f"Ehtimoliy imlo xatolari topildi: {preview}"
                        + (" va boshqalar." if len(metrics.misspelled_words) > 6 else "."),
            ))

        if sub_scores["coherence"] >= 85:
            strengths.append("Gaplar uzunligi muvozanatli — matn o'qishga qulay.")
        elif sub_scores["coherence"] < 55:
            if metrics.avg_sentence_length < 10:
                weaknesses.append("Gaplar juda qisqa va uzuq-yuluq — fikrlarni bog'lovchilar (however, moreover, because) yordamida bog'lang.")
            else:
                weaknesses.append("Ba'zi gaplar juda uzun — ularni ikki qismga bo'lib, aniqroq ifodalang.")
            feedback.append(EssayFeedbackItem(
                category="Sentence Structure",
                severity="warning",
                comment=f"O'rtacha gap uzunligi: {metrics.avg_sentence_length} so'z. Aniq va ravon matn uchun 10-25 so'zlik gaplar tavsiya etiladi.",
            ))

        if sub_scores["readability"] < 40:
            feedback.append(EssayFeedbackItem(
                category="Readability", severity="info",
                comment="Matn murakkab tuzilishga ega — bu ilg'or daraja uchun yaxshi, lekin haddan tashqari murakkab jumlalar tushunishni qiyinlashtirishi mumkin.",
            ))

        if metrics.word_count < target_word_count * 0.85:
            feedback.append(EssayFeedbackItem(
                category="Word Count", severity="warning",
                comment=f"Insho {metrics.word_count} so'zdan iborat, maqsad esa {target_word_count} so'z edi. Fikrlaringizni ko'proq misollar bilan kengaytiring.",
            ))
        elif metrics.word_count > target_word_count * 1.3:
            feedback.append(EssayFeedbackItem(
                category="Word Count", severity="info",
                comment=f"Insho {metrics.word_count} so'zdan iborat — maqsaddan ({target_word_count}) sezilarli uzunroq. Asosiy fikrlarga jamlanib, ortiqcha takrorlardan saqlaning.",
            ))

        if not strengths:
            strengths.append("Insho topshirilgan va tahlil qilindi — asosiy ko'rsatkichlarni yaxshilash ustida ishlang.")
        if not weaknesses:
            weaknesses.append("Aniq zaif tomon topilmadi — barcha ko'rsatkichlar qoniqarli darajada.")

        return EssayScoreOut(
            session_id=session_id,
            word_count=metrics.word_count,
            target_word_count=target_word_count,
            overall_score=overall,
            estimated_cefr=_estimate_cefr(overall),
            sub_scores=sub_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            feedback=feedback,
            graded_by="heuristic-engine-v1",
        )
