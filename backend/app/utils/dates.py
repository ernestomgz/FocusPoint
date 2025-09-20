from datetime import date, timedelta

def monday_of(d: date) -> date:
    # Monday as 0
    return d - timedelta(days=(d.weekday()))

def week_bounds(d: date) -> tuple[date, date]:
    start = monday_of(d)
    end = start + timedelta(days=6)
    return start, end

def month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    if d.month == 12:
        end = d.replace(day=31)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
        end = next_month - timedelta(days=1)
    return start, end

def year_bounds(d: date) -> tuple[date, date]:
    start = d.replace(month=1, day=1)
    end = d.replace(month=12, day=31)
    return start, end

