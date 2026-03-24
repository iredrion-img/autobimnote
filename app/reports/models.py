"""
app/reports/models.py – SQLAlchemy ORM model for BIM report jobs.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # BIM 도메인 필드
    structure_name:    Mapped[str] = mapped_column(String(512), nullable=False)
    discipline:        Mapped[str] = mapped_column(String(256), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    img_1_title:       Mapped[str] = mapped_column(String(256), nullable=False, default="이미지 1")
    img_2_title:       Mapped[str] = mapped_column(String(256), nullable=False, default="이미지 2")

    # 상태 관리
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )  # pending | done | error

    # 저장 경로 (로컬 절대경로 또는 gs://... )
    gcs_path: Mapped[str] = mapped_column(Text, nullable=True)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
