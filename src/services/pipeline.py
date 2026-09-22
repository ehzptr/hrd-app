from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

import polars as pl

from attendance import analytics as att_analytics
from attendance import engine as att_engine
from attendance.parser import AttendanceValidationError, clean_approved_leave, clean_attendance_data
from services.file_engine import read_table
from application.config import AppConfig, AttendanceConfig, PayrollConfig, ScoreConfig, SalesScoreConfig
from application.employee_master import load_employee_master, merge_master_into_log
from application.leave import load_leave_workbook
from application.payroll import build_payslip_records, calculate_payroll
from application.sales import calculate_sales_performance, clean_sales_activity, combine_attendance_and_sales


def _read_upload(file_bytes: bytes, filename: str | None) -> pl.DataFrame:
    return read_table(file_bytes, filename)


def run_attendance_pipeline(
    attendance_bytes: bytes,
    attendance_name: str,
    master_bytes: Optional[bytes],
    leave_bytes: Optional[bytes],
    master_name: str,
    leave_name: str,
    sales_bytes: Optional[bytes],
    sales_name: str,
    clock_in_str: str,
    weekday_out_str: str,
    saturday_out_str: str,
    grace_minutes: int,
    saturday_working: bool,
    sunday_off: bool,
    start_date_val: Optional[date],
    end_date_val: Optional[date],
    holidays_tuple: tuple[str, ...],
    score_thresholds: tuple[float, float, float],
    payroll_args: dict,
    sales_weights: dict,
    overtime_hourly_rate: float,
) -> dict:
    raw = _read_upload(attendance_bytes, attendance_name)
    clean, rejected, quality = clean_attendance_data(raw)
    if clean.is_empty():
        raise AttendanceValidationError("Tidak ada baris valid setelah proses cleaning.")

    master = pl.DataFrame()
    if master_bytes:
        master = load_employee_master(_read_upload(master_bytes, master_name))

    enriched, unmapped = merge_master_into_log(clean, master)

    leave_result = None
    approved_leave = None
    if leave_bytes:
        if leave_name.lower().endswith(".csv"):
            approved_leave = clean_approved_leave(_read_upload(leave_bytes, leave_name))
        else:
            from application.leave import load_leave_file
            leave_result = load_leave_file(leave_bytes, leave_name)

    holidays = set()
    for line in holidays_tuple:
        line = line.strip()
        if line:
            try:
                holidays.add(datetime.strptime(line[:10], "%Y-%m-%d").date())
            except ValueError:
                pass

    cfg = AppConfig(
        attendance=AttendanceConfig(
            clock_in=time.fromisoformat(clock_in_str),
            weekday_clock_out=time.fromisoformat(weekday_out_str),
            saturday_clock_out=time.fromisoformat(saturday_out_str),
            grace_minutes=grace_minutes,
            saturday_is_working=saturday_working,
            sunday_is_off=sunday_off,
            start_date=start_date_val,
            end_date=end_date_val,
        ),
        score=ScoreConfig(
            excellent_threshold=score_thresholds[0],
            good_threshold=score_thresholds[1],
            watch_threshold=score_thresholds[2],
        ),
        payroll=PayrollConfig(**payroll_args),
        sales_score=SalesScoreConfig(**sales_weights),
    )

    daily = att_engine.build_daily_attendance(
        enriched, cfg.attendance, holidays, approved_leave=approved_leave, leave_result=leave_result
    )
    employee_summary = att_analytics.calculate_employee_summary(daily, cfg.score)
    department_summary = att_analytics.calculate_department_summary(daily)
    trend = att_analytics.calculate_daily_trend(daily)
    anomalies = daily.filter(pl.col("Is_Anomali") == 1) if not daily.is_empty() else pl.DataFrame()
    insights = att_analytics.derive_hr_insights(employee_summary, department_summary)
    payroll = calculate_payroll(employee_summary, master, cfg.payroll)

    sales_activity = pl.DataFrame()
    sales_performance = pl.DataFrame()
    combined_view = pl.DataFrame()
    if sales_bytes:
        sales_raw = _read_upload(sales_bytes, sales_name)
        sales_activity = clean_sales_activity(sales_raw)
        sales_performance = calculate_sales_performance(sales_activity, master, cfg.sales_score)
        combined_view = combine_attendance_and_sales(employee_summary, sales_performance)

    period_label = ""
    if not daily.is_empty() and "Tanggal" in daily.columns:
        period_label = f"{daily['Tanggal'].min()} s/d {daily['Tanggal'].max()}"

    payslip_records = build_payslip_records(
        payroll,
        employee_summary,
        daily,
        master,
        overtime_hourly_rate=overtime_hourly_rate,
        period_label=period_label,
    )

    return {
        "cfg": cfg,
        "clean": clean,
        "rejected": rejected,
        "quality": quality,
        "master": master,
        "unmapped": unmapped,
        "daily": daily,
        "employee_summary": employee_summary,
        "department_summary": department_summary,
        "trend": trend,
        "anomalies": anomalies,
        "insights": insights,
        "payroll": payroll,
        "sales_activity": sales_activity,
        "sales_performance": sales_performance,
        "combined_view": combined_view,
        "payslips": payslip_records,
        "period_label": period_label,
    }