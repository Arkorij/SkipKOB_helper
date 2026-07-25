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

        self.current = 0
        self._syncing = False

        # Свайп между страницами — нативный (Flutter TabBarView): контент едет
        # за пальцем в реальном времени, можно остановиться на середине.
        # Обработка жеста на стороне Python дала бы заметную задержку.
        # Полоса вкладок сведена к тонкому индикатору страницы сверху.
        def slim_tab(content):
            # Подпись пустая: полоса вкладок работает как индикатор страницы,
            # названия и так есть в нижней панели. tab_content использовать
            # нельзя — во Flet 0.28 он сбивает соответствие вкладки и её
            # содержимого (вкладка 1 показывала страницу 2).
            return ft.Tab(text=" ", content=content, height=18)

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=250,
            indicator_color=T.ACCENT,
            indicator_thickness=3,
            indicator_padding=ft.padding.symmetric(horizontal=24),
            divider_color="#00000000",
            divider_height=0,
            label_padding=ft.padding.all(0),
            on_change=self._on_tabs,
            expand=True,
            tabs=[
                slim_tab(self.stats_page.build()),
                slim_tab(self.schedule_page.build()),
                slim_tab(self.settings_page.build()),
            ],
        )

        self.body = ft.Container(content=self.tabs, expand=True, bgcolor=T.BG)
        # SafeArea — чтобы контент не заезжал под строку состояния/вырез на телефоне
        self.safe_body = ft.SafeArea(content=self.body, expand=True, bottom=False)

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
        page.add(self.safe_body)
        self._show(0)

    # --- навигация --------------------------------------------------------
    def _on_nav(self, e):
        """Нажатие в нижней панели — переводим Tabs на нужную страницу."""
        if self._syncing:
            return
        self._show(self.nav.selected_index)

    def _on_tabs(self, e):
        """Смена страницы свайпом — подсвечиваем её в нижней панели."""
        if self._syncing:
            return
        index = self.tabs.selected_index or 0
        self.current = index
        self._syncing = True
        self.nav.selected_index = index
        self._syncing = False
        self.pages[index].refresh()
        self.page.update()

    def _show(self, index: int):
        self.current = index
        self._syncing = True
        self.tabs.selected_index = index
        self.nav.selected_index = index
        self._syncing = False
        self.pages[index].refresh()
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
