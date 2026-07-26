"""Учебный календарь: номера недель, чётность, пропуск каникул."""
from __future__ import annotations

from datetime import date, timedelta

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat"]  # Пн..Сб
DAY_NAMES_RU = {
    "mon": "Понедельник",
    "tue": "Вторник",
    "wed": "Среда",
    "thu": "Четверг",
    "fri": "Пятница",
    "sat": "Суббота",
}
DAY_SHORT_RU = {
    "mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт", "sat": "Сб",
}
MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
TOTAL_WEEKS = 40


def academic_year_for_date(d: date) -> int:
    """К какому учебному году (по 1 сентября) относится дата."""
    return d.year if d.month >= 9 else d.year - 1


def first_monday(year_start: int) -> date:
    """Понедельник недели, в которую попадает 1 сентября."""
    sept1 = date(year_start, 9, 1)
    return sept1 - timedelta(days=sept1.weekday())


def _parse_break(b: dict) -> tuple[date, date] | None:
    try:
        s = date.fromisoformat(b["start"])
        e = date.fromisoformat(b["end"])
    except (KeyError, ValueError, TypeError):
        return None
    if e < s:
        s, e = e, s
    return s, e


def _monday_in_break(monday: date, breaks: list[dict]) -> bool:
    """Неделя считается каникулярной, если её понедельник попал в каникулы."""
    for b in breaks:
        rng = _parse_break(b)
        if rng and rng[0] <= monday <= rng[1]:
            return True
    return False


def week_mondays(year_start: int, breaks: list[dict], total: int = TOTAL_WEEKS) -> dict[int, date]:
    """Сопоставление номер учебной недели (1..total) -> понедельник, пропуская каникулы."""
    mondays: dict[int, date] = {}
    m = first_monday(year_start)
    n = 0
    guard = 0
    while n < total and guard < total + 120:
        guard += 1
        if not _monday_in_break(m, breaks):
            n += 1
            mondays[n] = m
        m = m + timedelta(days=7)
    return mondays


def dates_for_week(year_start: int, breaks: list[dict], n: int) -> list[date]:
    """Список дат Пн..Сб для учебной недели n."""
    monday = week_mondays(year_start, breaks).get(n)
    if monday is None:
        return []
    return [monday + timedelta(days=i) for i in range(6)]


def is_odd(n: int) -> bool:
    return n % 2 == 1


def parity_key(n: int) -> str:
    return "odd" if is_odd(n) else "even"


def parity_label(n: int) -> str:
    return "нечётная" if is_odd(n) else "чётная"


def current_week_number(year_start: int, breaks: list[dict], today: date | None = None) -> int:
    """Номер учебной недели, в которую попадает дата (с защёлкиванием в диапазон)."""
    today = today or date.today()
    mondays = week_mondays(year_start, breaks)
    if not mondays:
        return 1
    for n, mon in mondays.items():
        if mon <= today <= mon + timedelta(days=6):
            return n
    if today < mondays[1]:
        return 1
    return max(mondays.keys())


def week_number_for_date(year_start: int, breaks: list[dict], d: date) -> int | None:
    """Точный номер недели для даты или None, если дата вне учебных недель (каникулы)."""
    mondays = week_mondays(year_start, breaks)
    for n, mon in mondays.items():
        if mon <= d <= mon + timedelta(days=5):  # Пн..Сб
            return n
    return None


def format_date(d: date) -> str:
    return f"{d.day} {MONTHS_RU[d.month]}"


def format_date_short(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}.{d.year}"
