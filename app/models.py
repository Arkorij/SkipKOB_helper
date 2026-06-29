"""Доменные модели: статусы посещаемости и представление пары."""
from __future__ import annotations

from dataclasses import dataclass

CONSULTATION_PREFIX = "#"

# Категории для подсчёта статистики
CAT_CAME = "came"            # пришёл — не прогул
CAT_EXCUSED = "excused"      # уважительная причина
CAT_UNEXCUSED = "unexcused"  # неуважительная причина
CAT_NEUTRAL = "neutral"      # не считается прогулом (всё сдал / отменено)
CAT_CONS_ABSENT = "cons_absent"
CAT_CONS_PRESENT = "cons_present"


@dataclass(frozen=True)
class Status:
    key: str
    label: str
    category: str
    color: str        # цвет кружка в расписании (имя атрибута ft.Colors)
    chart_color: str  # оттенок для диаграммы (чтобы похожие статусы различались)


# --- Статусы обычной пары -------------------------------------------------
# Кружок: пришёл — зелёный; справка/уваж. — оранжевый; проспал/не захотел/нет сил —
# красный; всё сдал — фиолетовый; отменена — серый. На диаграмме — лёгкие оттенки.
STATUSES: list[Status] = [
    Status("came", "Пришёл", CAT_CAME, "GREEN_400", "GREEN_400"),
    Status("medical", "Справка", CAT_EXCUSED, "ORANGE_400", "AMBER_300"),
    Status("excused", "Уваж. причина", CAT_EXCUSED, "ORANGE_400", "ORANGE_500"),
    Status("overslept", "Проспал", CAT_UNEXCUSED, "RED_400", "RED_300"),
    Status("skipped", "Не захотел", CAT_UNEXCUSED, "RED_400", "RED_400"),
    Status("no_energy", "Нет сил", CAT_UNEXCUSED, "RED_400", "RED_600"),
    Status("passed", "Всё сдал", CAT_NEUTRAL, "PURPLE_300", "PURPLE_300"),
    Status("cancelled", "Пара отменена", CAT_NEUTRAL, "BLUE_GREY_400", "BLUE_GREY_400"),
]
STATUS_BY_KEY: dict[str, Status] = {s.key: s for s in STATUSES}
DEFAULT_STATUS = "came"

# --- Статусы консультации -------------------------------------------------
CONS_STATUSES: list[Status] = [
    Status("not_came", "Не пришёл", CAT_CONS_ABSENT, "BLUE_GREY_400", "BLUE_GREY_400"),
    Status("present", "Пришёл", CAT_CONS_PRESENT, "GREEN_400", "GREEN_400"),
]
CONS_STATUS_BY_KEY: dict[str, Status] = {s.key: s for s in CONS_STATUSES}
CONS_DEFAULT_STATUS = "not_came"

# Множества статусов прогула
ABSENCE_KEYS = {"medical", "excused", "overslept", "skipped", "no_energy"}
EXCUSED_KEYS = {"medical", "excused"}
UNEXCUSED_KEYS = {"overslept", "skipped", "no_energy"}
NEUTRAL_KEYS = {"passed", "cancelled"}

# --- Тип занятия (для цветного значка у пары) -----------------------------
KIND_LECTURE = "lecture"
KIND_PRACTICE = "practice"
KIND_LAB = "lab"
KINDS = (KIND_LECTURE, KIND_PRACTICE, KIND_LAB)
KIND_LABELS = {KIND_LECTURE: "Лекция", KIND_PRACTICE: "Практика", KIND_LAB: "Лабораторная"}
KIND_SHORT = {KIND_LECTURE: "Лек", KIND_PRACTICE: "Прк", KIND_LAB: "Лаб"}
KIND_COLORS = {KIND_LECTURE: "GREEN_400", KIND_PRACTICE: "YELLOW_600", KIND_LAB: "BLUE_400"}
CONSULTATION_LABEL = "Консультация"
CONSULTATION_COLOR = "PINK_300"


def kind_label(kind: str) -> str:
    return KIND_LABELS.get(kind, KIND_LABELS[KIND_LECTURE])


def kind_short(kind: str) -> str:
    return KIND_SHORT.get(kind, KIND_SHORT[KIND_LECTURE])


def kind_color(kind: str) -> str:
    return KIND_COLORS.get(kind, KIND_COLORS[KIND_LECTURE])


# --- Пара: dict {name, kind, consultation} --------------------------------
def make_pair(name: str, kind: str = KIND_LECTURE, consultation: bool = False) -> dict:
    return {
        "name": str(name).strip(),
        "kind": kind if kind in KINDS else KIND_LECTURE,
        "consultation": bool(consultation),
    }


def pair_name(p: dict) -> str:
    return p.get("name", "")


def pair_kind(p: dict) -> str:
    return p.get("kind", KIND_LECTURE)


def pair_is_consultation(p: dict) -> bool:
    return bool(p.get("consultation"))


def pair_default_status(p: dict) -> str:
    return CONS_DEFAULT_STATUS if pair_is_consultation(p) else DEFAULT_STATUS


def pair_statuses(p: dict) -> list[Status]:
    return CONS_STATUSES if pair_is_consultation(p) else STATUSES


def parse_pair(line: str) -> dict:
    """Разбор строки редактора. Префиксы: '#'=консультация, '*'=практика, '~'=лаб, '^'=лекция."""
    s = str(line).strip()
    consultation = False
    kind = KIND_LECTURE
    while s[:1] in ("#", "*", "~", "^"):
        c = s[0]
        if c == "#":
            consultation = True
        elif c == "*":
            kind = KIND_PRACTICE
        elif c == "~":
            kind = KIND_LAB
        elif c == "^":
            kind = KIND_LECTURE
        s = s[1:].lstrip()
    return make_pair(s, kind, consultation)


def format_pair(p: dict) -> str:
    """Строка для редактора (обратимо к parse_pair)."""
    pre = ""
    if pair_is_consultation(p):
        pre += "#"
    k = pair_kind(p)
    if k == KIND_PRACTICE:
        pre += "*"
    elif k == KIND_LAB:
        pre += "~"
    return (pre + " " if pre else "") + pair_name(p)


def coerce_pair(item) -> dict:
    """Приводит элемент (dict или строку) к паре."""
    if isinstance(item, dict):
        return make_pair(item.get("name", ""), item.get("kind", KIND_LECTURE),
                         item.get("consultation", False))
    return parse_pair(str(item))
