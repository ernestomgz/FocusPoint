from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from ..models import Milestone, Dependency
from ..utils.formatting import parse_dmy

def _health(m: Milestone, today: date) -> str:
    if (today > m.end_date and m.percent_complete < 100):
        return "late"
    if ((m.end_date - today).days <= 7 and m.percent_complete < 80):
        return "risk"
    return "ok"

def upsert_milestone(
    db: Session, *, id: int | None, project_id: int, name: str, end_date_dmy: str,
    percent_complete: int, status: str, note: str | None, dependent_to_id: int | None
) -> Milestone:
    end_d = parse_dmy(end_date_dmy)
    if not end_d:
        raise ValueError("Invalid end date (use DD/MM/YYYY)")
    percent_complete = max(0, min(100, int(percent_complete)))

    if id:
        m = db.get(Milestone, id)
        if not m:
            raise ValueError("Milestone not found")
        m.project_id = project_id
        m.name = name
        m.end_date = end_d
        m.percent_complete = percent_complete
        m.status = status
        m.note = note
    else:
        m = Milestone(
            project_id=project_id, name=name, end_date=end_d,
            percent_complete=percent_complete, status=status, note=note
        )
        db.add(m)
        db.flush()  # to have m.id

    # optional dependency: dependent_to_id -> m (i.e., m depends on dependent_to_id)
    if dependent_to_id:
        if dependent_to_id == m.id:
            raise ValueError("A milestone cannot depend on itself")
        exists = db.execute(
            select(Dependency).filter(
                Dependency.project_id == project_id,
                Dependency.from_milestone_id == dependent_to_id,
                Dependency.to_milestone_id == m.id
            )
        ).scalars().first()
        if not exists:
            db.add(Dependency(
                project_id=project_id,
                from_milestone_id=dependent_to_id,
                to_milestone_id=m.id
            ))

    db.flush()
    return m

def set_percent(db: Session, milestone_id: int, value: int) -> Milestone:
    m = db.get(Milestone, milestone_id)
    if not m: raise ValueError("Milestone not found")
    m.percent_complete = max(0, min(100, int(value)))
    db.flush()
    return m

def set_note(db: Session, milestone_id: int, note: str | None) -> Milestone:
    m = db.get(Milestone, milestone_id)
    if not m: raise ValueError("Milestone not found")
    m.note = note
    db.flush()
    return m

def list_project_milestones_health(db: Session, project_id: int, today: date) -> list[dict]:
    ms = list(
        db.execute(
            select(Milestone).filter(Milestone.project_id == project_id)
            .order_by(Milestone.end_date, Milestone.name)
        ).scalars()
    )
    return [{
        "id": m.id, "name": m.name, "end_date": m.end_date,
        "percent_complete": m.percent_complete, "status": m.status,
        "note": m.note, "health": _health(m, today)
    } for m in ms]

