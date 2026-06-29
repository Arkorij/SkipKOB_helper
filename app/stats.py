"""Подсчёт статистики по сохранённым отметкам."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .models import (
    ABSENCE_KEYS,
    EXCUSED_KEYS,
    NEUTRAL_KEYS,
    STATUS_BY_KEY,
    UNEXCUSED_KEYS,
)


def _is_cons(m: dict) -> bool:
    c = m.get("consultation")
    if c is None:
        c = str(m.get("subject", "")).startswith("#")
    return bool(c)


@dataclass
class Stats:
    total_absences: int = 0
    excused: int = 0
    unexcused: int = 0
    full_days: int = 0
    passed: int = 0
    cancelled: int = 0
    cons_present: int = 0
    cons_total: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)   # ключ статуса -> кол-во
    by_subject: dict[str, int] = field(default_factory=dict)  # предмет -> кол-во прогулов
    by_subject_kind: dict[str, dict[str, int]] = field(default_factory=dict)  # предмет -> {тип -> кол-во}


def _is_full_day(marks: list[dict]) -> bool:
    """День полностью пропущен (см. правила в плане)."""
    countable = [
        m for m in marks
        if not _is_cons(m) and m["status"] not in NEUTRAL_KEYS
    ]
    if not countable:
        return False
    if any(m["status"] == "came" for m in countable):
        return False
    return all(m["status"] in ABSENCE_KEYS for m in countable)


def compute(data: dict) -> Stats:
    s = Stats()
    marks_by_date: dict[str, list[dict]] = data.get("marks", {})
    for iso, marks in marks_by_date.items():
        if not isinstance(marks, list):
            continue
        for m in marks:
            if not isinstance(m, dict):
                continue
            subject = m.get("subject", "")
            status = m.get("status", "")
            if _is_cons(m):
                s.cons_total += 1
                if status == "present":
                    s.cons_present += 1
                continue
            if status in ABSENCE_KEYS:
                s.total_absences += 1
                s.by_reason[status] = s.by_reason.get(status, 0) + 1
                s.by_subject[subject] = s.by_subject.get(subject, 0) + 1
                kind = m.get("kind", "lecture")
                bk = s.by_subject_kind.setdefault(subject, {})
                bk[kind] = bk.get(kind, 0) + 1
                if status in EXCUSED_KEYS:
                    s.excused += 1
                elif status in UNEXCUSED_KEYS:
                    s.unexcused += 1
            elif status == "passed":
                s.passed += 1
            elif status == "cancelled":
                s.cancelled += 1
        if _is_full_day(marks):
            s.full_days += 1
    return s


def absence_records(data: dict) -> list[tuple[date, str, str]]:
    """Список прогулов: (дата, предмет, ключ статуса), отсортированный по дате."""
    out: list[tuple[date, str, str]] = []
    for iso, marks in data.get("marks", {}).items():
        if not isinstance(marks, list):
            continue
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            continue
        for m in marks:
            if not isinstance(m, dict):
                continue
            if _is_cons(m):
                continue
            if m.get("status") in ABSENCE_KEYS:
                out.append((d, m["subject"], m["status"]))
    out.sort(key=lambda r: (r[0], r[1]))
    return out


def reason_label(key: str) -> str:
    st = STATUS_BY_KEY.get(key)
    return st.label if st else key
