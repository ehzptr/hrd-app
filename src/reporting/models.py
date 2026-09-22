"""Typed data contracts consumed by report renderers."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import polars as pl

from application.config import AppConfig


@dataclass
class ReportData:
    """All normalized and derived data needed for an Excel report."""

    config: AppConfig
    employee_master: pl.DataFrame
    raw_log: pl.DataFrame
    daily_attendance: pl.DataFrame
    employee_summary: pl.DataFrame
    department_summary: pl.DataFrame
    daily_trend: pl.DataFrame
    anomalies: pl.DataFrame
    rejected: pl.DataFrame
    payroll: pl.DataFrame
    sales_activity: pl.DataFrame
    sales_performance: pl.DataFrame
    insights: list[str]
    report_period_label: str = ""
    generated_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    source_files: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
