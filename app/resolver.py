"""Резолв пар дня (override/база по чётности) и работа с отметками."""
from __future__ import annotations

from datetime import date

from . import calendar_logic as cal
from . import models


def pairs_for_date(data: dict, d: date, week_n: int) -> list[dict]:
    """Список пар на дату: ручной override дня, иначе база по чётности недели."""
    iso = d.isoformat()
    overrides = data.get("overrides", {})
    if iso in overrides:
        return [models.coerce_pair(x) for x in overrides[iso]]
    # До 1 сентября учебного года пар нет (дни первой недели, попавшие в август).
    if d < date(data["academic_year_start"], 9, 1):
        return []
    parity = cal.parity_key(week_n)
    day_key = cal.DAYS[d.weekday()] if d.weekday() < len(cal.DAYS) else None
    if day_key is None:
        return []
    return [models.coerce_pair(x) for x in data["base_schedule"][parity].get(day_key, [])]


def day_marks(data: dict, d: date, pairs: list[dict]) -> list[dict]:
    """Отметки дня, выровненные по `pairs`. Недостающие — дефолтные.

    Каждый элемент: {"subject", "status", "consultation"}.
    """
    stored = data.get("marks", {}).get(d.isoformat(), [])
    result: list[dict] = []
    for i, p in enumerate(pairs):
        name = models.pair_name(p)
        cons = models.pair_is_consultation(p)
        status = None
        if i < len(stored) and isinstance(stored[i], dict) and stored[i].get("subject") == name:
            status = stored[i].get("status")
        if status is None:
            status = models.pair_default_status(p)
        result.append({
            "subject": name, "status": status,
            "consultation": cons, "kind": models.pair_kind(p),
        })
    return result


def set_mark(data: dict, d: date, pairs: list[dict], index: int, status: str) -> None:
    """Сохраняет статус для пары index, снапшотя весь день."""
    marks = day_marks(data, d, pairs)
    if 0 <= index < len(marks):
        marks[index]["status"] = status
    data.setdefault("marks", {})[d.isoformat()] = marks
