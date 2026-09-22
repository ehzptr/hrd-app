from __future__ import annotations

import flet as ft

from ui.components import checkbox, number_field, section_title, text_field
from ui.state import FletDashboardState


def build_config_panel(state: FletDashboardState) -> ft.Column:
    schedule = ft.Column(
        controls=[
            section_title("2", "Konfigurasi"),
            ft.Text("Jadwal Kerja", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
            text_field(state, "clock_in", "Jam masuk", "08:00"),
            text_field(state, "weekday_out", "Pulang Senin–Jumat", "17:00"),
            text_field(state, "saturday_out", "Pulang Sabtu", "14:00"),
            number_field(state, "grace_minutes", "Toleransi terlambat (menit)", 10, max_value=120),
            checkbox(state, "saturday_working", "Sabtu hari kerja", True),
            checkbox(state, "sunday_off", "Minggu libur", True),
            ft.Text("Periode", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
            text_field(state, "start_date", "Tanggal mulai (YYYY-MM-DD)"),
            text_field(state, "end_date", "Tanggal akhir (YYYY-MM-DD)"),
            text_field(state, "holidays", "Hari libur, satu tanggal per baris", multiline=True),
        ],
        spacing=8,
    )
    scoring = ft.Column(
        controls=[
            ft.Text("Scoring & Payroll", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
            number_field(state, "excellent_threshold", "EXCELLENT", 90, max_value=100),
            number_field(state, "good_threshold", "GOOD", 80, max_value=100),
            number_field(state, "watch_threshold", "WATCH", 70, max_value=100),
            checkbox(state, "use_late_rate", "Aktifkan potongan telat", False),
            text_field(state, "late_mode", "Mode: per_occurrence / per_minute", "per_occurrence"),
            number_field(state, "late_rate_per_occurrence", "Tarif telat / kejadian", 0, max_value=1_000_000, step=1000),
            number_field(state, "late_rate_per_minute", "Tarif telat / menit", 0, max_value=1_000_000, step=1000),
            checkbox(state, "use_sales_no_out_rate", "Potongan lupa pulang Sales", False),
            number_field(state, "sales_no_out_rate", "Tarif lupa pulang", 0, max_value=1_000_000, step=1000),
            checkbox(state, "use_early_rate", "Potongan pulang cepat", False),
            number_field(state, "early_rate", "Tarif pulang cepat / menit", 0, max_value=1_000_000, step=1000),
            checkbox(state, "use_absent_rate", "Potongan mangkir", False),
            number_field(state, "absent_rate", "Tarif mangkir / hari", 0, max_value=1_000_000, step=1000),
        ],
        spacing=8,
    )
    sales = ft.Column(
        controls=[
            ft.Text("Sales Weights", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
            number_field(state, "w_visit", "Visit", 0.15, max_value=1, step=0.01),
            number_field(state, "w_test_drive", "Test Drive", 0.15, max_value=1, step=0.01),
            number_field(state, "w_spk", "SPK", 0.30, max_value=1, step=0.01),
            number_field(state, "w_delivery", "Delivery", 0.25, max_value=1, step=0.01),
            number_field(state, "w_conversion", "Conversion", 0.15, max_value=1, step=0.01),
            ft.Text("Payslip", size=11, weight=ft.FontWeight.BOLD, color="#334155"),
            text_field(state, "company_name", "Nama perusahaan", "PT. Dealership Maju Bersama"),
            text_field(state, "company_address", "Alamat perusahaan", "Surabaya, Indonesia"),
            number_field(state, "overtime_hourly_rate", "Tarif lembur / jam", 0, max_value=10_000_000, step=5000),
        ],
        spacing=8,
    )
    return ft.Column([schedule, ft.Divider(), scoring, ft.Divider(), sales], spacing=12)
