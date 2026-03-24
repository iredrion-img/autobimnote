"""
app/reports/schemas.py
======================
Pydantic 요청/응답 모델.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    structure_name:    str
    discipline:        str
    issue_description: str
    img_1_title:       str
    img_2_title:       str


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    structure_name:    str
    discipline:        str
    issue_description: str
    img_1_title:       str
    img_2_title:       str
    status:            str           # pending | done | error
    created_at:        datetime.datetime
    download_url:      Optional[str] = None  # 프론트 편의용 (done 상태일 때만)


class ReportStatusResponse(BaseModel):
    """폴링용 경량 응답."""
    id:     str
    status: str   # pending | done | error
