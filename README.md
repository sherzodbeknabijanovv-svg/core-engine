# EduStimul Core Engine

**Level Placement Test & AI Roadmap microservice** — 40-question adaptive
English placement test (Grammar & Vocabulary, Listening, Reading) plus a
300-word essay, producing a personalized study roadmap (JSON + PDF).

Built as a standalone Python microservice, independent from the main
EduStimul Node.js platform — communicates over a clean REST API.

---

## Architecture

```
                         ┌─────────────────────────────┐
                         │   EduStimul Node.js App      │
                         │  (existing student platform) │
                         └──────────────┬───────────────┘
                                         │ HTTP (REST)
                                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                     edustimul-core-engine (FastAPI)                 │
│                                                                       │
│  ┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐   │
│  │  routers/      │──▶│  services/        │──▶│  models/          │  │
│  │  placement.py  │   │  test_scorer.py   │   │  schemas.py       │  │
│  │  (API layer)   │   │  question_bank.py │   │  (Pydantic v2)    │  │
│  │                │   │  session_store.py │   │                   │  │
│  │                │   │  roadmap_generator│   │                   │  │
│  │                │   │  pdf_generator.py │   │                   │  │
│  └───────────────┘   └─────────┬─────────┘   └──────────────────┘   │
│                                  │                                    │
│                     ┌────────────┴─────────────┐                     │
│                     │   essay_graders/           │                    │
│                     │   base.py    (interface)   │                    │
│                     │   heuristic.py (default)   │◀── no API key      │
│                     │   openai_grader.py         │◀── GPT-4o,         │
│                     │   grader_factory.py         │    needs key       │
│                     └────────────────────────────┘                    │
└────────────────────────────────────────────────────────────────────┘
```

**Key design decision — pluggable essay grading (Strategy pattern):**
`EssayGrader` is an abstract interface with two implementations:
`HeuristicEssayGrader` (statistical/linguistic analysis — works today,
no external API) and `OpenAIEssayGrader` (GPT-4o Structured Outputs —
ready to use once an API key is added). Swapping between them is a
single config change (`ESSAY_GRADER=heuristic|openai` in `.env`) —
nothing else in the codebase changes.

---

## Tech stack

| Layer            | Choice                                              |
|-------------------|------------------------------------------------------|
| API framework      | FastAPI                                              |
| Validation / DTOs  | Pydantic v2 (Structured Output-ready)                |
| AI grading (optional) | OpenAI GPT-4o via Structured Outputs             |
| Heuristic grading  | `pyspellchecker` (spelling), `textstat` (readability), custom NLP-lite metrics |
| PDF generation     | ReportLab                                            |
| Testing            | pytest + FastAPI `TestClient` (36 tests, all offline)|
| API docs           | Swagger UI (auto, at `/docs`) + Postman collection    |
| Config             | `pydantic-settings` (.env driven, no hardcoded secrets) |

---

## Setup guide

```bash
cd edustimul-core-engine
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # standart holida ESSAY_GRADER=heuristic — kalit shart emas

uvicorn app.main:app --reload --port 8000
```

Ochish:
- API: `http://localhost:8000`
- Interaktiv Swagger hujjatlar: `http://localhost:8000/docs`
- Postman: `postman/edustimul-core-engine.postman_collection.json` ni Postman'ga import qiling

### GPT-4o'ni keyinroq yoqish

1. `.env` faylida: `OPENAI_API_KEY=sk-...` va `ESSAY_GRADER=openai`
2. Serverni qayta ishga tushiring — boshqa hech narsa o'zgartirish shart emas.

> **Eslatma:** `OpenAIEssayGrader` kodi tayyor va to'g'ri yozilgan (OpenAI'ning
> rasmiy Structured Outputs andozasiga mos), lekin men buni o'z ishlash
> muhitimda haqiqiy API chaqiruvi bilan sinamadim (tashqi tarmoqqa
> ulanish cheklangan). Kalitni qo'shgach, birinchi chaqiruvni albatta
> qo'lda tekshirib ko'ring.

---

## Testlarni ishga tushirish

```bash
pytest -v
```

36 ta test — barchasi tarmoqqa chiqmasdan, to'liq offline ishlaydi
(heuristik grader OpenAI kalitisiz ham to'liq sinaladi).

---

## API payloadlari (qisqacha)

### `POST /api/v1/placement/start`
→ `{ session_id, first_question, progress }`

### `POST /api/v1/placement/answer`
```json
{ "session_id": "...", "question_id": "gv-m2", "selected_index": 1 }
```
→ `{ finished, section_finished, next_question, progress }`

### `POST /api/v1/placement/essay`
```json
{ "session_id": "...", "essay_text": "At least 50 characters..." }
```
→ `{ overall_score, estimated_cefr, sub_scores, strengths, weaknesses, feedback, graded_by }`

### `GET /api/v1/placement/roadmap/{session_id}`
→ to'liq structured JSON: `overall_level`, `section_scores`, `weak_areas`, `weekly_plan` (7 kun × 90 daqiqa)

### `GET /api/v1/placement/roadmap/{session_id}/pdf`
→ shu roadmap'ning yuklab olinadigan PDF fayli

To'liq so'rov/javob sxemalari va misollar: `/docs` (Swagger) yoki
`postman/` papkasidagi kolleksiya.

---

## Ma'lum cheklovlar (production uchun eslatmalar)

- **Sessiya saqlash** hozircha xotirada (in-memory dict) — demo/portfolio
  uchun yetarli, lekin production uchun Redis yoki DB'ga ko'chirilishi kerak
  (server qayta ishga tushganda sessiyalar yo'qoladi).
- **Adaptive test** — soddalashtirilgan (bir pog'onali) qiyinlik moslashuvi;
  IRT (Item Response Theory) kabi murakkabroq modellarga kengaytirilishi mumkin.
- **Listening** bo'limi hozircha matn transkripti bilan ishlaydi (haqiqiy
  audio fayl infratuzilmasi yo'q) — production versiyada `audio_transcript`
  o'rniga audio fayl URL qo'shiladi.
- **Savollar banki** — 55 ta savol (har bir bo'lim uchun bitta test
  o'tishga yetarli pool bilan). Ko'proq turli-tuman testlar kerak bo'lsa,
  `app/data/question_bank.json`ga yangi savollar qo'shish kifoya —
  kod o'zgarishi shart emas.
