import flet as ft

from ui.page import build_page


def main(page: ft.Page) -> None:
    page.title = "HR Attendance, Payroll & Sales Dashboard"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    build_page(page)


if __name__ == "__main__":
    ft.run(main)