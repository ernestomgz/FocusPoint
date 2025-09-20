from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from ..models import Project, Category, Milestone
from ..utils.formatting import parse_dmy

def list_projects(db: Session, category_id: int | None = None) -> list[Project]:
    stmt = select(Project).options(selectinload(Project.category)).order_by(Project.name)
    if category_id:
        stmt = stmt.filter(Project.category_id == category_id)
    return list(db.execute(stmt).scalars())

def get_project(db: Session, project_id: int) -> Project | None:
    return db.execute(
        select(Project)
        .options(selectinload(Project.category), selectinload(Project.milestones))
        .filter(Project.id == project_id)
    ).scalars().first()

def upsert_project(
    db: Session, *, id: int | None, category_id: int | None, name: str,
    objective: str | None, description: str | None, color: str | None,
    end_date_dmy: str, status: str
) -> Project:
    end_d = parse_dmy(end_date_dmy)
    if not end_d:
        raise ValueError("Invalid end date (use DD/MM/YYYY)")
    if id:
        p = db.get(Project, id)
        if not p:
            raise ValueError("Project not found")
        p.category_id = category_id
        p.name = name
        p.objective = objective
        p.description = description
        p.color = color
        p.end_date = end_d
        p.status = status
    else:
        p = Project(
            category_id=category_id, name=name, objective=objective,
            description=description, color=color, end_date=end_d, status=status
        )
        db.add(p)
    db.flush()
    return p

def list_milestones_for_project(db: Session, project_id: int) -> list[Milestone]:
    return list(
        db.execute(
            select(Milestone).options(selectinload(Milestone.project))
            .filter(Milestone.project_id == project_id)
            .order_by(Milestone.end_date, Milestone.name)
        ).scalars()
    )

def list_all_milestones_with_project_name(db: Session) -> list[dict]:
    """Preload project name to avoid detached access in templates."""
    rows = db.execute(
        select(Milestone, Project.name.label("project_name"))
        .join(Project, Project.id == Milestone.project_id)
        .order_by(Project.name, Milestone.name)
    ).all()
    out = []
    for m, pname in rows:
        out.append({
            "id": m.id, "name": m.name, "project_id": m.project_id,
            "project_name": pname, "end_date": m.end_date,
            "percent_complete": m.percent_complete, "status": m.status,
            "note": m.note
        })
    return out

