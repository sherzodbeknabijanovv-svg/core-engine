"""
Roadmap generator — test bo'limlari va insho ballarini birlashtirib,
umumiy daraja (CEFR), zaif tomonlar va kunlik 1.5 soatlik haftalik
o'quv rejasini hosil qiladi. Natija to'liq structured (Pydantic)
JSON — shu bilan birga PDF holida ham eksport qilinishi mumkin
(pdf_generator.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import CEFRLevel, RoadmapOut, Section, StudyDayPlan, WeakArea
from app.services.session_store import SessionState

DAILY_STUDY_MINUTES = 90  # 1.5 soat

_SECTION_LABELS = {
    Section.grammar_vocab: "Grammar & Vocabulary",
    Section.listening: "Listening",
    Section.reading: "Reading",
}


def _overall_score(section_scores: dict[Section, float], essay_score: float | None) -> float:
    test_avg = sum(section_scores.values()) / len(section_scores) if section_scores else 0.0
    if essay_score is None:
        return round(test_avg, 1)
    # Test 70%, insho 30% — insho yozma ko'nikmani, test esa grammatika/eshitish/o'qishni o'lchaydi
    return round(test_avg * 0.7 + essay_score * 0.3, 1)


def _level_from_score(score: float) -> CEFRLevel:
    if score < 40:
        return CEFRLevel.a2
    if score < 65:
        return CEFRLevel.b1
    if score < 85:
        return CEFRLevel.b2
    return CEFRLevel.c1


def _weak_areas(section_scores: dict[Section, float], essay_score: float | None) -> list[WeakArea]:
    all_scores: list[tuple[str, float]] = [
        (_SECTION_LABELS[s], score) for s, score in section_scores.items()
    ]
    if essay_score is not None:
        all_scores.append(("Essay Writing", essay_score))

    all_scores.sort(key=lambda x: x[1])
    weak = []
    for label, score in all_scores:
        if score < 70:  # 70% dan past — "e'tibor talab qiladi" chegarasi
            note = (
                f"{label} bo'yicha natija {score}% — bu yo'nalishga qo'shimcha vaqt ajratish tavsiya etiladi."
                if score >= 40 else
                f"{label} bo'yicha natija past ({score}%) — asosdan boshlab mustahkamlash kerak."
            )
            weak.append(WeakArea(section=label, score_percent=score, note=note))
    return weak[:3]  # eng zaif 3 tasi yetarli — roadmap haddan tashqari uzun bo'lib ketmasin


def _build_weekly_plan(weak_areas: list[WeakArea], essay_score: float | None) -> list[StudyDayPlan]:
    weak_labels = [w.section for w in weak_areas]
    plan: list[StudyDayPlan] = []

    day_templates = [
        ("1-kun", "Grammar & Vocabulary", [
            "20 ta grammatika mashqini bajaring (fokus: eng ko'p xato qilingan mavzu)",
            "15 ta yangi so'zni misollar bilan yodlang",
            "O'rganilgan so'zlarni ishlatib 5 ta gap tuzing",
        ]),
        ("2-kun", "Listening", [
            "15 daqiqalik ingliz tilidagi audio/podcast tinglang",
            "Tinglab, asosiy fikrlarni o'zbek tilida qisqacha yozing",
            "Tushunmagan 5 ta so'zni lug'atga yozib oling",
        ]),
        ("3-kun", "Reading", [
            "300-400 so'zli ingliz tilidagi matn o'qing (SAT-style)",
            "Matn bo'yicha 5 ta savolga javob bering",
            "Yangi uchragan so'zlarni belgilab, ma'nosini toping",
        ]),
        ("4-kun", "Essay Writing", [
            "300 so'zlik insho yozing (berilgan mavzu bo'yicha)",
            "Insho tuzilishini tekshiring: kirish - asosiy qism - xulosa",
            "O'zingiz yozgan inshoni ovoz chiqarib o'qib, xatolarni toping",
        ]),
        ("5-kun", "Grammar & Vocabulary", [
            "1-kunda xato qilingan mavzuni qayta mustahkamlang",
            "10 ta yangi so'zni takrorlang (spaced repetition)",
            "Mini-test: 10 ta grammatika savoli",
        ]),
        ("6-kun", "Mixed Practice", [
            "Listening + Reading aralash mashqi (30 daqiqa)",
            "Xato qilingan savollarni qayta ko'rib chiqing",
        ]),
        ("7-kun", "Review & Rest", [
            "Hafta davomida yozgan barcha eslatmalarni qayta o'qing",
            "Eng qiyin bo'lgan 5 ta savol/mavzuni belgilab qo'ying",
            "Yengil tinglash yoki o'qish bilan cheklaning — dam oling",
        ]),
    ]

    for day_label, focus, tasks in day_templates:
        # Agar shu fokus zaif tomonlar orasida bo'lsa — mashqlar sonini ko'paytiramiz
        is_weak_focus = any(focus in label for label in weak_labels)
        final_tasks = list(tasks)
        if is_weak_focus:
            final_tasks.append("(Zaif tomon) — bugun shu mavzuga qo'shimcha 15 daqiqa ajrating.")
        plan.append(StudyDayPlan(
            day_label=day_label,
            focus=focus,
            tasks=final_tasks,
            duration_minutes=DAILY_STUDY_MINUTES,
        ))
    return plan


def _summary_text(level: CEFRLevel, overall: float, weak_areas: list[WeakArea]) -> str:
    if not weak_areas:
        weak_part = "aniq zaif tomon aniqlanmadi — barcha yo'nalishlarda barqaror natija."
    else:
        weak_part = "asosiy e'tibor talab qiladigan yo'nalishlar: " + ", ".join(w.section for w in weak_areas) + "."
    return (
        f"Umumiy daraja: {level.value} ({overall}%). Kuniga {DAILY_STUDY_MINUTES} daqiqa "
        f"(1.5 soat) muntazam shug'ullanish tavsiya etiladi. {weak_part}"
    )


def generate_roadmap(state: SessionState) -> RoadmapOut:
    section_scores = {
        section: state.section_score_percent(section)
        for section in (Section.grammar_vocab, Section.listening, Section.reading)
        if state.answers.get(section)
    }
    essay_score = state.essay_result["overall_score"] if state.essay_result else None

    overall = _overall_score(section_scores, essay_score)
    level = _level_from_score(overall)
    weak_areas = _weak_areas(section_scores, essay_score)
    weekly_plan = _build_weekly_plan(weak_areas, essay_score)

    return RoadmapOut(
        session_id=state.session_id,
        generated_at=datetime.now(timezone.utc),
        overall_level=level,
        overall_score_percent=overall,
        section_scores={_SECTION_LABELS[s]: v for s, v in section_scores.items()},
        essay_score=essay_score,
        weak_areas=weak_areas,
        daily_study_minutes=DAILY_STUDY_MINUTES,
        weekly_plan=weekly_plan,
        summary=_summary_text(level, overall, weak_areas),
    )
