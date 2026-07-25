"""SkipKOB_Helper — учёт прогулов в университете. Точка входа (Flet)."""
import flet as ft

from app.storage import load_data, save_data
from app.ui import theme as T
from app.ui.schedule_page import SchedulePage
from app.ui.settings_page import SettingsPage
from app.ui.stats_page import StatsPage


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.data = load_data()

        self.stats_page = StatsPage(self)
        self.schedule_page = SchedulePage(self)
        self.settings_page = SettingsPage(self)
        self.pages = [self.stats_page, self.schedule_page, self.settings_page]

        self.body = ft.Container(expand=True, bgcolor=T.BG)

        self.nav = ft.NavigationBar(
            selected_index=0,
            bgcolor=T.SURFACE,
            indicator_color=ft.Colors.with_opacity(0.25, T.ACCENT),
            on_change=self._on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.INSIGHTS_OUTLINED,
                                            selected_icon=ft.Icons.INSIGHTS, label="Статистика"),
                ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                                            selected_icon=ft.Icons.CALENDAR_MONTH, label="Расписание"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED,
                                            selected_icon=ft.Icons.SETTINGS, label="Настройки"),
            ],
        )
        page.navigation_bar = self.nav
        page.add(self.body)
        self._show(0)

    # --- навигация --------------------------------------------------------
    def _on_nav(self, e):
        self._show(self.nav.selected_index)

    def _show(self, index: int):
        page_obj = self.pages[index]
        self.body.content = page_obj.build()
        self.page.update()

    # --- сервисы для страниц ---------------------------------------------
    def persist(self):
        save_data(self.data)

    def replace_data(self, new_data: dict):
        self.data = new_data
        for p in self.pages:
            p.refresh()
        self.page.update()

    def toast(self, message: str):
        if not message or not message.strip():
            return
        self.page.open(ft.SnackBar(
            ft.Text(message, color=T.TEXT),
            bgcolor=T.SURFACE_3,
            duration=2000,
        ))


def main(page: ft.Page):
    page.title = "SkipKOB_Helper"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=T.ACCENT, use_material3=True)
    page.bgcolor = T.BG
    page.padding = 0
    # Приложение вертикальное (как на телефоне) — задаём портретное окно на десктопе.
    page.window.width = 430
    page.window.height = 900
    page.window.min_width = 360
    page.window.min_height = 600
    page.window.center()
    App(page)


if __name__ == "__main__":
    ft.app(target=main)
