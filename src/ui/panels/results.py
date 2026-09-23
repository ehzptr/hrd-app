"""Results dashboard controls.

The pipeline deliberately returns Polars frames rather than UI objects.  This
module is the presentation boundary: it keeps the existing state contract and
turns each result into a compact, readable dashboard (including useful empty
states).
"""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import flet as ft
import polars as pl

from ui.components import BORDER, NAVY, SLATE_500, TEAL, card
from ui.formatters import format_period
from reporting.payslip import generate_bulk_payslip_excel, generate_bulk_payslip_pdf
from services.models import PipelineResult
from ui.state import FletDashboardState

MUTED = SLATE_500
GREEN = "#15803D"
AMBER = "#B45309"
RED = "#B91C1C"


def build_results_panel(state: FletDashboardState) -> ft.Column:
    """Create the stable host control used by :mod:`ui.page`."""
    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=18)


def _frame(result: PipelineResult, key: str) -> pl.DataFrame:
    value = getattr(result, key, None)
    return value if isinstance(value, pl.DataFrame) else pl.DataFrame()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return default if math.isnan(number) else number
    except (TypeError, ValueError):
        return default


def _integer(value: Any) -> int:
    return int(round(_number(value)))


def _fmt_number(value: Any) -> str:
    number = _number(value)
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.1f}"


def _fmt_percent(value: Any) -> str:
    return f"{_number(value):.1f}%"


def _fmt_currency(value: Any) -> str:
    return f"Rp {_number(value):,.0f}"


def _display(value: Any, column: str = "") -> str:
    if value is None:
        return "—"
    if column == "Revenue" or "revenue" in column.lower():
        return _fmt_currency(value)
    if "%" in column or "Rate" in column or "Score" in column:
        return _fmt_percent(value)
    if isinstance(value, float):
        return _fmt_number(value)
    return str(value)


def _title(label: str, subtitle: str | None = None) -> ft.Column:
    controls: list[ft.Control] = [
        ft.Text(label, size=16, weight=ft.FontWeight.BOLD, color=NAVY)
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=12, color=MUTED))
    return ft.Column(controls=controls, spacing=3)


def _empty(message: str = "Belum ada data untuk ditampilkan.") -> ft.Container:
    return card(
        ft.Row(
            controls=[
                ft.Text(ft.Icons.INFO_OUTLINE, size=20, color=MUTED),
                ft.Text(message, size=13, color=MUTED, expand=True),
            ],
            spacing=10,
        )
    )


def _kpi(label: str, value: str, detail: str = "", accent: str = TEAL) -> ft.Container:
    controls: list[ft.Control] = [
        ft.Text(label.upper(), size=10, weight=ft.FontWeight.BOLD, color=MUTED),
        ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=NAVY),
    ]
    if detail:
        controls.append(ft.Text(detail, size=11, color=MUTED))
    return ft.Container(
        content=ft.Column(controls=controls, spacing=4),
        padding=14,
        border=ft.Border(
            left=ft.BorderSide(4, accent),
            top=ft.BorderSide(1, BORDER),
            right=ft.BorderSide(1, BORDER),
            bottom=ft.BorderSide(1, BORDER),
        ),
        border_radius=8,
        bgcolor="white",
        col={"xs": 12, "sm": 6, "md": 3},
    )


def _table(df: pl.DataFrame, columns: list[str], limit: int = 8) -> ft.Container:
    available = [column for column in columns if column in df.columns]
    if df.is_empty() or not available:
        return _empty()

    rows = df.select(available).head(limit).to_dicts()

    def handle_row_selection_change(e: ft.ControlEvent) -> None:
        e.control.selected = not e.control.selected
        e.control.update()

    def sort_column(e: ft.DataColumnSortEvent) -> None:
        column = available[e.column_index]
        rows.sort(
            key=lambda row: (
                row.get(column) is None,
                row.get(column) if row.get(column) is not None else "",
            ),
            reverse=not e.ascending,
        )
        table.rows = get_data_rows(rows)
        table.sort_column_index = e.column_index
        table.sort_ascending = e.ascending
        table.update()

    def get_data_columns() -> list[ft.DataColumn]:
        return [
            ft.DataColumn(
                label=ft.Text(
                    column.replace("_", " "),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                ),
                on_sort=sort_column,
                numeric=index > 0,
            )
            for index, column in enumerate(available)
        ]

    def get_data_rows(items: list[dict[str, Any]]) -> list[ft.DataRow]:
        return [
            ft.DataRow(
                on_select_change=handle_row_selection_change,
                cells=[
                    ft.DataCell(ft.Text(_display(row.get(column), column), size=12))
                    for column in available
                ],
            )
            for row in items
        ]

    table = ft.DataTable(
        expand=True,
        show_checkbox_column=True,
        columns=get_data_columns(),
        rows=get_data_rows(rows),
        column_spacing=18,
        heading_row_color="#F1F5F9",
        heading_row_height=42,
        data_row_min_height=42,
        data_row_max_height=42,
        border=ft.Border.all(1, "#E2E8F0"),
        horizontal_lines=ft.BorderSide(1, "#E2E8F0"),
    )

    return ft.Container(
        height=310,
        expand=True,
        content=table,
    )


def _section(
    label: str, content: ft.Control, subtitle: str | None = None
) -> ft.Container:
    return card(ft.Column(controls=[_title(label, subtitle), content], spacing=12))


def _save_bytes_button(
    state: FletDashboardState,
    label: str,
    filename: str,
    content_factory,
    *,
    disabled: bool = False,
) -> ft.Button:
    picker = ft.FilePicker()
    state.page.services.append(picker)

    async def save(_: ft.ControlEvent) -> None:
        try:
            content = content_factory()
            path = await picker.save_file(
                file_name=filename,
                allowed_extensions=[Path(filename).suffix[1:]],
                file_type=ft.FilePickerFileType.CUSTOM,
                src_bytes=content,
            )
            if path:
                state.status.value = f"File tersimpan: {Path(path).name}"
        except Exception as exc:
            state.status.value = f"Gagal mengekspor {filename}: {exc}"
            state.page.update()
            return
        state.page.update()

    return ft.Button(label, icon=ft.Icons.DOWNLOAD, on_click=save, disabled=disabled)


def _dashboard(state: FletDashboardState) -> list[ft.Control]:
    result = state.result
    if result is None:
        return [
            _empty("Belum ada hasil. Upload data attendance lalu klik Proses Data.")
        ]
    summary = _frame(result, "employee_summary")
    departments = _frame(result, "department_summary")
    anomalies = _frame(result, "anomalies")
    payroll = _frame(result, "payroll")
    sales = _frame(result, "sales_performance")
    payslips = result.payslips
    payslip_rows = [asdict(slip) for slip in payslips if is_dataclass(slip)]
    payslip_frame = pl.DataFrame(payslip_rows) if payslip_rows else pl.DataFrame()
    insights = result.insights

    employees = summary.height
    avg_score = (
        summary["Attendance_Score"].mean()
        if "Attendance_Score" in summary.columns and employees
        else 100.0
    )
    attendance = (
        summary["Attendance_Rate_%"].mean()
        if "Attendance_Rate_%" in summary.columns and employees
        else 100.0
    )
    late = (
        summary["Terlambat"].sum()
        if "Terlambat" in summary.columns and employees
        else 0
    )
    absent = (
        summary["Mangkir"].sum() if "Mangkir" in summary.columns and employees else 0
    )
    revenue = (
        sales["Revenue"].sum()
        if "Revenue" in sales.columns and not sales.is_empty()
        else 0
    )

    controls: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(
                            "Ringkasan HR",
                            size=27,
                            weight=ft.FontWeight.BOLD,
                            color=NAVY,
                        ),
                        ft.Text(
                            f"{format_period(result.period_label)}  ·  Gunakan tabel di bawah untuk tindak lanjut.",
                            size=13,
                            color=MUTED,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        ft.ResponsiveRow(
            controls=[
                _kpi("Karyawan", _fmt_number(employees), "employee summary"),
                _kpi("Attendance score", _fmt_percent(avg_score), "rata-rata", GREEN),
                _kpi("Kehadiran", _fmt_percent(attendance), "attendance rate", TEAL),
                _kpi(
                    "Keterlambatan",
                    _fmt_number(late),
                    f"{_fmt_number(absent)} mangkir",
                    AMBER,
                ),
            ],
            spacing=10,
            run_spacing=10,
        ),
    ]

    insight_controls = (
        ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("•", size=18, color=TEAL),
                        ft.Text(str(text), size=13, expand=True),
                    ],
                    spacing=8,
                )
                for text in insights
            ],
            spacing=8,
        )
        if insights
        else _empty("Insight akan muncul setelah data berhasil diproses.")
    )
    controls.append(_section("Insights & perhatian", insight_controls))

    controls.extend(
        [
            _section(
                "Ringkasan attendance",
                _table(
                    summary,
                    [
                        "No.",
                        "Name",
                        "Department",
                        "Attendance_Rate_%",
                        "Terlambat",
                        "Mangkir",
                        "Attendance_Score",
                    ],
                ),
                "Karyawan dengan skor terendah ditampilkan lebih dulu.",
            ),
            _section(
                "Ringkasan departemen",
                _table(
                    departments,
                    [
                        "Department",
                        "Employee",
                        "Present",
                        "Late",
                        "Absent",
                        "Attendance_Rate_%",
                        "Attendance_Score_%",
                    ],
                ),
            ),
            _section(
                "Anomali attendance",
                _table(
                    anomalies,
                    [
                        "Tanggal",
                        "No.",
                        "Name",
                        "Department",
                        "Status_Masuk",
                        "Status_Pulang",
                        "Is_Anomali",
                    ],
                ),
                "Watchlist hari yang membutuhkan tindak lanjut.",
            ),
            _section(
                "Payroll",
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                _save_bytes_button(
                                    state,
                                    label="Export slip PDF",
                                    filename="Slip_Gaji.pdf",
                                    content_factory=lambda: generate_bulk_payslip_pdf(
                                        payslips,
                                        {
                                            "name": str(
                                                state._field_value(
                                                    "company_name",
                                                    "PT. Dealership Maju Bersama",
                                                )
                                            ),
                                            "address": str(
                                                state._field_value(
                                                    "company_address",
                                                    "Surabaya, Indonesia",
                                                )
                                            ),
                                        },
                                    ),
                                    disabled=not payslips,
                                ),
                                _save_bytes_button(
                                    state,
                                    label="Export slip Excel",
                                    filename="Slip_Gaji.xlsx",
                                    content_factory=lambda: generate_bulk_payslip_excel(
                                        payslips,
                                        {
                                            "name": str(
                                                state._field_value(
                                                    "company_name",
                                                    "PT. Dealership Maju Bersama",
                                                )
                                            ),
                                            "address": str(
                                                state._field_value(
                                                    "company_address",
                                                    "Surabaya, Indonesia",
                                                )
                                            ),
                                        },
                                    ),
                                    disabled=not payslips,
                                ),
                            ]
                        ),
                        _table(
                            payroll,
                            [
                                "No.",
                                "Name",
                                "Department",
                                "Monthly_Salary",
                                "Total_Potongan",
                                "Estimasi_Take_Home",
                                "Total_Menit_Telat",
                            ],
                        ),
                        _table(
                            payslip_frame,
                            [
                                "employee_id",
                                "name",
                                "department",
                                "period_label",
                                "total_pendapatan",
                                "total_potongan",
                                "take_home_pay",
                            ],
                        ),
                    ],
                ),
                "Perhitungan payroll berasal dari pipeline. Tabel kedua adalah ringkasan slip yang siap diekspor.",
            ),
            _section(
                "Sales performance",
                _table(
                    sales,
                    [
                        "No.",
                        "Name",
                        "Department",
                        "SPK",
                        "Delivery",
                        "Revenue",
                        "Conversion_Rate_%",
                        "Performance_Score",
                    ],
                ),
                f"Total revenue: {_fmt_currency(revenue)}"
                if not sales.is_empty()
                else "Belum ada file sales.",
            ),
        ]
    )
    return controls


def render_results(state: FletDashboardState) -> None:
    """Render the latest result while preserving the existing state/page API."""
    state.results_view.controls.clear()
    if state.result is None:
        state.results_view.controls.append(
            _empty("Belum ada hasil. Upload data attendance lalu klik Proses Data.")
        )
    else:
        state.results_view.controls.extend(_dashboard(state))
    state.page.update()
