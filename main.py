"""SkipKOB_Helper — учёт прогулов в университете. Точка входа (Flet)."""
import time

import flet as ft

from app.storage import load_data, save_data
from app.ui import theme as T
from app.ui.schedule_page import SchedulePage
from app.ui.settings_page import SettingsPage
from app.ui.stats_page import StatsPage

NAV_MS = 110          # переход по нижней панели
SWIPE_MS = 40         # переход свайпом — практически мгновенный
SWIPE_VELOCITY = 350  # ниже этой скорости жест не считается свайпом


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
        self._last_swipe = 0.0

        # Переключение страниц управляется здесь, а не нативным TabBarView:
        # у него физику жеста снаружи не задать, из-за чего доводка тянулась
        # и перехватывала следующее касание. Здесь переход мгновенный, а сам
        # свайп можно выключить (по умолчанию выключен, включается в настройках).
        for p in self.pages:
            p.build()
        self.pages_host = ft.AnimatedSwitcher(
            content=self.stats_page.view,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=NAV_MS,
            reverse_duration=int(NAV_MS * 0.6),
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            expand=True,
        )
        self.body = ft.Container(
            content=ft.GestureDetector(
                content=self.pages_host,
                on_horizontal_drag_end=self._on_swipe,
                expand=True,
            ),
            expand=True,
            bgcolor=T.BG,
        )
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

    def _on_swipe(self, e):
        """Свайп вбок между страницами — если включён в настройках.

        Переход мгновенный: половинчатых состояний нет, поэтому следующее
        касание не перехватывается незавершённой анимацией.
        """
        if not self.data.get("swipe_pages"):
            return
        v = getattr(e, "primary_velocity", None) or 0
        if abs(v) < SWIPE_VELOCITY:
            return
        now = time.time()
        if now - self._last_swipe < 0.25:
            return
        target = self.current + (1 if v < 0 else -1)
        if not 0 <= target < len(self.pages):
            return
        self._last_swipe = now
        self._show(target, duration=SWIPE_MS)

    def _show(self, index: int, duration: int = NAV_MS):
        self.current = index
        self.pages_host.duration = duration
        self.pages_host.reverse_duration = max(1, int(duration * 0.6))
        self.pages_host.content = self.pages[index].view
        self._syncing = True
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
