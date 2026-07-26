"""Палитра и общие визуальные константы тёмной темы."""
import flet as ft

BG = "#0F0F17"
SURFACE = "#1A1A26"
SURFACE_2 = "#232333"
SURFACE_3 = "#2D2D40"
ACCENT = "#7C8CF8"        # мягкий индиго
TEXT = "#ECECF2"
TEXT_CONS = "#C7C7D6"   # для имени консультации — чуть темнее обычного
TEXT_DIM = "#9A9AB0"
BORDER = "#33334A"

RADIUS = 16

# Размеры шрифтов (единые по всему приложению)
FS_TITLE = 22      # заголовок страницы
FS_VALUE = 28      # крупные числа в карточках
FS_SECTION = 17    # заголовок блока
FS_BODY = 15       # основной текст, названия предметов
FS_LABEL = 14      # подписи, значения в списках
FS_HINT = 13       # пояснения под заголовками
FS_CHIP = 11       # текст в цветных плашках


def color(name: str, fallback: str = TEXT) -> str:
    """Резолв имени атрибута ft.Colors (напр. 'GREEN_400') в значение."""
    return getattr(ft.Colors, name, fallback)
