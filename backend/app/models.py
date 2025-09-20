from datetime import date, datetime
from enum import Enum
from sqlalchemy import String, Text, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

# --- Enums ---

class StatusEnum(str, Enum):
    active = "active"
    on_hold = "on_hold"
    archived = "archived"
    done = "done"

# --- User ---

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- Categories / Projects ---

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="category", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), index=True)
    objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[StatusEnum] = mapped_column(String(20), default=StatusEnum.active)

    category: Mapped["Category"] = relationship(back_populates="projects")
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    actions: Mapped[list["Action"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_category_project_name"),)

# --- Milestones & Dependencies ---

class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    end_date: Mapped[date] = mapped_column(Date)
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    status: Mapped[StatusEnum] = mapped_column(String(20), default=StatusEnum.active)

    project: Mapped["Project"] = relationship(back_populates="milestones")
    outgoing: Mapped[list["Dependency"]] = relationship(
        back_populates="from_ms",
        foreign_keys="Dependency.from_milestone_id",
        cascade="all, delete-orphan"
    )
    incoming: Mapped[list["Dependency"]] = relationship(
        back_populates="to_ms",
        foreign_keys="Dependency.to_milestone_id",
        cascade="all, delete-orphan"
    )

class Dependency(Base):
    __tablename__ = "dependencies"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    from_milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id", ondelete="CASCADE"))
    to_milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id", ondelete="CASCADE"))

    from_ms: Mapped["Milestone"] = relationship(foreign_keys=[from_milestone_id], back_populates="outgoing")
    to_ms: Mapped["Milestone"] = relationship(foreign_keys=[to_milestone_id], back_populates="incoming")

    __table_args__ = (UniqueConstraint("project_id", "from_milestone_id", "to_milestone_id",
                                       name="uq_dep_unique"),)

# --- Actions (time logs) ---

class Action(Base):
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    milestone_id: Mapped[int | None] = mapped_column(ForeignKey("milestones.id", ondelete="SET NULL"))
    date: Mapped[date] = mapped_column(Date)
    minutes: Mapped[int] = mapped_column(Integer)   # store minutes internally
    comment: Mapped[str | None] = mapped_column(Text(), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="actions")
    milestone: Mapped["Milestone"] = relationship()

# --- Reports registry ---

class ReportFile(Base):
    __tablename__ = "report_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_type: Mapped[str] = mapped_column(String(20))  # weekly/monthly/yearly
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

