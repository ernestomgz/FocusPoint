from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from types import SimpleNamespace

from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import Session

from ..models import ReportFile, Project, Milestone, Category, Action


# -------------------------------
# Persisted files
# -------------------------------

def create_report_file(
    db: Session,
    period_type: str,
    start: date,
    end: date,
    file_path: str,
) -> ReportFile:
    row = ReportFile(
        period_type=period_type,
        period_start=start,
        period_end=end,
        file_path=str(file_path),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def list_report_files(db: Session) -> List[ReportFile]:
    stmt = select(ReportFile).order_by(ReportFile.id.desc())
    return db.execute(stmt).scalars().all()


# -------------------------------
# Report data helpers
# -------------------------------

def project_progress_overview(db: Session) -> Dict[int, SimpleNamespace]:
    """
    For each project, return avg % complete, total milestones, done milestones.
    { project_id: SimpleNamespace(avg_percent, total_ms, done_ms) }
    """
    stmt = (
        select(
            Milestone.project_id,
            func.coalesce(func.avg(Milestone.percent_complete), 0).label("avgp"),
            func.count(Milestone.id).label("total"),
            func.sum(
                case((Milestone.status == "done", 1), else_=0)
            ).label("done"),
        )
        .group_by(Milestone.project_id)
    )
    rows = db.execute(stmt).all()
    out: Dict[int, SimpleNamespace] = {}
    for pid, avgp, total, done in rows:
        out[int(pid or 0)] = SimpleNamespace(
            avg_percent=float(avgp or 0),
            total_ms=int(total or 0),
            done_ms=int(done or 0),
        )
    return out


def overdue_milestones(db: Session, ref_date: date, limit: Optional[int] = 20) -> List[SimpleNamespace]:
    """
    Milestones with end_date < ref_date and status != 'done'
    """
    stmt = (
        select(
            Category.name.label("category"),
            Project.id.label("project_id"),
            Project.name.label("project"),
            Milestone.id.label("milestone_id"),
            Milestone.name.label("milestone"),
            Milestone.end_date,
        )
        .select_from(Milestone)
        .join(Project, Project.id == Milestone.project_id)
        .join(Category, Category.id == Project.category_id, isouter=True)
        .where(and_(Milestone.status != "done", Milestone.end_date < ref_date))
        .order_by(Milestone.end_date.asc())
    )
    rows = db.execute(stmt).all()
    out: List[SimpleNamespace] = []
    for category, project_id, project, milestone_id, milestone, end_date in rows:
        days_late = (ref_date - end_date).days
        out.append(SimpleNamespace(
            category=category or "Uncategorized",
            project_id=int(project_id),
            project=project,
            milestone_id=int(milestone_id),
            milestone=milestone,
            end=end_date,
            days_late=int(days_late),
        ))
        if limit and len(out) >= limit:
            break
    return out


def upcoming_milestones(db: Session, start: date, end: date, limit: Optional[int] = 20) -> List[SimpleNamespace]:
    """
    Milestones with start <= end_date <= end and status != 'done'
    """
    stmt = (
        select(
            Category.name.label("category"),
            Project.id.label("project_id"),
            Project.name.label("project"),
            Milestone.id.label("milestone_id"),
            Milestone.name.label("milestone"),
            Milestone.end_date,
            Milestone.percent_complete,
        )
        .select_from(Milestone)
        .join(Project, Project.id == Milestone.project_id)
        .join(Category, Category.id == Project.category_id, isouter=True)
        .where(and_(Milestone.status != "done", Milestone.end_date >= start, Milestone.end_date <= end))
        .order_by(Milestone.end_date.asc())
    )
    rows = db.execute(stmt).all()
    out: List[SimpleNamespace] = []
    for category, project_id, project, milestone_id, milestone, end_date, pct in rows:
        out.append(SimpleNamespace(
            category=category or "Uncategorized",
            project_id=int(project_id),
            project=project,
            milestone_id=int(milestone_id),
            milestone=milestone,
            end=end_date,
            percent=int(pct or 0),
        ))
        if limit and len(out) >= limit:
            break
    return out


def times_by_project_range_map(db: Session, start: date, end: date) -> Dict[int, int]:
    """
    {project_id: minutes} for actions within [start, end]
    """
    stmt = (
        select(Action.project_id, func.coalesce(func.sum(Action.minutes), 0))
        .where(and_(Action.date >= start, Action.date <= end))
        .group_by(Action.project_id)
    )
    rows = db.execute(stmt).all()
    return {int(pid): int(m or 0) for pid, m in rows}


def project_milestone_health(db: Session, ref_date: date, lookahead_days: int = 14) -> Dict[int, SimpleNamespace]:
    """
    For each project: counts of overdue and at-risk milestones.
    - overdue: end_date < ref_date AND status != 'done'
    - risk:    ref_date <= end_date <= ref_date+lookahead AND status != 'done' AND percent_complete < 60
    Returns {project_id: SimpleNamespace(overdue=..., risk=...)}
    """
    horizon = ref_date + timedelta(days=lookahead_days)
    overdue_col = func.sum(
        case((and_(Milestone.status != "done", Milestone.end_date < ref_date), 1), else_=0)
    ).label("overdue")
    risk_col = func.sum(
        case((and_(Milestone.status != "done", Milestone.end_date >= ref_date,
                   Milestone.end_date <= horizon, Milestone.percent_complete < 60), 1), else_=0)
    ).label("risk")

    stmt = (
        select(Project.id, overdue_col, risk_col)
        .join(Project, Project.id == Milestone.project_id)
        .group_by(Project.id)
    )
    rows = db.execute(stmt).all()
    out: Dict[int, SimpleNamespace] = {}
    for pid, overdue_cnt, risk_cnt in rows:
        out[int(pid)] = SimpleNamespace(overdue=int(overdue_cnt or 0), risk=int(risk_cnt or 0))
    return out

