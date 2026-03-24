"""
app/core/config.py
==================
pydantic-settings 기반 환경변수 관리.

LOCAL 개발 (USE_GCS=false, SQLite):
  - DATABASE_URL 미설정 시 자동으로 SQLite 사용
  - 파일 저장: 로컬 output/ 디렉터리

GCS + Cloud SQL (프로덕션):
  - DATABASE_URL=postgresql+asyncpg://...
  - USE_GCS=true + GCS_BUCKET_NAME 설정
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── 보안 ──────────────────────────────────
    SECRET_KEY: str = "dev-secret-change-this-in-production-32chars"

    # ── 개발 모드 ─────────────────────────────
    DEBUG: bool = True
    ALLOWED_ORIGIN: str = "http://localhost:8000"

    # ── Google OAuth ──────────────────────────
    GOOGLE_CLIENT_ID: str     = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str  = "http://localhost:8000/auth/callback"

    # ── DB ────────────────────────────────────
    # 미설정 시 → 로컬 SQLite (aiosqlite)
    # 프로덕션 → postgresql+asyncpg://user:pass@host/db
    DATABASE_URL: str = ""

    @property
    def resolved_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # 로컬 SQLite 자동 사용
        db_path = Path("bim_reporter.db").resolve()
        return f"sqlite+aiosqlite:///{db_path}"

    # ── 스토리지 ──────────────────────────────
    # USE_GCS=false → 로컬 디렉터리 사용
    USE_GCS: bool          = False
    GCS_BUCKET_NAME: str   = "bim-reporter-files"
    GCS_PROJECT_ID: str    = ""
    LOCAL_OUTPUT_DIR: str  = "output"   # USE_GCS=false 일 때 파일 저장 경로

    # ── HWPX 엔진 ─────────────────────────────
    TEMPLATE_PATH: str = "templates_hwpx/template.hwpx"
    OUTPUT_TMP_DIR: str = "/tmp/bim_output"


settings = Settings()
