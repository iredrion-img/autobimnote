# AutoBIMNote (BIM 이슈 보고서 자동화 SaaS)

> 건화기술연구소(Kunhwa R&D) | ISO 19650 / MOLIT BIM 가이드라인 준수

BIM 이슈 보고서(HWPX)를 자동으로 생성하는 FastAPI 기반 SaaS 플랫폼입니다.

## 핵심 기능

| 기능 | 설명 |
|---|---|
| **HWPX 자동 생성** | 템플릿 기반 텍스트 치환 + 이미지 교체 → ZIP 재패킹 |
| **비동기 처리** | BackgroundTasks로 보고서 생성, DB 상태(pending/done/error) 관리 |
| **하이브리드 환경** | 로컬(SQLite/LocalFS) ↔ 운영(PostgreSQL/GCS) 자동 스위칭 |
| **Google OAuth** | Authlib + Starlette Session (DEV 모드 바이패스 포함) |
| **GCS 서명 URL** | 15분 유효 다운로드 링크 자동 발급 |

## 프로젝트 구조

```
autobimnote/
├── app/
│   ├── auth/          # Google OAuth 2.0 + DEV 바이패스
│   ├── core/          # config, database, storage 추상 레이어
│   ├── reports/       # router, service, schemas, models
│   └── templates/     # Jinja2 HTML (index, history, base)
├── engine/
│   └── xml_manager.py # HWPX 엔진 v1.1
├── scripts/
│   └── smoke_test.py  # 서버 없이 엔진 검증
├── templates_hwpx/    # HWPX 템플릿 (.gitignore 대상)
├── tests/
│   └── test_engine_integration.py
├── main.py            # FastAPI 진입점
├── requirements.txt
├── Dockerfile         # Cloud Run 배포용
└── .env.example       # 환경변수 템플릿
```

## 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/iredrion-img/autobimnote.git
cd autobimnote

# 2. 가상환경 생성 및 패키지 설치
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. 환경변수 설정
copy .env.example .env
# .env 파일 내 값 확인 (DEBUG=true → OAuth 바이패스)

# 4. HWPX 템플릿 배치
# templates_hwpx/template.hwpx 에 이슈보고서 양식 파일 복사

# 5. 엔진 스모크 테스트
python scripts/smoke_test.py

# 6. 서버 실행
python -m uvicorn main:app --reload
# → http://localhost:8000
```

## 팀 협업 가이드

### 브랜치 전략 (Git Flow)

| 브랜치 | 용도 |
|---|---|
| `main` | 배포 가능한 안정 버전 |
| `develop` | 개발 통합 브랜치 |
| `feature/*` | 기능 개발 (예: `feature/image-upload`) |
| `fix/*` | 버그 수정 (예: `fix/lineseg-cache`) |

### 작업 흐름

```
1. develop에서 feature 브랜치 생성
   git checkout develop
   git checkout -b feature/my-feature

2. 작업 후 커밋
   git add .
   git commit -m "feat: 이미지 업로드 기능 추가"

3. develop에 PR (Pull Request) 생성
   → 코드 리뷰 후 머지

4. 배포 시 develop → main 머지
```

### 커밋 메시지 규칙

```
feat:     새 기능
fix:      버그 수정
docs:     문서 변경
style:    코드 포맷 (기능 변경 없음)
refactor: 리팩토링
test:     테스트 추가/수정
chore:    빌드, 설정 변경
```

## 환경변수

`.env.example` 참고. 주요 설정:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DEBUG` | `true` | 개발 모드 (OAuth 바이패스) |
| `DATABASE_URL` | (빈값→SQLite) | PostgreSQL URL |
| `USE_GCS` | `false` | GCS 사용 여부 |
| `TEMPLATE_PATH` | `templates_hwpx/template.hwpx` | HWPX 템플릿 경로 |

## 라이선스

Copyright © 2026 건화기술연구소 (Kunhwa R&D). All rights reserved.
