from __future__ import annotations

import flet as ft

from ui.components import BORDER, NAVY, SLATE_50, SLATE_500, section_title
from ui.panels import build_config_panel, build_upload_panel
from ui.state import FletDashboardState


def build_sidebar(state: FletDashboardState) -> ft.Container:
    content = ft.Column(
        controls=[
            ft.Text("DATA INPUT", size=10, weight=ft.FontWeight.BOLD, color=SLATE_500),
            build_upload_panel(state),
            ft.Divider(),
            ft.Text("WORK SCHEDULE", size=10, weight=ft.FontWeight.BOLD, color=SLATE_500),
            build_config_panel(state),
            ft.Divider(),
            section_title("3", "Proses Data"),
            state.process_button,
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                bgcolor="#ECFDF5",
                border_radius=6,
                content=ft.Row(
                    controls=[
                        ft.Container(width=7, height=7, bgcolor="#16A34A", border_radius=4),
                        state.status,
                    ],
                    spacing=8,
                ),
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )
    return ft.Container(
        width=320,
        padding=20,
        bgcolor=SLATE_50,
        border=ft.Border(right=ft.BorderSide(1, BORDER)),
        content=content,
    )
