"""Small formatting helpers shared by UI panels."""

from __future__ import annotations

from typing import Any


def format_period(value: Any) -> str:
    return f"Periode: {value or 'Tidak tersedia'}"


def format_employee_count(summary: Any) -> str | None:
    if summary is None or getattr(summary, "is_empty", lambda: True)():
        return None
    return f"Karyawan: {summary.height}"

