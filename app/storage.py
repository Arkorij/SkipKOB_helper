"""Локальное хранилище данных (JSON) + экспорт/импорт расписания."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from . import models
from .calendar_logic import DAYS, academic_year_for_date

APP_NAME = "SkipKOB_Helper"
DATA_FILENAME = "data.json"

# Поля, относящиеся к «основе» расписания (экспортируются/импортируются)
BASE_FIELDS = ("academic_year_start", "breaks", "base_schedule")


def data_dir() -> Path:
    """Папка для данных. На упакованном Flet (Android/desktop) — FLET_APP_STORAGE_DATA,
    иначе %APPDATA%/SkipKOB_Helper (Windows) или ~/.SkipKOB_Helper."""
    storage = os.getenv("FLET_APP_STORAGE_DATA")
    if storage:
        p = Path(storage)
    else:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_file() -> Path:
    return data_dir() / DATA_FILENAME


def empty_schedule() -> dict:
    return {"odd": {d: [] for d in DAYS}, "even": {d: [] for d in DAYS}}


def default_data() -> dict:
    return {
        "academic_year_start": academic_year_for_date(date.today()),
        "breaks": [],
        "base_schedule": empty_schedule(),
        "overrides": {},
        "marks": {},
        "last_week": None,
    }


def _normalize(data: dict) -> dict:
    """Гарантирует наличие всех полей и корректную структуру расписания."""
    base = default_data()
    if not isinstance(data, dict):
        return base
    out = base
    if isinstance(data.get("academic_year_start"), int):
        out["academic_year_start"] = data["academic_year_start"]
    if isinstance(data.get("breaks"), list):
        out["breaks"] = [b for b in data["breaks"] if isinstance(b, dict)]
    sched = data.get("base_schedule")
    if isinstance(sched, dict):
        for parity in ("odd", "even"):
            par = sched.get(parity, {})
            if isinstance(par, dict):
                for d in DAYS:
                    lst = par.get(d, [])
                    if isinstance(lst, list):
                        out["base_schedule"][parity][d] = [models.coerce_pair(x) for x in lst]
    if isinstance(data.get("overrides"), dict):
        out["overrides"] = {
            k: [models.coerce_pair(x) for x in v]
            for k, v in data["overrides"].items()
            if isinstance(v, list)
        }
    if isinstance(data.get("marks"), dict):
        out["marks"] = data["marks"]
    if isinstance(data.get("last_week"), int):
        out["last_week"] = data["last_week"]
    return out


def load_data() -> dict:
    path = data_file()
    if not path.exists():
        d = default_data()
        save_data(d)
        return d
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _normalize(json.load(f))
    except (json.JSONDecodeError, OSError):
        return default_data()


def save_data(data: dict) -> None:
    path = data_file()
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def reset_data() -> dict:
    """Полный сброс к значениям по умолчанию."""
    d = default_data()
    save_data(d)
    return d


# --- Экспорт / импорт расписания (отдельный читаемый JSON) ----------------
def export_schedule(data: dict, path: str) -> None:
    payload = {
        "_format": "SkipKOB_Helper schedule",
        "academic_year_start": data["academic_year_start"],
        "breaks": data["breaks"],
        "base_schedule": data["base_schedule"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def import_schedule(data: dict, path: str) -> dict:
    """Перезаписывает основу (год/каникулы/расписание), не трогая marks/overrides."""
    with open(path, "r", encoding="utf-8") as f:
        incoming = json.load(f)
    merged = dict(data)
    norm = _normalize({**data, **{k: incoming.get(k) for k in BASE_FIELDS if k in incoming}})
    for k in BASE_FIELDS:
        merged[k] = norm[k]
    save_data(merged)
    return merged
