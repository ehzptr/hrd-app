from __future__ import annotations

import flet as ft

from ui.components import BORDER, NAVY, SLATE_500, TEAL
from ui.sidebar import build_sidebar
from ui.panels import build_results_panel
from ui.state import FletDashboardState

SLATE_100 = "#F1F5F9"


def build_page(page: ft.Page) -> None:
    page.title = "HR Attendance, Payroll & Sales Dashboard"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = SLATE_100
    state = FletDashboardState(page)
    state.results_view = build_results_panel(state)
    page.add(
        ft.Column(
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=24, vertical=14),
                    bgcolor="white",
                    border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                width=38,
                                height=38,
                                bgcolor=TEAL,
                                border_radius=8,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Text("HR", color="white", weight=ft.FontWeight.BOLD),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("HR Dashboard", size=19, weight=ft.FontWeight.BOLD, color=NAVY),
                                    ft.Text(
                                        "Attendance · Payroll · Sales Performance",
                                        size=11,
                                        color=SLATE_500,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                                border=ft.Border.all(1, BORDER),
                                border_radius=20,
                                content=ft.Row(
                                    controls=[
                                        ft.Container(width=7, height=7, bgcolor=TEAL, border_radius=4),
                                        ft.Text("Siap memproses data", size=11, color=SLATE_500),
                                    ],
                                    spacing=7,
                                ),
                            ),
                        ],
                        spacing=12,
                    ),
                ),
                ft.Row(
                    controls=[
                        build_sidebar(state),
                        ft.Container(content=state.results_view, expand=True, padding=24),
                    ],
                    expand=True,
                    spacing=0,
                ),
            ],
            expand=True,
        )
    )


__all__ = ["build_page"]
