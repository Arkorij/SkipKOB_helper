"""Переиспользуемые виджеты интерфейса."""
import flet as ft

from . import theme as T


def card(content, padding=16, bgcolor=T.SURFACE, **kwargs):
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor,
        border_radius=T.RADIUS,
        **kwargs,
    )


def stat_card(title: str, value, accent: str, icon=None, expand=True):
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(icon, color=accent, size=20) if icon else ft.Container(),
                        ft.Text(title, size=T.FS_LABEL, color=T.TEXT_DIM),
                    ],
                    spacing=6,
                ),
                ft.Text(str(value), size=T.FS_VALUE, weight=ft.FontWeight.BOLD, color=T.TEXT),
            ],
            spacing=4,
        ),
        expand=expand,
        border=ft.border.all(1, T.BORDER),
    )


def section_title(text: str):
    return ft.Text(text, size=T.FS_SECTION, weight=ft.FontWeight.BOLD, color=T.TEXT_DIM)


def primary_button(text, on_click, icon=None):
    return ft.ElevatedButton(
        text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=T.ACCENT,
            color="#10101A",
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
        ),
    )


def ghost_button(text, on_click, icon=None, color=None):
    color = color or T.TEXT
    return ft.OutlinedButton(
        text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=color,
            side=ft.BorderSide(1, T.BORDER),
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
        ),
    )
