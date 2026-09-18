from app.services.essay_graders.heuristic import HeuristicEssayGrader

GOOD_ESSAY = (
    "Technology has fundamentally transformed the way students learn English today. "
    "With mobile applications and interactive platforms, learners now access authentic "
    "materials from around the world. This shift has made language acquisition more "
    "flexible, allowing students to study at their own pace. However, this abundance of "
    "resources also presents challenges. Many students struggle to maintain discipline "
    "without the structure of a classroom. Furthermore, technology excels at teaching "
    "vocabulary through repetition, but it often falls short in developing genuine "
    "conversational fluency, which still requires real human interaction. In conclusion, "
    "technology should be viewed as a complement to traditional instruction rather than a "
    "complete replacement for it."
)

REPETITIVE_ESSAY = "The cat is good. The cat is good. The cat is good. " * 20

SHORT_ESSAY = "I like English very much because it is fun and useful for my future career plans."


def test_grader_returns_deterministic_score_for_same_input():
    grader = HeuristicEssayGrader()
    r1 = grader.grade("s1", GOOD_ESSAY, target_word_count=300)
    r2 = grader.grade("s1", GOOD_ESSAY, target_word_count=300)
    assert r1.overall_score == r2.overall_score
    assert r1.sub_scores == r2.sub_scores


def test_grader_penalizes_repetitive_vocabulary():
    grader = HeuristicEssayGrader()
    good = grader.grade("s1", GOOD_ESSAY, target_word_count=300)
    repetitive = grader.grade("s2", REPETITIVE_ESSAY, target_word_count=300)
    assert repetitive.sub_scores["vocabulary_richness"] < good.sub_scores["vocabulary_richness"]


def test_grader_flags_short_essay_in_feedback():
    grader = HeuristicEssayGrader()
    result = grader.grade("s3", SHORT_ESSAY, target_word_count=300)
    assert result.word_count < 300
    categories = [f.category for f in result.feedback]
    assert "Word Count" in categories


def test_grader_detects_misspelled_words():
    grader = HeuristicEssayGrader()
    misspelled_text = "I beleive that recieveing a good eduction is very importent for sucess in life. " * 4
    result = grader.grade("s4", misspelled_text, target_word_count=300)
    assert result.sub_scores["grammar_accuracy"] < 100
    assert any(f.category == "Spelling" for f in result.feedback)


def test_grader_output_score_within_bounds():
    grader = HeuristicEssayGrader()
    for text in (GOOD_ESSAY, REPETITIVE_ESSAY, SHORT_ESSAY):
        result = grader.grade("s5", text, target_word_count=300)
        assert 0 <= result.overall_score <= 100
        for sub_score in result.sub_scores.values():
            assert 0 <= sub_score <= 100


def test_grader_marked_as_heuristic_engine():
    grader = HeuristicEssayGrader()
    result = grader.grade("s6", GOOD_ESSAY, target_word_count=300)
    assert result.graded_by == "heuristic-engine-v1"


def test_grader_rejects_never_crashes_on_empty_ish_text():
    grader = HeuristicEssayGrader()
    result = grader.grade("s7", "Hello world. This is a test essay for length checking only right now.", target_word_count=300)
    assert result.word_count > 0
