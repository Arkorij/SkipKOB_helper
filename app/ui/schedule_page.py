"""Страница 2 — расписание по неделям с отметками посещаемости."""
from __future__ import annotations

import time
from datetime import date

import flet as ft

from .. import calendar_logic as cal
from .. import models
from .. import resolver
from ..calendar_logic import TOTAL_WEEKS
from ..models import (
    CONS_STATUS_BY_KEY,
    STATUS_BY_KEY,
    kind_color,
    kind_label,
    pair_is_consultation,
    pair_kind,
    pair_name,
    pair_statuses,
)
from . import theme as T
from . import widgets as W


OVERSCROLL_TRIGGER = 40.0   # накопленное перетягивание за край для смены недели


def _status_color(pair: dict, key: str) -> str:
    table = CONS_STATUS_BY_KEY if pair_is_consultation(pair) else STATUS_BY_KEY
    st = table.get(key)
    return st.color if st else "BLUE_GREY_400"


class SchedulePage:
    def __init__(self, app):
        self.app = app
        self.week: int | None = None
        self._last_switch = 0.0
        self._over_accum = 0.0

        self.week_label = ft.Text("", size=T.FS_SECTION, weight=ft.FontWeight.BOLD, color=T.TEXT)
        self.parity_badge = ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=20,
        )
        # Компактная кнопка выбора недели (вместо Dropdown: его popup рисуется
        # поверх всего экрана и залезает под строку состояния и кнопки навигации).
        self.week_btn_text = ft.Text("", size=T.FS_LABEL, weight=ft.FontWeight.BOLD, color=T.TEXT)
        self.week_btn = ft.Container(
            content=ft.Row(
                [self.week_btn_text, ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=20, color=T.TEXT_DIM)],
                spacing=0, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=12, right=4, top=8, bottom=8),
            border=ft.border.all(1, T.BORDER),
            border_radius=10,
            tooltip="Выбрать неделю",
            on_click=self._open_week_picker,
        )
        header = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row([self.week_label, self.parity_badge], spacing=8,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(expand=True),
                            self.week_btn,
                            ft.IconButton(
                                ft.Icons.KEYBOARD_ARROW_UP,
                                tooltip="Прошлая неделя",
                                icon_color=T.TEXT_DIM, icon_size=22,
                                on_click=lambda e: self._change_week(-1),
                            ),
                            ft.IconButton(
                                ft.Icons.KEYBOARD_ARROW_DOWN,
                                tooltip="Следующая неделя",
                                icon_color=T.TEXT_DIM, icon_size=22,
                                on_click=lambda e: self._change_week(1),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    ft.Text("свайп вбок или ↑↓ у края — смена недели",
                            size=T.FS_HINT, color=T.TEXT_DIM),
                ],
                spacing=2,
            ),
            padding=ft.padding.only(left=14, right=4, top=10, bottom=10),
            bgcolor=T.SURFACE,
        )

        self.days_list = ft.ListView(
            expand=True,
            spacing=12,
            padding=ft.padding.all(14),
            on_scroll=self._on_scroll,
        )
        # Горизонтальный свайп не конфликтует с вертикальной прокруткой списка,
        # поэтому срабатывает надёжно; вертикальный overscroll оставлен как доп. способ.
        swipe_area = ft.GestureDetector(
            content=self.days_list,
            on_horizontal_drag_end=self._on_h_swipe,
            expand=True,
        )
        self.view = ft.Column([header, swipe_area], expand=True, spacing=0)

    # --- неделя -----------------------------------------------------------
    def _ensure_week(self):
        if self.week is None:
            d = self.app.data
            last = d.get("last_week")
            if isinstance(last, int) and 1 <= last <= TOTAL_WEEKS:
                self.week = last
            else:
                self.week = cal.current_week_number(d["academic_year_start"], d["breaks"])

    def _save_week(self):
        self.app.data["last_week"] = self.week
        self.app.persist()

    def _change_week(self, delta: int):
        self._ensure_week()
        self.week = max(1, min(TOTAL_WEEKS, self.week + delta))
        self._save_week()
        self.refresh()

    def _on_h_swipe(self, e):
        """Свайп вбок: влево — следующая неделя, вправо — прошлая."""
        v = getattr(e, "primary_velocity", None) or 0
        if abs(v) < 150:
            return
        now = time.time()
        if now - self._last_switch < 0.5:
            return
        self._last_switch = now
        self._change_week(1 if v < 0 else -1)

    def _on_scroll(self, e):
        """Вертикальный overscroll: тянем за край списка — меняем неделю.

        События overscroll приходят маленькими порциями, поэтому копим сумму
        в одном направлении и срабатываем при заметном перетягивании.
        """
        etype = getattr(e, "event_type", None)
        if etype != "overscroll":
            if etype in ("start", "user"):
                self._over_accum = 0.0
            return
        now = time.time()
        if now - self._last_switch < 0.8:
            return
        ov = getattr(e, "overscroll", 0) or 0
        if self._over_accum * ov < 0:     # сменилось направление — копим заново
            self._over_accum = 0.0
        self._over_accum += ov
        if self._over_accum < -OVERSCROLL_TRIGGER:    # за верх -> прошлая неделя
            self._last_switch = now
            self._over_accum = 0.0
            self._change_week(-1)
        elif self._over_accum > OVERSCROLL_TRIGGER:   # за низ -> следующая неделя
            self._last_switch = now
            self._over_accum = 0.0
            self._change_week(1)

    # --- выбор недели диалогом --------------------------------------------
    def _open_week_picker(self, e):
        page = self.app.page

        def pick(n):
            self.week = n
            self._save_week()
            page.close(dlg)
            self.refresh()

        cells = []
        for n in range(1, TOTAL_WEEKS + 1):
            sel = n == self.week
            cells.append(ft.Container(
                content=ft.Text(
                    str(n), size=T.FS_BODY,
                    weight=ft.FontWeight.BOLD if sel else ft.FontWeight.NORMAL,
                    color="#10101A" if sel else T.TEXT,
                ),
                width=54, height=46,
                alignment=ft.alignment.center,
                bgcolor=T.ACCENT if sel else T.SURFACE_2,
                border_radius=10,
                on_click=lambda e, k=n: pick(k),
            ))

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=T.SURFACE,
            title=ft.Text("Выбор недели", color=T.TEXT, size=T.FS_SECTION),
            content=ft.Container(
                content=ft.Column(
                    [ft.Row(cells, wrap=True, spacing=8, run_spacing=8)],
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
                width=320, height=360,
            ),
            actions=[ft.TextButton("Отмена", on_click=lambda e: page.close(dlg))],
        )
        page.open(dlg)

    # --- построение -------------------------------------------------------
    def build(self):
        self.refresh()
        return self.view

    def refresh(self):
        self._ensure_week()
        n = self.week
        self.week_label.value = f"Неделя {n}"
        odd = cal.is_odd(n)
        self.parity_badge.content = ft.Text(
            cal.parity_label(n), size=T.FS_CHIP, weight=ft.FontWeight.BOLD, color="#10101A",
        )
        self.parity_badge.bgcolor = T.color("AMBER_300") if odd else T.color("TEAL_300")
        self.week_btn_text.value = str(n)

        data = self.app.data
        dates = cal.dates_for_week(data["academic_year_start"], data["breaks"], n)
        self.days_list.controls = [self._day_card(d, n) for d in dates]
        self._safe_update()

    def _safe_update(self):
        try:
            self.view.update()
        except Exception:
            pass

    def _day_card(self, d: date, week_n: int):
        data = self.app.data
        day_key = cal.DAYS[d.weekday()]
        pairs = resolver.pairs_for_date(data, d, week_n)
        marks = resolver.day_marks(data, d, pairs)
        is_override = d.isoformat() in data.get("overrides", {})
        today = d == date.today()

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(cal.DAY_NAMES_RU[day_key], size=T.FS_SECTION, weight=ft.FontWeight.BOLD,
                                color=T.ACCENT if today else T.TEXT),
                        ft.Text(cal.format_date(d), size=T.FS_HINT, color=T.TEXT_DIM),
                    ],
                    spacing=1,
                ),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text("изменён", size=T.FS_CHIP, color="#10101A",
                                            weight=ft.FontWeight.BOLD),
                            bgcolor=T.color("ORANGE_300"),
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            border_radius=20,
                        ) if is_override else ft.Container(),
                        ft.IconButton(
                            ft.Icons.EDIT_CALENDAR_OUTLINED,
                            icon_size=22, icon_color=T.TEXT_DIM,
                            tooltip="Изменить пары этого дня",
                            on_click=lambda e, dd=d, wk=week_n: self._edit_day(dd, wk),
                        ),
                    ],
                    spacing=4,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        if pairs:
            rows = [self._pair_row(d, pairs, i, marks[i]) for i in range(len(pairs))]
            body = ft.Column(rows, spacing=10)
        else:
            body = ft.Text("Нет пар", size=T.FS_HINT, color=T.TEXT_DIM, italic=True)

        return W.card(
            ft.Column([header, ft.Divider(height=14, color=T.BORDER), body], spacing=6),
            border=ft.border.all(1, T.ACCENT if today else T.BORDER),
        )

    def _chip(self, text: str, bg: str):
        return ft.Container(
            content=ft.Text(text, size=T.FS_CHIP, weight=ft.FontWeight.BOLD, color="#10101A"),
            bgcolor=bg,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=20,
        )

    def _kind_chip(self, pair: dict):
        if pair_is_consultation(pair):
            return self._chip(models.CONSULTATION_LABEL, T.color(models.CONSULTATION_COLOR))
        kind = pair_kind(pair)
        return self._chip(kind_label(kind), T.color(kind_color(kind)))

    def _pair_row(self, d: date, pairs: list[dict], index: int, mark: dict):
        pair = pairs[index]
        cons = pair_is_consultation(pair)
        status_key = mark["status"]
        dot = ft.Container(
            width=10, height=10, border_radius=10,
            bgcolor=T.color(_status_color(pair, status_key)),
        )
        opts = [ft.dropdown.Option(s.key, s.label) for s in pair_statuses(pair)]
        dd = ft.Dropdown(
            value=status_key, options=opts, dense=True, text_size=T.FS_LABEL, width=168,
            border_color=T.BORDER,
            on_change=self._make_status_handler(d, pairs, index, dot),
        )
        name = ft.Text(
            pair_name(pair),
            size=T.FS_BODY, color=T.TEXT_CONS if cons else T.TEXT,
            expand=True, no_wrap=False,
        )
        top = ft.Row(
            [self._kind_chip(pair), name],
            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        bottom = ft.Row(
            [dot, dd],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Container(content=ft.Column([top, bottom], spacing=6))

    def _make_status_handler(self, d: date, pairs: list[dict], index: int, dot):
        def handler(e):
            key = e.control.value
            resolver.set_mark(self.app.data, d, pairs, index, key)
            self.app.persist()
            dot.bgcolor = T.color(_status_color(pairs[index], key))
            dot.update()
        return handler

    # --- редактирование пар конкретного дня -------------------------------
    def _edit_day(self, d: date, week_n: int):
        data = self.app.data
        pairs = resolver.pairs_for_date(data, d, week_n)
        field = ft.TextField(
            value="\n".join(models.format_pair(p) for p in pairs),
            multiline=True, min_lines=5, max_lines=12, text_size=T.FS_BODY,
            border_color=T.BORDER,
            label="Пары (по одной в строке)",
        )
        page = self.app.page

        def save(e):
            lines = [models.parse_pair(ln) for ln in field.value.split("\n") if ln.strip()]
            data.setdefault("overrides", {})[d.isoformat()] = lines
            data.get("marks", {}).pop(d.isoformat(), None)
            self.app.persist()
            self._close_dialog()
            self.refresh()

        def reset(e):
            data.get("overrides", {}).pop(d.isoformat(), None)
            data.get("marks", {}).pop(d.isoformat(), None)
            self.app.persist()
            self._close_dialog()
            self.refresh()

        self._dialog = ft.AlertDialog(
            modal=True,
            bgcolor=T.SURFACE,
            title=ft.Text(f"{cal.DAY_NAMES_RU[cal.DAYS[d.weekday()]]}, {cal.format_date(d)}",
                          color=T.TEXT, size=T.FS_SECTION),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Префиксы: # — консультация, * — практика, ~ — лаб (без знака — лекция)",
                            size=T.FS_HINT, color=T.TEXT_DIM),
                    field,
                ], spacing=8, tight=True),
                width=360,
            ),
            actions=[
                ft.TextButton("Сбросить к базе", on_click=reset,
                              style=ft.ButtonStyle(color=T.color("RED_300"))),
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog()),
                W.primary_button("Сохранить", save),
            ],
        )
        page.open(self._dialog)

    def _close_dialog(self):
        if getattr(self, "_dialog", None):
            self.app.page.close(self._dialog)
