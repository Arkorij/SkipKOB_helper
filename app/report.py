"""Генерация Markdown-отчёта о прогулах (для чтения и анализа ИИ)."""
from __future__ import annotations

from datetime import date

from . import calendar_logic as cal
from . import stats as stats_mod
from .stats import reason_label


def build_markdown(data: dict) -> str:
    s = stats_mod.compute(data)
    records = stats_mod.absence_records(data)
    today = date.today()

    lines: list[str] = []
    lines.append("# Отчёт о прогулах — SkipKOB_Helper")
    lines.append("")
    lines.append(f"_Сформировано: {cal.format_date_short(today)}_")
    lines.append("")
    lines.append("## Краткая статистика")
    lines.append("")
    lines.append(f"- Всего прогулов (пар): **{s.total_absences}**")
    lines.append(f"  - по уважительной причине: **{s.excused}**")
    lines.append(f"  - по неуважительной причине: **{s.unexcused}**")
    lines.append(f"- Полностью пропущенных дней: **{s.full_days}**")
    lines.append(f"- Пар «всё сдал»: {s.passed}")
    lines.append(f"- Отменённых пар: {s.cancelled}")
    lines.append(f"- Посещено консультаций: {s.cons_present} из {s.cons_total}")
    lines.append("")

    if s.by_reason:
        lines.append("### По причинам")
        lines.append("")
        for key, cnt in sorted(s.by_reason.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {reason_label(key)}: {cnt}")
        lines.append("")

    if s.by_subject:
        lines.append("### По предметам")
        lines.append("")
        for subj, cnt in sorted(s.by_subject.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {subj}: {cnt}")
        lines.append("")

    lines.append("## Подробности по каждому прогулу")
    lines.append("")
    if not records:
        lines.append("_Прогулов нет._")
    else:
        lines.append("| Дата | Предмет | Причина |")
        lines.append("| --- | --- | --- |")
        for d, subject, status in records:
            day = cal.DAY_SHORT_RU.get(cal.DAYS[d.weekday()], "") if d.weekday() < 6 else ""
            date_str = f"{cal.format_date_short(d)} ({day})" if day else cal.format_date_short(d)
            lines.append(f"| {date_str} | {subject} | {reason_label(status)} |")
    lines.append("")
    return "\n".join(lines)
