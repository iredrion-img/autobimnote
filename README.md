[🇬🇧 English](README.md) | [🇰🇷 한국어(Korean)](README_ko.md)

# AutoBIMNote (BIM Issue Report Automation SaaS)

> Kunhwa R&D | ISO 19650 / MOLIT BIM Guidelines Compliant

A FastAPI-based SaaS platform that automatically generates BIM issue reports (HWPX format).

## Core Features

| Feature | Description |
|---|---|
| **Auto HWPX Generation** | Template-based text replacement + image embedding → ZIP repacking |
| **Asynchronous Processing** | BackgroundTasks for report generation, DB status (pending/done/error) tracking |
| **Hybrid Environment** | Auto-switching between Local (SQLite/LocalFS) ↔ Production (PostgreSQL/GCS) |
| **Google OAuth** | Authlib + Starlette Session (Includes DEV mode bypass) |
| **GCS Signed URLs** | Auto-issued 15-minute valid download links |

## Project Structure

```
autobimnote/
├── app/
│   ├── auth/          # Google OAuth 2.0 + DEV bypass
│   ├── core/          # config, database, storage abstraction layers
│   ├── reports/       # router, service, schemas, models
│   └── templates/     # Jinja2 HTML (index, history, base)
├── engine/
│   └── xml_manager.py # HWPX engine v1.1
├── scripts/
│   └── smoke_test.py  # Headless engine verification
├── templates_hwpx/    # HWPX Template directory (ignored in git)
├── tests/
│   └── test_engine_integration.py
├── main.py            # FastAPI entry point
├── requirements.txt
├── Dockerfile         # Cloud Run deployment
└── .env.example       # Environment variables template
```

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/iredrion-img/autobimnote.git
cd autobimnote

# 2. Virtual environment and dependencies
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. Environment variables
copy .env.example .env
# Ensure DEBUG=true for OAuth bypass in local dev

# 4. HWPX Template setup
# Place your HWPX template in templates_hwpx/template.hwpx

# 5. Engine smoke test
python scripts/smoke_test.py

# 6. Run server
python -m uvicorn main:app --reload
# → http://localhost:8000
```

## Team Collaboration Guide

### Branching Strategy (Git Flow)

| Branch | Purpose |
|---|---|
| `main` | Stable, deployable version |
| `develop` | Integration branch for development |
| `feature/*` | Feature development (e.g., `feature/image-upload`) |
| `fix/*` | Bug fixes (e.g., `fix/lineseg-cache`) |

### Workflow

```
1. Create a feature branch from develop
   git checkout develop
   git checkout -b feature/my-feature

2. Commit your changes
   git add .
   git commit -m "feat: add image upload feature"

3. Create PR (Pull Request) into develop
   → Code review and merge

4. Merge develop → main when deploying
```

### Commit Message Conventions

```
feat:     New feature
fix:      Bug fix
docs:     Documentation changes
style:    Code formatting (no functional changes)
refactor: Code refactoring
test:     Add or modify tests
chore:    Build, configuration changes
```

## Environment Variables

See `.env.example`. Key configurations:

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `true` | Dev mode (OAuth bypass ON) |
| `DATABASE_URL` | (Empty→SQLite) | PostgreSQL URL |
| `USE_GCS` | `false` | Enable/Disable GCS |
| `TEMPLATE_PATH` | `templates_hwpx/template.hwpx` | HWPX Template path |

## License

Copyright © 2026 Kunhwa R&D. All rights reserved.
