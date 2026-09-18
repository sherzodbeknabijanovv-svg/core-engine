from app.models.schemas import Difficulty, Section
from app.services.question_bank import QuestionBank, next_difficulty


def test_bank_loads_all_sections():
    bank = QuestionBank()
    for section in (Section.grammar_vocab, Section.listening, Section.reading):
        for tier in (Difficulty.easy, Difficulty.medium, Difficulty.hard):
            assert bank._by_section_tier.get((section, tier)), f"{section}/{tier} bo'sh bo'lmasligi kerak"


def test_pick_returns_question_from_requested_tier_when_available():
    bank = QuestionBank()
    item = bank.pick(Section.grammar_vocab, Difficulty.easy, exclude_ids=set())
    assert item is not None
    assert item["difficulty"] == "easy"
    assert item["section"] == "grammar_vocab"


def test_pick_excludes_already_asked_questions():
    bank = QuestionBank()
    seen = set()
    for _ in range(5):
        item = bank.pick(Section.reading, Difficulty.medium, exclude_ids=seen)
        assert item is not None
        assert item["id"] not in seen
        seen.add(item["id"])


def test_pick_falls_back_gracefully_when_tier_exhausted():
    bank = QuestionBank()
    # Listening 'hard' pool eng kichik (3 ta) — barchasini "so'ralgan" deb belgilaymiz
    hard_ids = {qid for qid in bank._by_section_tier[(Section.listening, Difficulty.hard)]}
    item = bank.pick(Section.listening, Difficulty.hard, exclude_ids=hard_ids)
    assert item is not None, "Tier tugaganda ham eng yaqin darajadan savol topilishi kerak"
    assert item["difficulty"] in ("medium", "easy")


def test_pick_returns_none_only_when_entire_section_exhausted():
    bank = QuestionBank()
    all_ids = set()
    for tier in (Difficulty.easy, Difficulty.medium, Difficulty.hard):
        all_ids |= set(bank._by_section_tier[(Section.listening, tier)])
    item = bank.pick(Section.listening, Difficulty.medium, exclude_ids=all_ids)
    assert item is None


def test_next_difficulty_increases_on_correct():
    assert next_difficulty(Difficulty.easy, was_correct=True) == Difficulty.medium
    assert next_difficulty(Difficulty.medium, was_correct=True) == Difficulty.hard


def test_next_difficulty_caps_at_hard():
    assert next_difficulty(Difficulty.hard, was_correct=True) == Difficulty.hard


def test_next_difficulty_decreases_on_incorrect():
    assert next_difficulty(Difficulty.hard, was_correct=False) == Difficulty.medium
    assert next_difficulty(Difficulty.medium, was_correct=False) == Difficulty.easy


def test_next_difficulty_floors_at_easy():
    assert next_difficulty(Difficulty.easy, was_correct=False) == Difficulty.easy
