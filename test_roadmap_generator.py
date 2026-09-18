from app.models.schemas import CEFRLevel, Difficulty, Section
from app.services.roadmap_generator import generate_roadmap
from app.services.session_store import AnsweredQuestion, SessionState


def _make_state_with_scores(gv_correct: int, ls_correct: int, rd_correct: int, essay_score: float | None = None) -> SessionState:
    state = SessionState(session_id="test-session")

    def fill(section: Section, total: int, correct: int):
        answers = []
        for i in range(total):
            answers.append(AnsweredQuestion(
                question_id=f"{section.value}-{i}",
                difficulty=Difficulty.medium,
                selected_index=0,
                correct=(i < correct),
            ))
        state.answers[section] = answers

    fill(Section.grammar_vocab, 15, gv_correct)
    fill(Section.listening, 10, ls_correct)
    fill(Section.reading, 15, rd_correct)

    if essay_score is not None:
        state.essay_result = {"overall_score": essay_score}
    return state


def test_perfect_scores_yield_c1():
    state = _make_state_with_scores(15, 10, 15, essay_score=95.0)
    roadmap = generate_roadmap(state)
    assert roadmap.overall_level == CEFRLevel.c1
    assert roadmap.overall_score_percent > 85


def test_low_scores_yield_a2():
    state = _make_state_with_scores(2, 1, 2, essay_score=15.0)
    roadmap = generate_roadmap(state)
    assert roadmap.overall_level == CEFRLevel.a2


def test_weak_areas_identifies_lowest_scoring_sections():
    # Reading juda past, qolganlari yaxshi
    state = _make_state_with_scores(gv_correct=14, ls_correct=9, rd_correct=3, essay_score=85.0)
    roadmap = generate_roadmap(state)
    weak_labels = [w.section for w in roadmap.weak_areas]
    assert "Reading" in weak_labels


def test_no_weak_areas_when_everything_is_strong():
    state = _make_state_with_scores(15, 10, 15, essay_score=90.0)
    roadmap = generate_roadmap(state)
    assert roadmap.weak_areas == []


def test_weekly_plan_has_seven_days_at_90_minutes():
    state = _make_state_with_scores(10, 7, 10, essay_score=70.0)
    roadmap = generate_roadmap(state)
    assert len(roadmap.weekly_plan) == 7
    assert all(day.duration_minutes == 90 for day in roadmap.weekly_plan)
    assert roadmap.daily_study_minutes == 90


def test_roadmap_works_without_essay_submitted():
    state = _make_state_with_scores(12, 8, 11, essay_score=None)
    roadmap = generate_roadmap(state)
    assert roadmap.essay_score is None
    assert roadmap.overall_score_percent > 0
