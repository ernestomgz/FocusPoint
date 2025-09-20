from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Category

def list_categories(db: Session) -> list[Category]:
    return list(db.execute(select(Category).order_by(Category.name)).scalars())

def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)

def upsert_category(db: Session, *, id: int | None, name: str, description: str | None) -> Category:
    if id:
        obj = db.get(Category, id)
        if not obj:
            raise ValueError("Category not found")
        obj.name = name
        obj.description = description
    else:
        obj = Category(name=name, description=description)
        db.add(obj)
    db.flush()
    return obj

def delete_category(db: Session, category_id: int) -> None:
    obj = db.get(Category, category_id)
    if obj:
        db.delete(obj)

