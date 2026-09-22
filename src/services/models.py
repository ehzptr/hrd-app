from dataclasses import dataclass
from datetime import date
from typing import Any

import polars as pl

from application.config import AppConfig


@dataclass(frozen=True)
class UploadedFile:
    content: bytes
    filename: str


@dataclass(frozen=True)
class PipelineRequest:
    attendance: UploadedFile
    master: UploadedFile | None
    leave: UploadedFile | None
    sales: UploadedFile | None
    config: AppConfig
    holidays: frozenset[date]
    overtime_hourly_rate: float = 0.0


@dataclass
class PipelineResult:
    config: AppConfig
    clean: pl.DataFrame
    rejected: pl.DataFrame
    quality: dict[str, Any]
    master: pl.DataFrame
    unmapped: pl.DataFrame
    daily: pl.DataFrame
    employee_summary: pl.DataFrame
    department_summary: pl.DataFrame
    trend: pl.DataFrame
    anomalies: pl.DataFrame
    insights: list[str]
    payroll: pl.DataFrame
    sales_activity: pl.DataFrame
    sales_performance: pl.DataFrame
    combined_view: pl.DataFrame
    payslips: list[Any]
    period_label: str