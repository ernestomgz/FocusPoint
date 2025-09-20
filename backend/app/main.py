from pathlib import Path
from datetime import date
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from .crud import actions as ca   # ADD THIS
from .utils.formatting import parse_dmy, minutes_to_hhmm  # keep parse_dmy; minutes_to_hhmm optional

from .settings import settings
from .db import engine, Base, session_scope
from .models import User
from .security.auth import (
    login_user, logout_user, verify_password, current_user_id, bootstrap_admin
)
from .security.csrf import get_or_set_csrf, validate_csrf

from .crud import reports as cr
from .crud.actions import totals_by_day_range, totals_by_project_range, total_minutes_range
from .utils.dates import week_bounds, month_bounds, year_bounds
from .utils.formatting import parse_dmy, minutes_to_hhmm, dmy


# CRUD layers
from .crud import categories as cc
from .crud import projects as cp
from .crud import milestones as cm
from .crud import dependencies as cd
from .crud import reports as cr
from .utils.dates import week_bounds, month_bounds, year_bounds
from .utils.formatting import parse_dmy
from .utils.reporting import render_report_pdf

# --- App & FS
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie=settings.session_cookie_name)

static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
reports_dir = Path(__file__).parent / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["APP_NAME"] = settings.app_name
templates.env.filters["hhmm"] = minutes_to_hhmm

def render(tpl: str, **ctx):
    template = templates.get_template(tpl)
    return HTMLResponse(template.render(**ctx))

@app.on_event("startup")
def startup():
    bootstrap_admin()

# ------------------
# Auth
# ------------------
@app.get("/login")
def login_page(request: Request):
    return render("auth/login.html", request=request, csrf_token=get_or_set_csrf(request), title="Login")

@app.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    with session_scope() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            return render("auth/login.html", request=request, csrf_token=get_or_set_csrf(request),
                          title="Login", error="Invalid credentials")
        user_id = int(user.id)  # capture before session closes
    resp = RedirectResponse(url="/", status_code=303)
    return login_user(resp, request, user_id)

@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    resp = RedirectResponse(url="/login", status_code=303)
    return logout_user(resp, request)

# ------------------
# Pages
# ------------------
@app.get("/")
def home(request: Request):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/add-action", status_code=302)

@app.get("/add-action")
def add_action_page(request: Request, day_dmy: str | None = None):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)

    from datetime import date as _date
    from .utils.formatting import dmy as _dmy

    # Default to today (DD/MM/YYYY)
    if day_dmy:
        sel_date = parse_dmy(day_dmy.strip())
        if not sel_date:
            sel_date = _date.today()
    else:
        sel_date = _date.today()

    with session_scope() as db:
        # For the autocomplete
        all_ms = cp.list_all_milestones_with_project_name(db)
        # Today’s actions list
        rows = ca.list_actions_by_date(db, sel_date)

    return render(
        "tabs/add_action.html",
        request=request,
        csrf_token=get_or_set_csrf(request),
        title="Add Action",
        day_dmy=_dmy(sel_date),
        milestones=all_ms,
        actions=rows
    )



@app.post("/api/actions/add")
def api_actions_add(
    request: Request,
    csrf_token: str = Form(...),
    date_dmy: str = Form(...),
    project_id: str = Form(...),
    milestone_id: str = Form(""),
    hhmm: str = Form(...),
    comment: str = Form("")
):
    validate_csrf(request, csrf_token)

    # Validate IDs
    if not project_id.strip():
        return HTMLResponse("Project is required", status_code=400)
    pid = int(project_id)
    mid = int(milestone_id) if milestone_id.strip() else None

    # Validate date & time inside CRUD; but pre-check to give friendly errors
    if not parse_dmy(date_dmy.strip()):
        return HTMLResponse("Invalid date (use DD/MM/YYYY)", status_code=400)

    with session_scope() as db:
        try:
            ca.add_action(
                db,
                project_id=pid,
                milestone_id=mid,
                date_dmy=date_dmy.strip(),
                hhmm=hhmm.strip(),
                comment=(comment.strip() or None),
            )
        except ValueError as e:
            # Re-render the page with an error message
            from datetime import date as _date
            from .utils.formatting import dmy as _dmy
            all_ms = cp.list_all_milestones_with_project_name(db)
            rows = ca.list_actions_by_date(db, parse_dmy(date_dmy.strip()) or _date.today())
            return render(
                "tabs/add_action.html",
                request=request,
                csrf_token=get_or_set_csrf(request),
                title="Add Action",
                day_dmy=_dmy(parse_dmy(date_dmy.strip()) or _date.today()),
                milestones=all_ms,
                actions=rows,
                error=str(e)
            )

    # Redirect back to same day
    return RedirectResponse(url=f"/add-action?day_dmy={date_dmy.strip()}", status_code=303)

@app.get("/categories")
def categories_page(request: Request):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)
    ok = request.query_params.get("ok")
    with session_scope() as db:
        cats = cc.list_categories(db)
    return render(
        "tabs/categories.html",
        request=request,
        csrf_token=get_or_set_csrf(request),
        title="Categories",
        categories=cats,
        success=("Saved" if ok else None)
    )

@app.get("/projects")
def projects_page(request: Request, category_id: int | None = None, project_id: int | None = None, view: str = "list"):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)
    with session_scope() as db:
        cats = cc.list_categories(db)
        projs = cp.list_projects(db, category_id=category_id)
        sel_id = project_id or (projs[0].id if projs else None)
        ms = cp.list_milestones_for_project(db, sel_id) if sel_id else []
    return render(
        "tabs/projects.html",
        request=request,
        csrf_token=get_or_set_csrf(request),
        title="Projects",
        categories=cats,
        projects=projs,
        milestones=ms,
        category_id=category_id,
        selected_pid=sel_id,
        view=view
    )

@app.get("/reviews")
def reviews_page(request: Request, week_start_dmy: str | None = None):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)

    today = date.today()
    # Determine week start (Monday)
    if week_start_dmy and week_start_dmy.strip():
        ws = parse_dmy(week_start_dmy.strip())
        if not ws:
            ws, _ = week_bounds(today)
    else:
        ws, _ = week_bounds(today)
    ws, we = week_bounds(ws)  # normalize to Mon–Sun

    # Pull data
    with session_scope() as db:
        days = totals_by_day_range(db, ws, we)          # [(date, minutes)]
        per_project = totals_by_project_range(db, ws, we, limit=None)
        week_total = total_minutes_range(db, ws, we)

    # Prepare template-friendly rows
    series_max = max((m for _, m in days), default=0)
    day_rows = []
    for d, minutes in days:
        pct = int((minutes * 100) / series_max) if series_max > 0 else 0
        day_rows.append({
            "label": d.strftime("%a"),
            "minutes": minutes,
            "hhmm": minutes_to_hhmm(minutes),
            "pct": pct
        })

    proj_rows = []
    for p in per_project:
        share = (p.total_minutes * 100 / week_total) if week_total else 0
        proj_rows.append({
            "name": p.name,
            "minutes": p.total_minutes,
            "hhmm": minutes_to_hhmm(p.total_minutes),
            "share": f"{share:.1f}%"
        })

    # Prev/next links (Mon-based)
    from datetime import timedelta
    prev_ws = ws - timedelta(days=7)
    next_ws = ws + timedelta(days=7)

    return render(
        "tabs/reviews.html",
        request=request,
        csrf_token=get_or_set_csrf(request),
        title="Week Reviews",
        ws=ws, we=we,
        day_rows=day_rows,
        proj_rows=proj_rows,
        week_total_hhmm=minutes_to_hhmm(week_total),
        prev_ws_dmy=dmy(prev_ws),
        this_ws_dmy=dmy(week_bounds(today)[0]),
        next_ws_dmy=dmy(next_ws),
    )

@app.get("/reports")
def reports_page(request: Request):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)
    ok = request.query_params.get("ok")
    with session_scope() as db:
        files = cr.list_report_files(db)
    return render("tabs/reports.html",
                  request=request,
                  csrf_token=get_or_set_csrf(request),
                  title="Reports",
                  reports=files,
                  success=("Report generated" if ok else None))

@app.get("/settings")
def settings_page(request: Request):
    if not current_user_id(request):
        return RedirectResponse(url="/login", status_code=302)
    return render("tabs/settings.html", request=request, csrf_token=get_or_set_csrf(request), title="Settings")

# ------------------
# API (forms)
# ------------------

# Categories
@app.post("/api/categories/upsert")
def api_categories_upsert(
    request: Request,
    csrf_token: str = Form(...),
    id: str = Form(""),
    name: str = Form(...),
    description: str = Form("")
):
    validate_csrf(request, csrf_token)
    with session_scope() as db:
        cid = int(id) if id.strip() else None
        cc.upsert_category(db, id=cid, name=name.strip(), description=(description.strip() or None))
    return RedirectResponse(url="/categories?ok=1", status_code=303)

# Projects
@app.post("/api/projects/upsert")
def api_projects_upsert(
    request: Request,
    csrf_token: str = Form(...),
    id: str = Form(""),
    category_id: str = Form(""),
    name: str = Form(...),
    objective: str = Form(""),
    description: str = Form(""),
    color: str = Form(""),
    end_date_dmy: str = Form(...),
    status: str = Form("active"),
):
    validate_csrf(request, csrf_token)
    pid = int(id) if id.strip() else None
    cat_id = int(category_id) if category_id.strip() else None
    with session_scope() as db:
        p = cp.upsert_project(
            db, id=pid, category_id=cat_id, name=name.strip(),
            objective=(objective.strip() or None), description=(description.strip() or None),
            color=(color.strip() or None), end_date_dmy=end_date_dmy.strip(), status=status
        )
        new_id = int(p.id)
    return RedirectResponse(url=f"/projects?project_id={new_id}&view=list", status_code=303)

# Milestones
@app.post("/api/milestones/upsert")
def api_milestones_upsert(
    request: Request,
    csrf_token: str = Form(...),
    id: str = Form(""),
    project_id: int = Form(...),
    name: str = Form(...),
    end_date_dmy: str = Form(...),
    percent_complete: int = Form(0),
    status: str = Form("active"),
    note: str = Form(""),
    dependent_to_id: str = Form("")
):
    validate_csrf(request, csrf_token)
    mid = int(id) if id.strip() else None
    dep = int(dependent_to_id) if dependent_to_id.strip() else None
    with session_scope() as db:
        m = cm.upsert_milestone(
            db, id=mid, project_id=project_id, name=name.strip(),
            end_date_dmy=end_date_dmy.strip(), percent_complete=percent_complete,
            status=status, note=(note.strip() or None), dependent_to_id=dep
        )
        sel_project = int(m.project_id)
    return RedirectResponse(url=f"/projects?project_id={sel_project}&view=list#m-{m.id}", status_code=303)

@app.post("/api/milestones/{mid}/percent")
def api_milestones_percent(request: Request, mid: int, csrf_token: str = Form(...), value_num: int = Form(...)):
    validate_csrf(request, csrf_token)
    with session_scope() as db:
        m = cm.set_percent(db, mid, value_num)
        pid = int(m.project_id)
    return RedirectResponse(url=f"/projects?project_id={pid}&view=list#m-{mid}", status_code=303)

@app.post("/api/milestones/{mid}/note")
def api_milestones_note(request: Request, mid: int, csrf_token: str = Form(...), note: str = Form("")):
    validate_csrf(request, csrf_token)
    with session_scope() as db:
        m = cm.set_note(db, mid, (note.strip() or None))
        pid = int(m.project_id)
    return RedirectResponse(url=f"/projects?project_id={pid}&view=list#m-{mid}", status_code=303)

# Node graph data (vis-network)
@app.get("/api/projects/{pid}/graph")
def project_graph(pid: int):
    from datetime import date as _date
    with session_scope() as db:
        data = cd.graph_for_project(db, pid, _date.today())
        # also expose milestone status for client-side hiding
        # (graph_for_project already sizes & colors)
        # ensure nodes have 'status' key:
        # (backfill if missing)
        for n in data.get("nodes", []):
            n.setdefault("status", "active")
        return data

# Reports (basic generate/download hooks)
@app.post("/api/reports/generate")
def api_reports_generate(
    request: Request,
    csrf_token: str = Form(...),
    type: str = Form(...),
    start_dmy: str = Form(""),
):
    validate_csrf(request, csrf_token)
    today = date.today()

    # Resolve start date (DD/MM/YYYY or default period start)
    if start_dmy.strip():
        start = parse_dmy(start_dmy.strip())
        if not start:
            return render("tabs/reports.html", request=request, csrf_token=get_or_set_csrf(request),
                          title="Reports", error="Invalid start date (DD/MM/YYYY)", reports=[])
    else:
        if type == "weekly":
            start, _ = week_bounds(today)
        elif type == "monthly":
            start = today.replace(day=1)
        elif type == "yearly":
            start = today.replace(month=1, day=1)
        else:
            return render("tabs/reports.html", request=request, csrf_token=get_or_set_csrf(request),
                          title="Reports", error="Unknown report type", reports=[])

    # Get end bound for DB record
    if type == "weekly":
        ws, we = week_bounds(start)
    elif type == "monthly":
        ws, we = month_bounds(start)
    else:
        ws, we = year_bounds(start)

    # Render PDF
    out_path = render_report_pdf(templates_dir, reports_dir, type, start, settings.app_name)

    # Store DB row
    with session_scope() as db:
        cr.create_report_file(db, type, ws, we, str(out_path))

    return RedirectResponse(url="/reports?ok=1", status_code=303)

@app.get("/api/reports/download")
def api_reports_download(id: int):
    from sqlalchemy import select as _select
    from .models import ReportFile
    with session_scope() as db:
        r = db.execute(_select(ReportFile).where(ReportFile.id == id)).scalars().first()
        if not r:
            return HTMLResponse("Not found", status_code=404)
        return FileResponse(path=r.file_path, media_type="application/pdf",
                            filename=Path(r.file_path).name)

