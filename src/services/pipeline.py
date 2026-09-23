from __future__ import annotations

import polars as pl

from attendance import analytics as att_analytics
from attendance import engine as att_engine
from attendance.parser import AttendanceValidationError, clean_approved_leave, clean_attendance_data
from services.file_engine import read_table
from application.leave import load_leave_file
from application.employee_master import load_employee_master, merge_master_into_log
from application.payroll import build_payslip_records, calculate_payroll
from application.sales import calculate_sales_performance, clean_sales_activity, combine_attendance_and_sales
from services.models import PipelineRequest, PipelineResult


def _read_upload(file_bytes: bytes, filename: str | None) -> pl.DataFrame:
    return read_table(file_bytes, filename)


def run_pipeline(request: PipelineRequest) -> PipelineResult:
    """Execute the application workflow using validated typed inputs."""
    raw = _read_upload(request.attendance.content, request.attendance.filename)
    clean, rejected, quality = clean_attendance_data(raw)
    if clean.is_empty():
        raise AttendanceValidationError("Tidak ada baris valid setelah proses cleaning.")

    master = pl.DataFrame()
    if request.master:
        master = load_employee_master(
            _read_upload(request.master.content, request.master.filename)
        )

    enriched, unmapped = merge_master_into_log(clean, master)

    leave_result = None
    approved_leave = None
    if request.leave:
        if request.leave.filename.lower().endswith(".csv"):
            approved_leave = clean_approved_leave(
                _read_upload(request.leave.content, request.leave.filename)
            )
        else:
            leave_result = load_leave_file(request.leave.content, request.leave.filename)

    daily = att_engine.build_daily_attendance(
        enriched,
        request.config.attendance,
        request.holidays,
        approved_leave=approved_leave,
        leave_result=leave_result,
    )
    employee_summary = att_analytics.calculate_employee_summary(daily, request.config.score)
    department_summary = att_analytics.calculate_department_summary(daily)
    trend = att_analytics.calculate_daily_trend(daily)
    anomalies = daily.filter(pl.col("Is_Anomali") == 1) if not daily.is_empty() else pl.DataFrame()
    insights = att_analytics.derive_hr_insights(employee_summary, department_summary)
    payroll = calculate_payroll(employee_summary, master, request.config.payroll)

    sales_activity = pl.DataFrame()
    sales_performance = pl.DataFrame()
    combined_view = pl.DataFrame()
    if request.sales:
        sales_raw = _read_upload(request.sales.content, request.sales.filename)
        sales_activity = clean_sales_activity(sales_raw)
        sales_performance = calculate_sales_performance(
            sales_activity, master, request.config.sales_score
        )
        combined_view = combine_attendance_and_sales(employee_summary, sales_performance)

    period_label = ""
    if not daily.is_empty() and "Tanggal" in daily.columns:
        period_label = f"{daily['Tanggal'].min()} s/d {daily['Tanggal'].max()}"

    payslip_records = build_payslip_records(
        payroll,
        employee_summary,
        daily,
        master,
        overtime_hourly_rate=request.overtime_hourly_rate,
        period_label=period_label,
    )

    return PipelineResult(
        config=request.config,
        clean=clean,
        rejected=rejected,
        quality=quality,
        master=master,
        unmapped=unmapped,
        daily=daily,
        employee_summary=employee_summary,
        department_summary=department_summary,
        trend=trend,
        anomalies=anomalies,
        insights=insights,
        payroll=payroll,
        sales_activity=sales_activity,
        sales_performance=sales_performance,
        combined_view=combined_view,
        payslips=payslip_records,
        period_label=period_label,
    )