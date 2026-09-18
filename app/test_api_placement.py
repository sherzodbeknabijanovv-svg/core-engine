import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_BANK_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "question_bank.json"


def _answer_key() -> dict[str, int]:
    raw = json.loads(_BANK_PATH.read_text(encoding="utf-8"))
    key = {}
    for section, tiers in raw.items():
        for tier, items in tiers.items():
            for item in items:
                key[item["id"]] = item["correct"]
    return key


def _complete_test_session() -> str:
    key = _answer_key()
    r = client.post("/api/v1/placement/start")
    data = r.json()
    session_id = data["session_id"]
    q = data["first_question"]
    finished = False
    while not finished:
        r = client.post("/api/v1/placement/answer", json={
            "session_id": session_id, "question_id": q["id"], "selected_index": key[q["id"]],
        })
        step = r.json()
        finished = step["finished"]
        if not finished:
            q = step["next_question"]
    return session_id


def test_health_check():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_start_session_returns_first_question():
    r = client.post("/api/v1/placement/start")
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["first_question"]["section"] == "grammar_vocab"
    assert data["first_question"]["difficulty"] == "medium"


def test_answer_endpoint_returns_next_question():
    r = client.post("/api/v1/placement/start")
    data = r.json()
    session_id, q = data["session_id"], data["first_question"]

    key = _answer_key()
    r2 = client.post("/api/v1/placement/answer", json={
        "session_id": session_id, "question_id": q["id"], "selected_index": key[q["id"]],
    })
    assert r2.status_code == 200
    assert r2.json()["finished"] is False
    assert r2.json()["next_question"] is not None


def test_answer_with_bad_session_returns_404():
    r = client.post("/api/v1/placement/answer", json={
        "session_id": "nonexistent", "question_id": "gv-e1", "selected_index": 0,
    })
    assert r.status_code == 404


def test_full_flow_essay_and_roadmap():
    session_id = _complete_test_session()

    essay_text = (
        "Learning a new language requires consistent daily practice and genuine curiosity "
        "about the culture behind it. Many students focus only on grammar rules, but real "
        "fluency comes from using the language in authentic situations, such as conversations "
        "with native speakers or watching films without subtitles. " * 3
    )
    r = client.post("/api/v1/placement/essay", json={"session_id": session_id, "essay_text": essay_text})
    assert r.status_code == 200
    essay_data = r.json()
    assert essay_data["graded_by"] == "heuristic-engine-v1"
    assert 0 <= essay_data["overall_score"] <= 100

    r2 = client.get(f"/api/v1/placement/roadmap/{session_id}")
    assert r2.status_code == 200
    roadmap = r2.json()
    assert roadmap["overall_level"] in ("A2", "B1", "B2", "C1")
    assert roadmap["essay_score"] == essay_data["overall_score"]
    assert len(roadmap["weekly_plan"]) == 7


def test_roadmap_pdf_endpoint_returns_valid_pdf():
    session_id = _complete_test_session()
    r = client.get(f"/api/v1/placement/roadmap/{session_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_essay_too_short_is_rejected_by_validation():
    r = client.post("/api/v1/placement/start")
    session_id = r.json()["session_id"]
    r2 = client.post("/api/v1/placement/essay", json={"session_id": session_id, "essay_text": "too short"})
    assert r2.status_code == 422  # Pydantic min_length validatsiyasi ishlashi kerak


def test_roadmap_for_unknown_session_returns_404():
    r = client.get("/api/v1/placement/roadmap/does-not-exist")
    assert r.status_code == 404
