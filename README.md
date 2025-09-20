# FocusPoint

**FocusPoint** is a self-hosted simple progress tracker.  
It complements your calendar tool by answering two questions:

1) **How am I investing my time?**  
2) **How are my projects advancing over weeks/months/years?**

It is not focused as calendar or todo app. It is designed to be a general guide more than a concret action plan.

---

## Features 

### Core entities
- **Categories**  
  High-level buckets (e.g., *Studies*, *Work*, *Personal*). Projects belong to a Category.

- **Projects**  
  The unit of planning. Each project has:
  - Name, objective, **end date** (DD/MM/YYYY)
  - Multiple **milestones** (each with percent complete and end date)
  - Optional milestone **dependencies** (advisory: they don’t block percentages, but are visualized)

- **Milestones**  
  Steps toward the project objective:
  - Fields: name, end date, percent complete (0–100), optional notes
  - Optional **Dependent to** another milestone (for visualization)
  - Progress is **averaged equally** across milestones (v1)

- **Actions**  
  Daily time entries you add quickly:
  - Project → Milestone (autocomplete), **time HH:MM**, optional comment, date (DD/MM/YYYY)
  - Stored as minutes internally, always shown as **HH:MM**

### Tabs (UI)
- **Add Action**  
  Fast day selector (`<< Yesterday | Today (calendar) | >> Tomorrow`) + “Add action” box + today’s actions list.

- **Categories**  
  Create/edit/delete categories. Shows projects inside a category.

- **Projects**  
  List view and **Node view** (milestones as nodes, **visible arrows** for dependencies).  
  You can add/edit projects and milestones; editing preloads current values.

- **Week Reviews**  
  Monday-based week. Edit milestone percentages/notes for the week; mark review as “done” (badge resets weekly).

- **Reports**  
  **Weekly / Monthly / Yearly** PDF:
  - Compact **KPI** cards (2×3 layout) for totals, active days, averages, top shares, streaks
  - Clean bar charts (auto-fit) for period totals
  - **Top projects**, with overdue/at-risk counts
  - **By category** totals
  - **Overdue** and **Upcoming** milestones (lookahead tuned per period)
  - **GTD suggestions** (focus nudges based on progress/time patterns)

### Conventions
- **Dates:** `DD/MM/YYYY`
- **Time:** `HH:MM` (no decimals)
- **Week start:** Monday (Europe/Madrid)
- **Auth:** Single user login (hashed password). CSRF protected forms.
- **REST:** Clean endpoints under `/api/...` for future integrations.

---

## Screens (what to expect)

- **Left sidebar (hideable):** Add Action, Categories, Projects, Week Reviews, Reports (bottom: Settings, Log out)
- **Obsidian-ish dark theme:** purple/grey/black accents; modern but minimal
- **Node view:** reliable dependency arrows (configured to be high-contrast)

---

## Getting started

### 1) Prepare environment

```bash
cp .env.example .env
# Edit values if needed:
# APP_NAME=FocusPoint
# SECRET_KEY=change-me
# DATABASE_URL=postgresql+psycopg2://focuspoint:focuspoint@db:5432/focuspoint
````

### 2) Docker Compose (PostgreSQL + FastAPI)

> Your `docker-compose.yml` should be similar to this:

```yaml
version: "3.9"

services:
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: focuspoint
      POSTGRES_USER: focuspoint
      POSTGRES_PASSWORD: focuspoint
      TZ: Europe/Madrid
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U focuspoint -d focuspoint"]
      interval: 5s
      timeout: 3s
      retries: 10

  web:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: ${DATABASE_URL}
      APP_NAME: ${APP_NAME}
      SECRET_KEY: ${SECRET_KEY}
      TZ: Europe/Madrid
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app/reports:/app/app/reports  # generated PDFs
      - ./backend/app/static:/app/app/static:ro # static files (optional)

volumes:
  db_data:
```

### 3) Build & run

```bash
docker compose build web
docker compose up -d
# App at http://localhost:8000
```

### 4) Log in

* First run will prompt to create/set the single user (or you may already have a seeded user).
* Login UI: `/login`

---

## Data model (brief)

* `Category(id, name)`
* `Project(id, category_id, name, objective, end_date)`
* `Milestone(id, project_id, name, end_date, percent_complete, status, notes, depends_on_milestone_id?)`
* `Action(id, project_id, milestone_id, date, minutes, comment)`
* `ReportFile(id, period_type, period_start, period_end, file_path, created_at)`
* `User(id, username, password_hash, created_at)`

**Project progress** is the simple average of milestone percentages (equal weights).
**Dependencies** are advisory (v1): arrows shown; they don’t gate percentages.

---

## REST endpoints (selected)

* `POST /api/actions/add` — add an action (HH\:MM)
* `POST /api/projects/upsert` — create/update project
* `POST /api/milestones/upsert` — create/update milestone (optional dependency)
* `POST /api/categories/upsert` — create/update category
* `POST /api/reports/generate` — create a weekly/monthly/yearly PDF
* Most forms require a valid **CSRF** token.

*(Exact payloads live in `backend/app/schemas.py` and views in `backend/app/main.py`.)*

---

## Reports

* **Weekly:** daily bars, KPIs, top projects, overdue/upcoming (7d), suggestions
* **Monthly:** week-chunk bars (auto-fit), KPIs, by category, top projects, overdue/upcoming (14d), suggestions
* **Yearly:** monthly bars (auto-fit), KPIs, by category, top projects, overdue/upcoming (30d), suggestions
* **Style:** `backend/app/static/css/pdf.css` (print-optimized, modern theme)

---

## Technologies & why

* **FastAPI** (backend & server-rendered pages)
  Simple, fast, Pythonic. We keep deployment uncomplicated (no frontend build step).

* **Jinja2** (templates)
  Lightweight server rendering; easy to maintain and theme.

* **PostgreSQL**
  Solid transactional DB, well supported. We use SQLAlchemy 2.0 for ORM/queries.

* **WeasyPrint** (HTML → PDF)
  Stable CSS/print engine. Report templates are pure HTML/CSS with SVG bars (no headless browser).

* **Passlib\[bcrypt]**
  Password hashing with a battle-tested library.

* **vis-network (JS)**
  Node view for milestones + dependencies (clean, robust, arrow support).

* **dark theme**
  Familiar dark palette that stays readable in print.

---

## Configuration

* **APP\_NAME** — shown across the app and reports (default: *FocusPoint*)
* **SECRET\_KEY** — used for sessions/CSRF. **Change it** in `.env`.
* **DATABASE\_URL** — SQLAlchemy DSN; defaults to Docker service `db`.

**Formats**

* **Dates:** `DD/MM/YYYY` everywhere (UI + PDFs)
* **Time:** `HH:MM` only (no decimals in UI)

**Timezone**

* All services run with `TZ=Europe/Madrid`. Adjust if needed.

---

## Security notes

* Single-user authentication / session cookies
* CSRF token on all forms
* Bcrypt password hashing (via Passlib)
* No third-party tracking or external fonts
* HTTPS recommended via your reverse proxy (the app serves HTTP)

---

## Roadmap (future “must-dos” & ideas)

* CSV export for actions & project snapshots
* API tokens (for physical device time tracking)
* Better keyboard flow in Add Action (all from the keyboard)
* Multi-user (scoped categories/projects)
* Backups page (one-click dump/restore)
* Options and security (modify account, modify colors...)
* Improve nodes GUI


---

## License

TODO
