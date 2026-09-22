from __future__ import annotations

import flet as ft

from ui.state import FletDashboardState


def build_sidebar(state: FletDashboardState) -> ft.Container:
    return ft.Container(
        width=300,
        padding=20,
        bgcolor="#F1F5F9",
        content=ft.Column(
            controls=[
                ft.Text(
                    "HR Dashboard",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color="#0F2B46",
                ),
                ft.Text(
                    "Attendance · Payroll · Sales",
                    size=12,
                    color="#475569",
                ),
                ft.Divider(),
                ft.Text(
                    "Upload Data",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "File upload controls will be added here.",
                    size=12,
                    color="#64748B",
                ),
                ft.Divider(),
                state.status,
                state.process_button,
            ],
            spacing=12,
        ),
    )


def build_page(page: ft.Page) -> None:
    state = FletDashboardState(page)

    page.add(
        ft.Row(
            controls=[
                build_sidebar(state),
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=state.results_view,
                    expand=True,
                    padding=20,
                ),
            ],
            expand=True,
        )
    )