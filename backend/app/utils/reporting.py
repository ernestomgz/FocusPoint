from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta, datetime
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..utils.formatting import minutes_to_hhmm
from ..utils.pdf import render_html_to_pdf
from ..utils.dates import week_bounds, month_bounds, year_bounds
from ..crud.actions import (
    totals_by_day_range,
    totals_by_project_range,
    totals_by_category_range,
    total_minutes_range,
)
from ..crud.reports import (
    project_progress_overview,
    overdue_milestones,
    upcoming_milestones,
    times_by_project_range_map,
    project_milestone_health,
)


def _env(templates_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["hhmm"] = minutes_to_hhmm
    env.globals["zip"] = zip
    return env


def _static_pdf_css_path(templates_dir: Path) -> Path:
    return templates_dir.parent / "static" / "css" / "pdf.css"


# ---------- small helpers ----------

def _active_days_and_streak(day_totals: list[tuple[date, int]]):
    active = [d for d, m in day_totals if (m or 0) > 0]
    active_days = len(active)
    longest = cur = 0
    prev = None
    for d, m in day_totals:
        if (m or 0) > 0:
            if prev and (d - prev).days == 1:
                cur += 1
            else:
                cur = 1
            longest = max(longest, cur)
            prev = d
        else:
            prev = None
            cur = 0
    return active_days, longest


def _top_shares(items: list[int]) -> tuple[float, float]:
    total = float(sum(items))
    if total <= 0:
        return 0.0, 0.0
    top1 = 100.0 * (items[0] / total) if items else 0.0
    top3 = 100.0 * (sum(items[:3]) / total) if len(items) >= 3 else top1
    return top1, top3


def _enrich_projects_with_health(projects: list[SimpleNamespace], health_map: dict[int, SimpleNamespace]) -> list[SimpleNamespace]:
    out = []
    for p in projects:
        h = health_map.get(p.project_id, SimpleNamespace(overdue=0, risk=0))
        out.append(SimpleNamespace(
            project_id=p.project_id,
            name=p.name,
            total_minutes=p.total_minutes,
            overdue=h.overdue,
            risk=h.risk,
        ))
    return out


# ---------- weekly ----------

def _weekly_context(db, start: date, app_name: str, templates_dir: Path) -> dict:
    ws, we = week_bounds(start)
    day_totals = totals_by_day_range(db, ws, we)
    series_labels = [d.strftime("%a") for d, _ in day_totals]
    series_values = [m for _, m in day_totals]
    series_max = max(series_values) if series_values else 0
    # busiest day
    if series_values:
        max_idx = max(range(len(series_values)), key=lambda i: series_values[i])
        busiest_label = series_labels[max_idx]
        busiest_value = series_values[max_idx]
    else:
        busiest_label, busiest_value = "-", 0

    cats = totals_by_category_range(db, ws, we)
    projs_raw = totals_by_project_range(db, ws, we, limit=12)
    proj_minutes_list = [p.total_minutes for p in projs_raw]
    top1, top3 = _top_shares(proj_minutes_list)

    week_total = sum(series_values)
    active_days, longest_streak = _active_days_and_streak(day_totals)
    avg_active = int(week_total / active_days) if active_days else 0

    prog = project_progress_overview(db)
    proj_times_map = times_by_project_range_map(db, ws, we)
    health_map = project_milestone_health(db, we, lookahead_days=7)
    projs = _enrich_projects_with_health(projs_raw, health_map)

    # Suggestions (GTD-friendly)
    ups = upcoming_milestones(db, we + timedelta(days=1), we + timedelta(days=7), limit=10)
    ods = overdue_milestones(db, we + timedelta(days=1), limit=10)
    suggestions = []
    for u in ups[:5]:
        p = prog.get(u.project_id)
        if p and p.avg_percent < 60:
            suggestions.append(f"Focus '{u.project}' → '{u.milestone}' due {u.end.strftime('%d/%m/%Y')} (progress {int(p.avg_percent)}%).")
    for o in ods[:5]:
        suggestions.append(f"Overdue '{o.project}' → '{o.milestone}' by {o.days_late} day(s).")
    proj_with_time = {pid for pid, m in proj_times_map.items() if m > 0}
    for u in ups:
        if u.project_id not in proj_with_time:
            suggestions.append(f"Start '{u.project}': next milestone {u.end.strftime('%d/%m/%Y')} and no time logged this week.")
            break

    return {
        "app_name": app_name,
        "generated": date.today(),
        "series_title": "Week at a glance",
        "start": ws,
        "end": we,
        "busiest_label": busiest_label,
        "busiest_value": minutes_to_hhmm(busiest_value),
        "series_labels": series_labels,
        "series_values": series_values,
        "series_max": series_max,
        "categories_data": cats,
        "projects": projs,
        "week_total": week_total,
        "week_total_hhmm": minutes_to_hhmm(week_total),
        "active_days": active_days,
        "avg_active_hhmm": minutes_to_hhmm(avg_active),
        "longest_streak": longest_streak,
        "top1_share": f"{top1:.1f}%",
        "top3_share": f"{top3:.1f}%",
        "upcoming": ups,
        "overdue": ods,
        "suggestions": suggestions[:8],
        "css_paths": [_static_pdf_css_path(templates_dir)],
        "template_name": "reports/report_week.html",
        "suggested_filename": f"weekly_{ws.strftime('%Y-%m-%d')}_to_{we.strftime('%Y-%m-%d')}.pdf",
    }


# ---------- monthly ----------

def _monthly_context(db, start: date, app_name: str, templates_dir: Path) -> dict:
    ms, me = month_bounds(start)

    # Week-chunks inside the month (1–7, 8–14, 15–21, 22–28, 29–end)
    labels, bounds = [], []
    cur = ms
    idx = 1
    while cur <= me:
        ce = min(cur + timedelta(days=6), me)
        labels.append(f"W{idx}")
        bounds.append((cur, ce))
        cur = ce + timedelta(days=1)
        idx += 1

    values = [total_minutes_range(db, s, e) for s, e in bounds]
    series_labels = labels
    series_values = values
    series_max = max(series_values) if series_values else 0
    # busiest week-chunk
    if series_values:
        max_idx = max(range(len(series_values)), key=lambda i: series_values[i])
        busiest_label = series_labels[max_idx]
        busiest_value = series_values[max_idx]
    else:
        busiest_label, busiest_value = "-", 0

    cats = totals_by_category_range(db, ms, me)
    projs_raw = totals_by_project_range(db, ms, me, limit=15)
    proj_minutes_list = [p.total_minutes for p in projs_raw]
    top1, top3 = _top_shares(proj_minutes_list)

    day_totals = totals_by_day_range(db, ms, me)
    month_total = sum(m for _, m in day_totals)
    active_days, longest_streak = _active_days_and_streak(day_totals)
    avg_active = int(month_total / active_days) if active_days else 0

    prog = project_progress_overview(db)
    health_map = project_milestone_health(db, me, lookahead_days=14)
    projs = _enrich_projects_with_health(projs_raw, health_map)

    ups = upcoming_milestones(db, me + timedelta(days=1), me + timedelta(days=14), limit=20)
    ods = overdue_milestones(db, me + timedelta(days=1), limit=20)

    suggestions = []
    if top1 >= 60:
        suggestions.append("Strong focus detected. Consider checking balance across categories.")
    for u in ups[:6]:
        p = prog.get(u.project_id)
        if p and p.avg_percent < 60:
            suggestions.append(f"Prepare '{u.project}' → '{u.milestone}' (due {u.end.strftime('%d/%m/%Y')}, progress {int(p.avg_percent)}%).")
    for o in ods[:6]:
        suggestions.append(f"Resolve overdue '{o.project}' → '{o.milestone}' ({o.days_late} day(s) late).")

    return {
        "app_name": app_name,
        "generated": date.today(),
        "series_title": "Weekly totals (inside month)",
        "start": ms,
        "end": me,
        "busiest_label": busiest_label,
        "busiest_value": minutes_to_hhmm(busiest_value),
        "series_labels": series_labels,
        "series_values": series_values,
        "series_max": series_max,
        "categories_data": cats,
        "projects": projs,
        "month_total": month_total,
        "month_total_hhmm": minutes_to_hhmm(month_total),
        "active_days": active_days,
        "avg_active_hhmm": minutes_to_hhmm(avg_active),
        "longest_streak": longest_streak,
        "top1_share": f"{top1:.1f}%",
        "top3_share": f"{top3:.1f}%",
        "upcoming": ups,
        "overdue": ods,
        "suggestions": suggestions[:10],
        "css_paths": [_static_pdf_css_path(templates_dir)],
        "template_name": "reports/report_month.html",
        "suggested_filename": f"monthly_{ms.strftime('%Y-%m')}.pdf",
    }


# ---------- yearly ----------

def _yearly_context(db, start: date, app_name: str, templates_dir: Path) -> dict:
    ys, ye = year_bounds(start)

    series_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    series_values = []
    for month in range(1, 13):
        ms = date(ys.year, month, 1)
        me = (date(ys.year, month + 1, 1) - timedelta(days=1)) if month < 12 else ye
        series_values.append(total_minutes_range(db, ms, me))
    series_max = max(series_values) if series_values else 0
    # busiest month
    if series_values:
        max_idx = max(range(len(series_values)), key=lambda i: series_values[i])
        busiest_label = series_labels[max_idx]
        busiest_value = series_values[max_idx]
    else:
        busiest_label, busiest_value = "-", 0

    cats = totals_by_category_range(db, ys, ye)
    projs_raw = totals_by_project_range(db, ys, ye, limit=20)
    proj_minutes_list = [p.total_minutes for p in projs_raw]
    top1, top3 = _top_shares(proj_minutes_list)

    day_totals = totals_by_day_range(db, ys, ye)
    year_total = sum(m for _, m in day_totals)
    active_days, longest_streak = _active_days_and_streak(day_totals)
    avg_active = int(year_total / active_days) if active_days else 0

    health_map = project_milestone_health(db, ye, lookahead_days=30)
    projs = _enrich_projects_with_health(projs_raw, health_map)

    ups = upcoming_milestones(db, ye + timedelta(days=1), ye + timedelta(days=30), limit=30)
    ods = overdue_milestones(db, ye + timedelta(days=1), limit=30)

    suggestions = []
    if top3 < 50:
        suggestions.append("Attention spread across many projects. Consider limiting WIP for deeper focus.")
    # Nudge low-progress top projects
    prog = project_progress_overview(db)
    hot = [p for p in projs_raw[:5] if prog.get(p.project_id) and prog[p.project_id].avg_percent < 50]
    for h in hot:
        suggestions.append(f"Raise progress on '{h.name}' (only {int(prog[h.project_id].avg_percent)}%).")
    for o in ods[:8]:
        suggestions.append(f"Overdue '{o.project}' → '{o.milestone}' ({o.days_late} day(s) late).")

    return {
        "app_name": app_name,
        "generated": date.today(),
        "series_title": "Monthly totals",
        "start": ys,
        "end": ye,
        "busiest_label": busiest_label,
        "busiest_value": minutes_to_hhmm(busiest_value),
        "series_labels": series_labels,
        "series_values": series_values,
        "series_max": series_max,
        "categories_data": cats,
        "projects": projs,
        "year_total": year_total,
        "year_total_hhmm": minutes_to_hhmm(year_total),
        "active_days": active_days,
        "avg_active_hhmm": minutes_to_hhmm(avg_active),
        "longest_streak": longest_streak,
        "top1_share": f"{top1:.1f}%",
        "top3_share": f"{top3:.1f}%",
        "upcoming": ups,
        "overdue": ods,
        "suggestions": suggestions[:12],
        "css_paths": [_static_pdf_css_path(templates_dir)],
        "template_name": "reports/report_year.html",
        "suggested_filename": f"yearly_{ys.year}.pdf",
    }


def render_report_pdf(templates_dir: Path, reports_dir: Path, period_type: str, start: date, app_name: str) -> Path:
    from ..db import session_scope

    env = _env(templates_dir)
    with session_scope() as db:
        if period_type == "weekly":
            ctx = _weekly_context(db, start, app_name, templates_dir)
        elif period_type == "monthly":
            ctx = _monthly_context(db, start, app_name, templates_dir)
        elif period_type == "yearly":
            ctx = _yearly_context(db, start, app_name, templates_dir)
        else:
            raise ValueError("Unknown report type")

    tpl = env.get_template(ctx["template_name"])
    html = tpl.render(**ctx)
    out_path = reports_dir / ctx["suggested_filename"]
    render_html_to_pdf(html, out_path, css_paths=ctx["css_paths"])
    return out_path

