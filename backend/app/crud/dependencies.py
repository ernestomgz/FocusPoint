from datetime import date
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from ..models import Dependency, Milestone
from ..crud.milestones import list_project_milestones_health

def add_dependency(db: Session, project_id: int, from_id: int, to_id: int) -> Dependency:
    if from_id == to_id:
        raise ValueError("A milestone cannot depend on itself")
    exists = db.execute(
        select(Dependency).filter(
            Dependency.project_id == project_id,
            Dependency.from_milestone_id == from_id,
            Dependency.to_milestone_id == to_id
        )
    ).scalars().first()
    if exists:
        return exists
    dep = Dependency(project_id=project_id, from_milestone_id=from_id, to_milestone_id=to_id)
    db.add(dep)
    db.flush()
    return dep

def list_dependencies(db: Session, project_id: int) -> list[Dependency]:
    return list(
        db.execute(
            select(Dependency).filter(Dependency.project_id == project_id)
        ).scalars()
    )

def remove_dependency(db: Session, dep_id: int):
    d = db.get(Dependency, dep_id)
    if d: db.delete(d)

# --- vis-network graph data ---

def graph_for_project(db: Session, project_id: int, today: date) -> dict:
    """
    Returns dict with 'nodes' and 'edges' for vis-network.
    Nodes contain id, label, title (tooltip), color, border, and size by %.
    Edges contain from, to, arrows='to', color.
    """
    ms = list_project_milestones_health(db, project_id, today)
    deps = list_dependencies(db, project_id)

    nodes = []
    for m in ms:
        # color border by health; white background; size by percent
        border = {"ok": "#2ec27e", "risk": "#ffcc66", "late": "#ff6b6b"}.get(m["health"], "#ddd")
        size = 20 + (m["percent_complete"] / 100.0) * 20  # 20..40
        label = f'{m["name"]}\n{m["percent_complete"]}% · {m["end_date"].strftime("%d/%m/%Y")}'
        nodes.append({
            "id": str(m["id"]),
            "label": label,
            "title": f'{m["name"]} — ends {m["end_date"].strftime("%d/%m/%Y")}',
            "shape": "box",
            "margin": 8,
            "color": {
                "background": "#ffffff",
                "border": border,
                "highlight": {"background": "#ffffff", "border": "#7c4dff"},
                "hover": {"background": "#ffffff", "border": "#7c4dff"},
            },
            "font": {"color": "#111", "size": 12, "multi": "html"},
            "borderWidth": 3,
            "widthConstraint": {"maximum": 260},
            "heightConstraint": {"minimum": 36, "maximum": 80},
            "size": size,
        })

    edges = [{
        "id": str(d.id),
        "from": str(d.from_milestone_id),
        "to": str(d.to_milestone_id),
        "arrows": "to",
        "color": {"color": "#2f1bb3", "highlight": "#7c4dff", "hover": "#7c4dff"},
        "width": 3
    } for d in deps]

    return {"nodes": nodes, "edges": edges}

