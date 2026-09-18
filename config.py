"""
Ilova sozlamalari — barchasi .env fayldan yoki muhit o'zgaruvchilaridan
o'qiladi. Hech qaysi maxfiy qiymat kodga qattiq yozilmagan (hardcode
qilinmagan).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # essay_grader: "heuristic" (standart, kalit talab qilmaydi) yoki "openai"
    # (GPT-4o orqali baholaydi, OPENAI_API_KEY shart).
    essay_grader: str = "heuristic"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # Har bir insho uchun maqsadli so'zlar soni (roadmap'da og'ish % shundan hisoblanadi)
    essay_target_word_count: int = 300

    app_name: str = "EduStimul Core Engine"
    app_version: str = "1.0.0"
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
