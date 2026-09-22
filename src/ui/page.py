from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import flet as ft

from application.employee_master import build_employee_master_template
from application.leave import build_leave_template
from application.sales import build_sales_activity_template
from ui.state import FletDashboardState


NAVY = "#0F2B46"
TEAL = "#0D9488"
SLATE_50 = "#F8FAFC"
SLATE_100 = "#F1F5F9"
SLATE_500 = "#64748B"
SLATE_700 = "#334155"
BORDER = "#E2E8F0"


def _section_title(number: str, label: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(number, color="white", weight=ft.FontWeight.BOLD, size=12),
                width=26,
                height=26,
                bgcolor=TEAL,
                border_radius=13,
                alignment=ft.Alignment(0, 0),
            ),
            ft.Text(label.upper(), size=12, weight=ft.FontWeight.BOLD, color=NAVY),
        ],
        spacing=10,
    )


def _card(content: ft.Control) -> ft.Container:
    return ft.Container(content=content, padding=12, border=ft.Border.all(1, BORDER), border_radius=8, bgcolor="white")


def _text_field(state: FletDashboardState, key: str, label: str, value: str = "", *, width: int | None = None, multiline: bool = False, input_type: ft.KeyboardType | None = None) -> ft.TextField:
    field = ft.TextField(
        label=label,
        value=value,
        border=ft.InputBorder.OUTLINE,
        border_radius=6,
        text_size=13,
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=5 if multiline else 1,
        keyboard_type=input_type,
        width=width,
    )
    state.config_fields[key] = field
    return field


def _number_field(state: FletDashboardState, key: str, label: str, value: float | int, *, min_value: float = 0, max_value: float = 10_000_000, step: float = 1) -> ft.TextField:
    field = _text_field(state, key, label, str(value), input_type=ft.KeyboardType.NUMBER)
    field.helper_text = f"{min_value:g} – {max_value:g}"
    field.data = {"min": min_value, "max": max_value, "step": step}
    return field


def _checkbox(state: FletDashboardState, key: str, label: str, value: bool) -> ft.Checkbox:
    # ``dense`` is not supported by the installed Flet Checkbox API.
    control = ft.Checkbox(label=label, value=value)
    state.config_fields[key] = control
    return control


def _upload_control(state: FletDashboardState, key: str, label: str, required: bool = False) -> ft.Container:
    filename = ft.Text("Belum dipilih", size=11, color=SLATE_500, expand=True, overflow=ft.TextOverflow.ELLIPSIS)
    state.upload_labels[key] = filename
    picker = ft.FilePicker(on_result=lambda event: state.handle_file_pick(key, event))
    state.file_pickers[key] = picker
    state.page.overlay.append(picker)

    async def choose(_: ft.ControlEvent) -> None:
        await picker.pick_files(allow_multiple=False, allowed_extensions=["xlsx", "xls", "csv"], dialog_title=label)

    button = ft.Button("Pilih File", icon=ft.Icons.UPLOAD_FILE, on_click=choose)
    button.style = ft.ButtonStyle(bgcolor=TEAL if required else "white", color="white" if required else NAVY, side=ft.BorderSide(1, TEAL if required else BORDER))
    return _card(ft.Column(controls=[ft.Row(controls=[ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=SLATE_700, expand=True), ft.Text("WAJIB" if required else "OPSIONAL", size=9, color=TEAL if required else SLATE_500)]), ft.Row(controls=[filename, button], spacing=8)], spacing=8))


def _template_button(label: str, icon: str, data_factory: Callable[[], bytes], state: FletDashboardState) -> ft.Button:
    picker = ft.FilePicker()
    state.page.overlay.append(picker)

    async def save(_: ft.ControlEvent) -> None:
        path = await picker.save_file(file_name=f"{label}.xlsx", allowed_extensions=["xlsx"])
        if path:
            Path(path).write_bytes(data_factory())
            state.status.value = f"Template tersimpan: {Path(path).name}"
            state.page.update()

    return ft.Button(label, icon=icon, on_click=save, style=ft.ButtonStyle(color=NAVY))


def build_sidebar(state: FletDashboardState) -> ft.Container:
    upload_section = ft.Column(controls=[
        _section_title("1", "Upload Data"),
        _upload_control(state, "attendance", "Export Mesin Absensi", required=True),
        ft.Text("Data Pendukung", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _upload_control(state, "master", "Employee Master"),
        _upload_control(state, "leave", "Cuti / Izin / Lembur"),
        _upload_control(state, "sales", "Sales Activity"),
        ft.Text("Template Download", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _template_button("Template Cuti", ft.Icons.DOWNLOAD, build_leave_template, state),
        _template_button("Template Employee", ft.Icons.DOWNLOAD, build_employee_master_template, state),
        _template_button("Template Sales", ft.Icons.DOWNLOAD, build_sales_activity_template, state),
    ], spacing=8)

    schedule = ft.Column(controls=[
        _section_title("2", "Konfigurasi"),
        ft.Text("Jadwal Kerja", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _text_field(state, "clock_in", "Jam masuk", "08:00"),
        _text_field(state, "weekday_out", "Pulang Senin–Jumat", "17:00"),
        _text_field(state, "saturday_out", "Pulang Sabtu", "14:00"),
        _number_field(state, "grace_minutes", "Toleransi terlambat (menit)", 10, max_value=120),
        _checkbox(state, "saturday_working", "Sabtu hari kerja", True),
        _checkbox(state, "sunday_off", "Minggu libur", True),
        ft.Text("Periode", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _text_field(state, "start_date", "Tanggal mulai (YYYY-MM-DD)"),
        _text_field(state, "end_date", "Tanggal akhir (YYYY-MM-DD)"),
        _text_field(state, "holidays", "Hari libur, satu tanggal per baris", multiline=True),
    ], spacing=8)

    scoring = ft.Column(controls=[
        ft.Text("Scoring & Payroll", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _number_field(state, "excellent_threshold", "EXCELLENT", 90, max_value=100),
        _number_field(state, "good_threshold", "GOOD", 80, max_value=100),
        _number_field(state, "watch_threshold", "WATCH", 70, max_value=100),
        _checkbox(state, "use_late_rate", "Aktifkan potongan telat", False),
        _text_field(state, "late_mode", "Mode: per_occurrence / per_minute", "per_occurrence"),
        _number_field(state, "late_rate_per_occurrence", "Tarif telat / kejadian", 0, max_value=1_000_000, step=1000),
        _number_field(state, "late_rate_per_minute", "Tarif telat / menit", 0, max_value=1_000_000, step=1000),
        _checkbox(state, "use_sales_no_out_rate", "Potongan lupa pulang Sales", False),
        _number_field(state, "sales_no_out_rate", "Tarif lupa pulang", 0, max_value=1_000_000, step=1000),
        _checkbox(state, "use_early_rate", "Potongan pulang cepat", False),
        _number_field(state, "early_rate", "Tarif pulang cepat / menit", 0, max_value=1_000_000, step=1000),
        _checkbox(state, "use_absent_rate", "Potongan mangkir", False),
        _number_field(state, "absent_rate", "Tarif mangkir / hari", 0, max_value=1_000_000, step=1000),
    ], spacing=8)

    sales = ft.Column(controls=[
        ft.Text("Sales Weights", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _number_field(state, "w_visit", "Visit", 0.15, max_value=1, step=0.01),
        _number_field(state, "w_test_drive", "Test Drive", 0.15, max_value=1, step=0.01),
        _number_field(state, "w_spk", "SPK", 0.30, max_value=1, step=0.01),
        _number_field(state, "w_delivery", "Delivery", 0.25, max_value=1, step=0.01),
        _number_field(state, "w_conversion", "Conversion", 0.15, max_value=1, step=0.01),
        ft.Text("Payslip", size=11, weight=ft.FontWeight.BOLD, color=SLATE_700),
        _text_field(state, "company_name", "Nama perusahaan", "PT. Dealership Maju Bersama"),
        _text_field(state, "company_address", "Alamat perusahaan", "Surabaya, Indonesia"),
        _number_field(state, "overtime_hourly_rate", "Tarif lembur / jam", 0, max_value=10_000_000, step=5000),
    ], spacing=8)

    return ft.Container(width=340, padding=16, bgcolor=SLATE_50, border=ft.Border(right=ft.BorderSide(1, BORDER)), content=ft.Column(controls=[ft.Text("HR Dashboard", size=24, weight=ft.FontWeight.BOLD, color=NAVY), ft.Text("Attendance · Payroll · Sales Performance", size=12, color=SLATE_500), ft.Divider(), upload_section, ft.Divider(), schedule, ft.Divider(), scoring, ft.Divider(), sales, ft.Divider(), _section_title("3", "Proses Data"), state.process_button, state.status], spacing=12, scroll=ft.ScrollMode.AUTO))


def build_page(page: ft.Page) -> None:
    page.title = "HR Attendance, Payroll & Sales Dashboard"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = SLATE_100
    state = FletDashboardState(page)
    page.add(ft.Row(controls=[build_sidebar(state), ft.Container(content=state.results_view, expand=True, padding=24)], expand=True, spacing=0))
