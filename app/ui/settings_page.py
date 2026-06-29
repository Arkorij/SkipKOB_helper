"""Страница 3 — настройки: год, каникулы, редактор расписания, экспорт/импорт, сброс."""
from __future__ import annotations

import threading
import time

import flet as ft

from .. import calendar_logic as cal
from .. import models
from .. import report as report_mod
from .. import storage
from ..calendar_logic import DAYS, DAY_NAMES_RU
from . import theme as T
from . import widgets as W


class SettingsPage:
    def __init__(self, app):
        self.app = app
        self.sched_fields: dict[str, dict[str, ft.TextField]] = {"odd": {}, "even": {}}

        # файловые пикеры
        self.fp_export_sched = ft.FilePicker(on_result=self._on_export_schedule)
        self.fp_import_sched = ft.FilePicker(on_result=self._on_import_schedule)
        self.fp_export_report = ft.FilePicker(on_result=self._on_export_report)
        for fp in (self.fp_export_sched, self.fp_import_sched, self.fp_export_report):
            app.page.overlay.append(fp)

        self.year_field = ft.TextField(
            width=120, text_size=14, border_color=T.BORDER, keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.breaks_col = ft.Column(spacing=8)
        self.view = ft.ListView(expand=True, padding=ft.padding.all(16), spacing=18)

    # --- построение -------------------------------------------------------
    def build(self):
        self.refresh()
        return self.view

    def refresh(self):
        data = self.app.data
        self.year_field.value = str(data["academic_year_start"])
        self._rebuild_breaks()
        self.view.controls = [
            self._year_section(),
            self._breaks_section(),
            self._schedule_section(),
            self._io_section(),
            self._danger_section(),
        ]
        self._safe_update()

    def _safe_update(self):
        try:
            self.view.update()
        except Exception:
            pass

    # --- год --------------------------------------------------------------
    def _year_section(self):
        def apply(e):
            try:
                y = int(self.year_field.value)
            except (TypeError, ValueError):
                self.app.toast("Год должен быть числом")
                return
            self.app.data["academic_year_start"] = y
            self.app.persist()
            self.app.toast(f"Учебный год: 1 сентября {y}")
        return W.card(
            ft.Column([
                W.section_title("Учебный год"),
                ft.Text("Год, в котором 1 сентября. По нему строится весь календарь (недели 1–40).",
                        size=11, color=T.TEXT_DIM),
                ft.Row([self.year_field, W.ghost_button("Применить", apply)],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            ], spacing=10),
            border=ft.border.all(1, T.BORDER),
        )

    # --- каникулы ---------------------------------------------------------
    def _breaks_section(self):
        return W.card(
            ft.Column([
                W.section_title("Каникулы"),
                ft.Text("На каникулах нумерация недель не идёт. Формат дат: ГГГГ-ММ-ДД.",
                        size=11, color=T.TEXT_DIM),
                self.breaks_col,
                W.ghost_button("Добавить период", self._add_break, icon=ft.Icons.ADD),
            ], spacing=10),
            border=ft.border.all(1, T.BORDER),
        )

    def _rebuild_breaks(self):
        rows = []
        breaks = self.app.data["breaks"]
        for i, b in enumerate(breaks):
            start = ft.TextField(
                value=b.get("start", ""), width=140, text_size=13, dense=True,
                border_color=T.BORDER, label="с",
                on_blur=self._make_break_handler(i, "start"),
            )
            end = ft.TextField(
                value=b.get("end", ""), width=140, text_size=13, dense=True,
                border_color=T.BORDER, label="по",
                on_blur=self._make_break_handler(i, "end"),
            )
            rows.append(ft.Row([
                start, end,
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=T.color("RED_300"),
                              on_click=lambda e, idx=i: self._del_break(idx)),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER))
        if not breaks:
            rows.append(ft.Text("Каникулы не заданы", size=12, color=T.TEXT_DIM, italic=True))
        self.breaks_col.controls = rows

    def _make_break_handler(self, idx, field):
        def handler(e):
            if idx < len(self.app.data["breaks"]):
                self.app.data["breaks"][idx][field] = e.control.value.strip()
                self.app.persist()
        return handler

    def _add_break(self, e):
        self.app.data["breaks"].append({"start": "", "end": ""})
        self.app.persist()
        self._rebuild_breaks()
        self._safe_update()

    def _del_break(self, idx):
        if idx < len(self.app.data["breaks"]):
            self.app.data["breaks"].pop(idx)
            self.app.persist()
            self._rebuild_breaks()
            self._safe_update()

    # --- редактор базового расписания -------------------------------------
    def _schedule_section(self):
        self.sched_fields = {"odd": {}, "even": {}}

        def make_col(parity, visible):
            fields = []
            for d in DAYS:
                pairs = [models.coerce_pair(x) for x in self.app.data["base_schedule"][parity][d]]
                tf = ft.TextField(
                    value="\n".join(models.format_pair(p) for p in pairs),
                    multiline=True, min_lines=1, max_lines=8, text_size=13,
                    border_color=T.BORDER, label=DAY_NAMES_RU[d],
                )
                self.sched_fields[parity][d] = tf
                fields.append(tf)
            return ft.Column(fields, spacing=8, visible=visible)

        odd_col = make_col("odd", True)
        even_col = make_col("even", False)

        btn_odd = ft.TextButton("Нечётная")
        btn_even = ft.TextButton("Чётная")

        def style(parity):
            btn_odd.style = ft.ButtonStyle(
                bgcolor=T.ACCENT if parity == "odd" else T.SURFACE_2,
                color="#10101A" if parity == "odd" else T.TEXT_DIM,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=18, vertical=10),
            )
            btn_even.style = ft.ButtonStyle(
                bgcolor=T.ACCENT if parity == "even" else T.SURFACE_2,
                color="#10101A" if parity == "even" else T.TEXT_DIM,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=18, vertical=10),
            )

        def select(parity):
            odd_col.visible = parity == "odd"
            even_col.visible = parity == "even"
            style(parity)
            self._safe_update()

        btn_odd.on_click = lambda e: select("odd")
        btn_even.on_click = lambda e: select("even")
        style("odd")

        def save(e):
            for parity in ("odd", "even"):
                for d in DAYS:
                    val = self.sched_fields[parity][d].value
                    pairs = [models.parse_pair(ln) for ln in val.split("\n") if ln.strip()]
                    self.app.data["base_schedule"][parity][d] = pairs
            self.app.persist()
            self.app.toast("Базовое расписание сохранено")

        return W.card(
            ft.Column([
                W.section_title("Базовое расписание"),
                ft.Text("Пары по одной в строке. Префиксы: # — консультация, * — практика, ~ — лаб (без знака — лекция).",
                        size=11, color=T.TEXT_DIM),
                ft.Row([btn_odd, btn_even], spacing=8),
                odd_col,
                even_col,
                W.primary_button("Сохранить расписание", save, icon=ft.Icons.SAVE_OUTLINED),
            ], spacing=10),
            border=ft.border.all(1, T.BORDER),
        )

    # --- экспорт / импорт / отчёт -----------------------------------------
    def _io_section(self):
        return W.card(
            ft.Column([
                W.section_title("Файлы"),
                ft.Row([
                    W.ghost_button("Экспорт расписания", lambda e: self.fp_export_sched.save_file(
                        dialog_title="Сохранить расписание",
                        file_name="skipkob_schedule.json",
                        allowed_extensions=["json"],
                    ), icon=ft.Icons.UPLOAD_FILE),
                    W.ghost_button("Импорт расписания", lambda e: self.fp_import_sched.pick_files(
                        dialog_title="Выбрать файл расписания (.conf или .json)",
                        allowed_extensions=["conf", "json"], allow_multiple=False,
                    ), icon=ft.Icons.DOWNLOAD),
                ], spacing=10, wrap=True),
                ft.Divider(height=8, color=T.BORDER),
                W.primary_button("Экспорт отчёта о прогулах (Markdown)",
                                 lambda e: self.fp_export_report.save_file(
                                     dialog_title="Сохранить отчёт",
                                     file_name="skipkob_report.md",
                                     allowed_extensions=["md"],
                                 ), icon=ft.Icons.DESCRIPTION_OUTLINED),
            ], spacing=12),
            border=ft.border.all(1, T.BORDER),
        )

    def _on_export_schedule(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        path = e.path if e.path.lower().endswith(".json") else e.path + ".json"
        try:
            storage.export_schedule(self.app.data, path)
            self.app.toast("Расписание экспортировано")
        except OSError as ex:
            self.app.toast(f"Ошибка: {ex}")

    def _on_import_schedule(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        path = e.files[0].path

        def do_import():
            try:
                new_data = storage.import_schedule(self.app.data, path)
                self.app.replace_data(new_data)
                self.app.toast("Расписание импортировано")
            except (OSError, ValueError) as ex:
                self.app.toast(f"Ошибка импорта: {ex}")

        self._confirm(
            "Импорт расписания",
            "Основа (год, каникулы, расписание) будет перезаписана. Отметки прогулов сохранятся. Продолжить?",
            do_import,
        )

    def _on_export_report(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        path = e.path if e.path.lower().endswith(".md") else e.path + ".md"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(report_mod.build_markdown(self.app.data))
            self.app.toast("Отчёт сохранён")
        except OSError as ex:
            self.app.toast(f"Ошибка: {ex}")

    # --- опасная зона: полный сброс ---------------------------------------
    def _danger_section(self):
        return W.card(
            ft.Column([
                W.section_title("Опасная зона"),
                ft.Text("Полный сброс удалит расписание, каникулы и все отметки прогулов.",
                        size=11, color=T.TEXT_DIM),
                ft.OutlinedButton(
                    "Полный сброс",
                    icon=ft.Icons.DELETE_FOREVER,
                    on_click=self._reset_flow,
                    style=ft.ButtonStyle(
                        color=T.color("RED_400"),
                        side=ft.BorderSide(1, T.color("RED_400")),
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.padding.symmetric(horizontal=16, vertical=14),
                    ),
                ),
            ], spacing=10),
            border=ft.border.all(1, T.color("RED_900")),
        )

    def _reset_flow(self, e):
        page = self.app.page
        confirm_btn = ft.ElevatedButton(
            "Подождите… 3",
            disabled=True,
            style=ft.ButtonStyle(bgcolor=T.color("RED_400"), color="#10101A",
                                 shape=ft.RoundedRectangleBorder(radius=12)),
        )

        def do_reset(ev):
            new_data = storage.reset_data()
            self.app.replace_data(new_data)
            page.close(dlg)
            self.app.toast("Все данные сброшены")

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=T.SURFACE,
            icon=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=T.color("RED_400"), size=40),
            title=ft.Text("Полный сброс", color=T.TEXT),
            content=ft.Text(
                "Это действие необратимо. Все отметки, расписание и каникулы будут удалены.\n"
                "Кнопка станет активной через 3 секунды.",
                color=T.TEXT_DIM, size=13,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda ev: page.close(dlg)),
                confirm_btn,
            ],
        )
        page.open(dlg)

        def countdown():
            for s in range(3, 0, -1):
                confirm_btn.text = f"Подождите… {s}"
                try:
                    confirm_btn.update()
                except Exception:
                    return
                time.sleep(1)
            confirm_btn.text = "Сбросить всё"
            confirm_btn.disabled = False
            confirm_btn.on_click = do_reset
            try:
                confirm_btn.update()
            except Exception:
                pass

        threading.Thread(target=countdown, daemon=True).start()

    # --- общий диалог подтверждения ---------------------------------------
    def _confirm(self, title: str, message: str, on_yes):
        page = self.app.page

        def yes(e):
            page.close(dlg)
            on_yes()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=T.SURFACE,
            title=ft.Text(title, color=T.TEXT),
            content=ft.Text(message, color=T.TEXT_DIM, size=13),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.close(dlg)),
                W.primary_button("Продолжить", yes),
            ],
        )
        page.open(dlg)
