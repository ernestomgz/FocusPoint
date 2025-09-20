from datetime import date
from pydantic import BaseModel, Field

# Minimal API schemas (more in Part 2)

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None

class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    category_id: int | None = None
    name: str
    objective: str | None = None
    description: str | None = None
    color: str | None = None
    end_date_dmy: str  # DD/MM/YYYY
    status: str = "active"

class MilestoneCreate(BaseModel):
    project_id: int
    name: str
    end_date_dmy: str
    percent_complete: int = 0
    status: str = "active"
    note: str | None = None
    dependent_to_id: int | None = None

class ActionCreate(BaseModel):
    project_id: int
    milestone_id: int | None = None
    date_dmy: str      # DD/MM/YYYY
    hhmm: str          # HH:MM
    comment: str | None = None

