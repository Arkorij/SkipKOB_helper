"""Страница 2 — расписание по неделям с отметками посещаемости."""
from __future__ import annotations

import threading
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


EDGE_ZONE = 90         # высота зон-подсказок сверху и снизу списка
OVER_TRIGGER = 60.0    # насколько нужно оттянуть список ЗА край для смены недели
OVER_RESET = 0.35      # пауза без протягивания, после которой накопленное сбрасывается
SWITCH_COOLDOWN = 0.9  # защита от повторного срабатывания сразу после смены
PULL_BAR_W = 150       # ширина индикатора протягивания
PULL_FPS = 1 / 120     # частота перерисовки индикатора
PULL_BACK_MS = 350     # за сколько полоска плавно возвращается назад


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
        self._last_over = 0.0
        self._last_visual = 0.0
        self._pull_timer: threading.Timer | None = None
        self._pull_top = None       # (иконка, подпись, заполнение) верхней подсказки
        self._pull_bottom = None    # то же для нижней

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
                ],
                spacing=2,
            ),
            padding=ft.padding.only(left=14, right=4, top=10, bottom=10),
            bgcolor=T.SURFACE,
        )

        self.days_list = self._new_list()
        # смена недели — плавным проявлением, а не рывком
        self.list_box = ft.AnimatedSwitcher(
            content=self.days_list,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=200,
            reverse_duration=120,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            expand=True,
        )
        self.view = ft.Column([header, self.list_box], expand=True, spacing=0)

    def _new_list(self):
        return ft.ListView(
            expand=True,
            spacing=12,
            padding=ft.padding.all(14),
            on_scroll=self._on_scroll,
        )

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

    def _on_scroll(self, e):
        """Смена недели: долистал до края — и намеренно оттянул дальше.

        Реагируем только на события протягивания за край. Их тип у Flet — 'over'
        (не 'overscroll', как можно подумать), поэтому раньше обработчик молчал.

        Отскок по инерции после броска тоже даёт такие события, но у них
        заполнена velocity — их пропускаем, иначе неделя менялась бы сама.
        Считается только протягивание пальцем, и только набрав OVER_TRIGGER
        в одну сторону.
        """
        if getattr(e, "event_type", None) != "over":
            return
        # инерционный отскок, а не намеренное протягивание
        if abs(getattr(e, "velocity", None) or 0.0) > 0.01:
            return
        ov = getattr(e, "overscroll", None) or 0.0
        if not ov:
            return

        now = time.time()
        if now - self._last_over > OVER_RESET:   # отпустили и подумали — копим заново
            self._over_accum = 0.0
        self._last_over = now
        if self._over_accum * ov < 0:            # потянули в другую сторону
            self._over_accum = 0.0
        self._over_accum += ov

        # подсветить прогресс жеста; сброс — по таймеру, событий об отпускании нет
        if now - self._last_visual >= PULL_FPS:
            self._last_visual = now
            self._show_pull(self._over_accum > 0, abs(self._over_accum) / OVER_TRIGGER)
        if self._pull_timer:
            self._pull_timer.cancel()
        self._pull_timer = threading.Timer(OVER_RESET, self._reset_pull)
        self._pull_timer.daemon = True
        self._pull_timer.start()

        if now - self._last_switch < SWITCH_COOLDOWN:
            return
        if self._over_accum >= OVER_TRIGGER:     # оттянули за низ — следующая неделя
            self._last_switch = now
            self._show_pull(True, 1.0)
            self._over_accum = 0.0
            self._change_week(1)
        elif self._over_accum <= -OVER_TRIGGER:  # оттянули за верх — прошлая неделя
            self._last_switch = now
            self._show_pull(False, 1.0)
            self._over_accum = 0.0
            self._change_week(-1)

    def _edge_hint(self, up: bool):
        """Зона-подсказка у края списка с индикатором протягивания.

        Полоска заполняется по мере оттягивания, чтобы было видно, что жест
        засчитывается, а не палец скользит по неподвижному экрану.
        """
        icon = ft.Icon(ft.Icons.KEYBOARD_ARROW_UP if up else ft.Icons.KEYBOARD_ARROW_DOWN,
                       size=22, color=T.TEXT_DIM)
        label = ft.Text("Прошлая неделя" if up else "Следующая неделя",
                        size=T.FS_HINT, color=T.TEXT_DIM)
        # анимация переключается: при протягивании — почти мгновенно (чтобы
        # полоска шла за пальцем), при отпускании — плавный возврат
        fill = ft.Container(width=0, height=4, bgcolor=T.ACCENT, border_radius=3,
                            animate=ft.Animation(60, ft.AnimationCurve.LINEAR))
        track = ft.Container(
            width=PULL_BAR_W, height=4, bgcolor=T.SURFACE_2, border_radius=3,
            alignment=ft.alignment.center_left, content=fill,
        )
        if up:
            self._pull_top = (icon, label, fill)
        else:
            self._pull_bottom = (icon, label, fill)
        return ft.Container(
            height=EDGE_ZONE,
            alignment=ft.alignment.center,
            content=ft.Column(
                [icon, label, track],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

    def _show_pull(self, down: bool, frac: float):
        """Отрисовать прогресс протягивания в нужной подсказке."""
        parts = self._pull_bottom if down else self._pull_top
        if not parts:
            return
        icon, label, fill = parts
        frac = max(0.0, min(1.0, frac))
        ready = frac >= 1.0
        color = T.ACCENT if ready else T.TEXT_DIM
        fill.animate = ft.Animation(60, ft.AnimationCurve.LINEAR)
        fill.width = PULL_BAR_W * frac
        fill.bgcolor = T.ACCENT if ready else T.color("BLUE_GREY_300")
        icon.color = color
        label.color = color
        try:
            fill.update()
            icon.update()
            label.update()
        except Exception:
            pass

    def _reset_pull(self):
        """Сбросить индикаторы, когда протягивание прекратилось."""
        self._over_accum = 0.0
        for parts in (self._pull_top, self._pull_bottom):
            if not parts:
                continue
            icon, label, fill = parts
            fill.animate = ft.Animation(PULL_BACK_MS, ft.AnimationCurve.EASE_OUT)
            fill.width = 0
            icon.color = T.TEXT_DIM
            label.color = T.TEXT_DIM
            try:
                fill.update()
                icon.update()
                label.update()
            except Exception:
                pass

    # --- выбор недели диалогом --------------------------------------------
    def _open_week_picker(self, e):
        page = self.app.page

        def pick(n):
            self.week = n
            self._save_week()
            page.close(dlg)
            self.refresh()

        def cell(n: int):
            sel = n == self.week
            odd = cal.is_odd(n)
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Container(width=4, height=24, border_radius=3,
                                     bgcolor="#10101A" if sel else (
                                         T.color("AMBER_300") if odd else T.color("TEAL_300"))),
                        ft.Text(
                            str(n), size=T.FS_SECTION,
                            weight=ft.FontWeight.BOLD if sel else ft.FontWeight.NORMAL,
                            color="#10101A" if sel else T.TEXT,
                        ),
                    ],
                    spacing=10, tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=118, height=58,
                alignment=ft.alignment.center,
                bgcolor=T.ACCENT if sel else T.SURFACE_2,
                border_radius=12,
                on_click=lambda e, k=n: pick(k),
            )

        # по два в ряду: слева нечётная, справа чётная — так же, как чередуются
        # базовые расписания
        rows = [
            ft.Row([cell(n), cell(n + 1)], spacing=10,
                   alignment=ft.MainAxisAlignment.CENTER)
            for n in range(1, TOTAL_WEEKS + 1, 2)
        ]

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=T.SURFACE,
            title=ft.Text("Выбор недели", color=T.TEXT, size=T.FS_SECTION),
            content=ft.Container(
                content=ft.Column(
                    rows,
                    spacing=10,
                    scroll=ft.ScrollMode.ALWAYS,   # полоса прокрутки видна всегда
                    tight=True,
                ),
                width=300, height=400,
                padding=ft.padding.only(right=10),   # место под полосу прокрутки
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
        # новый список — чтобы AnimatedSwitcher плавно сменил неделю
        self.days_list = self._new_list()
        self.days_list.controls = (
            [self._edge_hint(up=True)]
            + [self._day_card(d, n) for d in dates]
            + [self._edge_hint(up=False)]
        )
        self.list_box.content = self.days_list
        self._last_switch = time.time()   # не срабатывать сразу после перерисовки
        self._over_accum = 0.0            # накопленное протягивание не переносим
        self._safe_update()
        # встать сразу под верхней подсказкой, чтобы начинать с понедельника
        try:
            self.days_list.scroll_to(offset=EDGE_ZONE, duration=1)
        except Exception:
            pass

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
