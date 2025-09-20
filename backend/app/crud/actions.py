from __future__ import annotations
from typing import Optional, List
from types import SimpleNamespace
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..models import Action, Project, Milestone, Category
from ..utils.formatting import parse_dmy, hhmm_to_minutes


# ------------------------
# Create & list
# ------------------------

def add_action(
    db: Session,
    project_id: int,
    milestone_id: Optional[int],
    date_dmy: str,
    hhmm: str,
    comment: Optional[str] = None,
) -> Action:
    d = parse_dmy(date_dmy)
    if not d:
        raise ValueError("Invalid date (use DD/MM/YYYY)")

    minutes = hhmm_to_minutes(hhmm)  # raises ValueError if invalid

    proj = db.get(Project, project_id)
    if not proj:
        raise ValueError("Project not found")

    if milestone_id:
        ms = db.get(Milestone, milestone_id)
        if not ms:
            raise ValueError("Milestone not found")
        if ms.project_id != project_id:
            raise ValueError("Milestone does not belong to the selected project")

    a = Action(
        project_id=project_id,
        milestone_id=milestone_id,
        date=d,
        minutes=minutes,
        comment=comment if comment else None,
    )
    db.add(a)
    db.flush()
    return a


def list_actions_by_date(db: Session, day: date) -> List[SimpleNamespace]:
    """
    Return actions for a given date with project/milestone names,
    in a template-friendly structure.
    """
    stmt = (
        select(
            Action.id,
            Action.date,
            Action.minutes,
            Action.comment,
            Project.name.label("project_name"),
            Milestone.name.label("milestone_name"),
        )
        .join(Project, Project.id == Action.project_id)
        .join(Milestone, Milestone.id == Action.milestone_id, isouter=True)
        .where(Action.date == day)
        .order_by(Action.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        SimpleNamespace(
            id=r.id,
            date=r.date,
            minutes=int(r.minutes or 0),
            comment=r.comment,
            project_name=r.project_name,
            milestone_name=r.milestone_name,
        )
        for r in rows
    ]


# ------------------------
# Aggregations for reports
# ------------------------

def total_minutes_range(db: Session, start: date, end: date) -> int:
    """Total minutes across a closed date interval [start, end]."""
    stmt = select(func.coalesce(func.sum(Action.minutes), 0)).where(
        Action.date >= start, Action.date <= end
    )
    return int(db.execute(stmt).scalar_one() or 0)


def totals_by_day_range(db: Session, start: date, end: date) -> List[tuple[date, int]]:
    """
    Minutes per day for a closed date interval [start, end], with zero-filled days.
    Returns list of (date, minutes) in chronological order.
    """
    stmt = (
        select(Action.date, func.coalesce(func.sum(Action.minutes), 0))
        .where(Action.date >= start, Action.date <= end)
        .group_by(Action.date)
    )
    rows = dict(db.execute(stmt).all())  # {date: minutes}
    out: List[tuple[date, int]] = []
    cur = start
    one = timedelta(days=1)
    while cur <= end:
        out.append((cur, int(rows.get(cur, 0) or 0)))
        cur += one
    return out


def totals_by_project_range(
    db: Session, start: date, end: date, limit: Optional[int] = None
) -> List[SimpleNamespace]:
    """
    Minutes per project for [start, end], descending.
    Returns list of SimpleNamespace(name, project_id, total_minutes).
    """
    stmt = (
        select(Project.id, Project.name, func.coalesce(func.sum(Action.minutes), 0).label("m"))
        .join(Project, Project.id == Action.project_id)
        .where(Action.date >= start, Action.date <= end)
        .group_by(Project.id, Project.name)
        .order_by(func.coalesce(func.sum(Action.minutes), 0).desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    rows = db.execute(stmt).all()
    return [
        SimpleNamespace(project_id=r.id, name=r.name, total_minutes=int(r.m or 0))
        for r in rows
    ]


def totals_by_category_range(
    db: Session, start: date, end: date
) -> List[SimpleNamespace]:
    """
    Minutes per category for [start, end].
    Returns list of SimpleNamespace(category_id, category, minutes), descending.
    Projects without category are grouped under 'Uncategorized'.
    """
    stmt = (
        select(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Action.minutes), 0).label("m"),
        )
        .select_from(Action)
        .join(Project, Project.id == Action.project_id)
        .join(Category, Category.id == Project.category_id, isouter=True)
        .where(Action.date >= start, Action.date <= end)
        .group_by(Category.id, Category.name)
        .order_by(func.coalesce(func.sum(Action.minutes), 0).desc())
    )
    rows = db.execute(stmt).all()
    out: List[SimpleNamespace] = []
    for cid, name, m in rows:
        out.append(
            SimpleNamespace(
                category_id=cid,
                category=name or "Uncategorized",
                minutes=int(m or 0),
            )
        )
    return out

