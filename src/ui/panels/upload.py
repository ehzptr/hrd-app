from __future__ import annotations

import flet as ft

from application.employee_master import build_employee_master_template
from application.leave import build_leave_template
from application.sales import build_sales_activity_template
from ui.components import (
    SLATE_700,
    section_title,
    template_button,
    upload_control,
)
from ui.state import FletDashboardState


def build_upload_panel(state: FletDashboardState) -> ft.Column:
    return ft.Column(
        controls=[
            section_title("1", "Upload Data"),
            upload_control(state, "attendance", "Export Mesin Absensi", required=True),
            ft.Text("Data Pendukung", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
            upload_control(state, "master", "Employee Master"),
            upload_control(state, "leave", "Cuti / Izin / Lembur"),
            upload_control(state, "sales", "Sales Activity"),
            ft.Text("Template Download", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
            template_button("Template Cuti", ft.Icons.DOWNLOAD, build_leave_template, state),
            template_button("Template Employee", ft.Icons.DOWNLOAD, build_employee_master_template, state),
            template_button("Template Sales", ft.Icons.DOWNLOAD, build_sales_activity_template, state),
        ],
        spacing=8,
    )
