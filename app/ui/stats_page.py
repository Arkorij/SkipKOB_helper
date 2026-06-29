"""Страница 1 — инфографика и статистика."""
from __future__ import annotations

import flet as ft

from .. import models
from .. import stats as stats_mod
from ..models import STATUS_BY_KEY
from . import theme as T
from . import widgets as W


class StatsPage:
    def __init__(self, app):
        self.app = app
        self._subjects_detail = True
        self.view = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=16)

    def build(self):
        self.refresh()
        return self.view

    def refresh(self):
        s = stats_mod.compute(self.app.data)
        self.view.controls = [
            ft.Text("Статистика прогулов", size=20, weight=ft.FontWeight.BOLD, color=T.TEXT),
            ft.Row([
                W.stat_card("Всего прогулов", s.total_absences, T.color("RED_300"),
                            ft.Icons.EVENT_BUSY),
                W.stat_card("Полных дней", s.full_days, T.color("DEEP_ORANGE_300"),
                            ft.Icons.TODAY),
            ], spacing=12),
            ft.Row([
                W.stat_card("Уважительные", s.excused, T.color("BLUE_300"),
                            ft.Icons.VERIFIED_OUTLINED),
                W.stat_card("Неуважительные", s.unexcused, T.color("ORANGE_300"),
                            ft.Icons.REPORT_GMAILERRORRED),
            ], spacing=12),
            self._reasons_card(s),
            self._subjects_card(s),
            self._extra_card(s),
        ]
        self._safe_update()

    def _safe_update(self):
        try:
            self.view.update()
        except Exception:
            pass

    def _reasons_card(self, s: stats_mod.Stats):
        if not s.by_reason:
            return W.card(
                ft.Column([
                    W.section_title("Причины прогулов"),
                    ft.Text("Пока нет прогулов", size=12, color=T.TEXT_DIM, italic=True),
                ], spacing=8),
                border=ft.border.all(1, T.BORDER),
            )
        total = sum(s.by_reason.values())
        sections = []
        legend = []
        for key, cnt in sorted(s.by_reason.items(), key=lambda kv: -kv[1]):
            st = STATUS_BY_KEY[key]
            col = T.color(st.chart_color)
            pct = round(cnt / total * 100)
            sections.append(ft.PieChartSection(
                value=cnt, title=f"{pct}%", color=col, radius=55,
                title_style=ft.TextStyle(size=11, color="#10101A", weight=ft.FontWeight.BOLD),
            ))
            legend.append(ft.Row([
                ft.Container(width=12, height=12, border_radius=6, bgcolor=col),
                ft.Text(f"{st.label} — {cnt}", size=12, color=T.TEXT),
            ], spacing=8))
        chart = ft.PieChart(sections=sections, sections_space=2,
                            center_space_radius=30, height=180, expand=True)
        return W.card(
            ft.Column([
                W.section_title("Причины прогулов"),
                ft.Row([chart, ft.Column(legend, spacing=6)],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            ], spacing=10),
            border=ft.border.all(1, T.BORDER),
        )

    def _toggle_subjects(self, e):
        self._subjects_detail = not self._subjects_detail
        self.refresh()

    def _subjects_card(self, s: stats_mod.Stats):
        if not s.by_subject:
            return ft.Container()
        toggle = ft.TextButton(
            "Детально" if not self._subjects_detail else "Суммарно",
            icon=ft.Icons.TUNE,
            on_click=self._toggle_subjects,
            style=ft.ButtonStyle(
                color=T.ACCENT,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                shape=ft.RoundedRectangleBorder(radius=10),
                bgcolor=T.SURFACE_2,
            ),
        )
        header = ft.Row(
            [W.section_title("Прогулы по предметам"), toggle],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        body = self._subjects_detailed(s) if self._subjects_detail else self._subjects_summary(s)
        return W.card(
            ft.Column([header, body], spacing=12),
            border=ft.border.all(1, T.BORDER),
        )

    def _bar_track(self, cnt: int, maxv: int, color: str = None):
        """Полоса, растягивающаяся по ширине блока (flex), с запасом справа."""
        color = color or T.ACCENT
        headroom = max(1, round(maxv * 0.18))   # чтобы самая длинная не упиралась вправо
        total = maxv + headroom
        filled = max(1, cnt)
        return ft.Row(
            [
                ft.Container(height=14, bgcolor=color, border_radius=8, expand=filled),
                ft.Container(expand=max(1, total - filled)),
            ],
            expand=True, spacing=0,
        )

    def _subjects_summary(self, s: stats_mod.Stats):
        items = sorted(s.by_subject.items(), key=lambda kv: -kv[1])[:10]
        maxv = max(v for _, v in items)
        rows = []
        for subj, cnt in items:
            rows.append(ft.Row([
                ft.Container(
                    content=ft.Text(subj, size=12, color=T.TEXT, no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                    width=120,
                ),
                self._bar_track(cnt, maxv),
                ft.Text(str(cnt), size=14, weight=ft.FontWeight.BOLD, color=T.TEXT, width=26,
                        text_align=ft.TextAlign.RIGHT),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, height=24))
        return ft.Column(rows, spacing=8)

    def _kind_chip(self, kind: str):
        return ft.Container(
            content=ft.Text(models.kind_short(kind), size=9, weight=ft.FontWeight.BOLD,
                            color="#10101A"),
            bgcolor=T.color(models.kind_color(kind)),
            padding=ft.padding.symmetric(horizontal=7, vertical=3),
            border_radius=20,
        )

    def _subjects_detailed(self, s: stats_mod.Stats):
        # строка = предмет + тип; полосы как в суммарном, пересортировка под новые числа
        entries = []
        for subj, kinds in s.by_subject_kind.items():
            for k in models.KINDS:
                cnt = kinds.get(k, 0)
                if cnt:
                    entries.append((subj, k, cnt))
        entries.sort(key=lambda e: -e[2])
        entries = entries[:14]
        if not entries:
            return ft.Column([])
        maxv = max(e[2] for e in entries)
        rows = []
        for subj, kind, cnt in entries:
            rows.append(ft.Row([
                ft.Container(
                    content=ft.Text(subj, size=12, color=T.TEXT, no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                    width=105,
                ),
                self._kind_chip(kind),
                self._bar_track(cnt, maxv),
                ft.Text(str(cnt), size=14, weight=ft.FontWeight.BOLD, color=T.TEXT, width=26,
                        text_align=ft.TextAlign.RIGHT),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, height=24))
        return ft.Column(rows, spacing=8)

    def _extra_card(self, s: stats_mod.Stats):
        def line(label, value, color, icon):
            return ft.Row([
                ft.Icon(icon, size=16, color=color),
                ft.Text(label, size=13, color=T.TEXT_DIM, expand=True),
                ft.Text(str(value), size=14, weight=ft.FontWeight.BOLD, color=T.TEXT),
            ], spacing=8)
        return W.card(
            ft.Column([
                W.section_title("Дополнительно (не считается прогулом)"),
                line("Освобождён от пары", s.passed, T.color("PURPLE_300"), ft.Icons.CHECK_CIRCLE_OUTLINE),
                line("Отменено пар", s.cancelled, T.color("BLUE_GREY_300"), ft.Icons.CANCEL_OUTLINED),
                line("Посещено консультаций", s.cons_present,
                     T.color("GREEN_300"), ft.Icons.SCHOOL_OUTLINED),
            ], spacing=12),
            border=ft.border.all(1, T.BORDER),
        )
