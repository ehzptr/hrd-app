from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import flet as ft

from application.config import AppConfig, AttendanceConfig, PayrollConfig, ScoreConfig, SalesScoreConfig
from services.models import PipelineRequest, PipelineResult, UploadedFile
from services.pipeline import run_pipeline
from ui.view_models import ConfigViewModel, ResultViewModel, UploadViewModel

LOGGER = logging.getLogger(__name__)


class FletDashboardState:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.result: PipelineResult | None = None
        self.error: str | None = None

        self.uploads: dict[str, UploadedFile | None] = {
            "attendance": None,
            "master": None,
            "leave": None,
            "sales": None,
        }
        self.upload_names: dict[str, str] = {
            "attendance": "",
            "master": "",
            "leave": "",
            "sales": "",
        }
        self.file_pickers: dict[str, ft.FilePicker] = {}
        self.upload_labels: dict[str, ft.Text] = {}
        self.config_fields: dict[str, ft.Control] = {}
        self.upload_view_model = UploadViewModel(self.uploads, self.upload_names)
        self.config_view_model = ConfigViewModel(self.config_fields)
        self.result_view_model = ResultViewModel()

        self.status = ft.Text("Menunggu upload data...")
        self.process_button = ft.Button(
            "Proses Data",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.process,
            bgcolor="#0d9488",
            color="white",
            disabled=False,
        )
        self.results_view = ft.Column(expand=True)

    async def handle_file_pick(self, kind: str, files: list[ft.FilePickerFile]) -> None:
        """Store the file returned by the Flet 1.x pick_files service call."""
        if not files:
            return

        selected = files[0]
        try:
            # Flet 1.0 exposes selected bytes (when requested with_data=True)
            # rather than the removed FilePickerFile.read() coroutine.
            content = selected.bytes
            if content is None and selected.path:
                content = Path(selected.path).read_bytes()
            if content is None:
                raise ValueError("File picker tidak mengembalikan isi file.")
        except Exception as exc:  # pragma: no cover - UI fallback
            self.error = f"Gagal membaca {kind}: {exc}"
            self.uploads[kind] = None
            self.upload_names[kind] = ""
            if kind in self.upload_labels:
                self.upload_labels[kind].value = "Gagal dibaca"
                self.upload_labels[kind].color = "#ef4444"
            self.page.update()
            return

        self.uploads[kind] = UploadedFile(content=content, filename=selected.name)
        self.upload_names[kind] = selected.name
        if kind in self.upload_labels:
            self.upload_labels[kind].value = selected.name
            self.upload_labels[kind].color = "#166534"
        self.status.value = f"{kind.title()} siap diproses."
        self.page.update()

    async def process(self, event: ft.ControlEvent) -> None:
        self.process_button.disabled = True
        self.status.value = "Memproses..."
        self.page.update()

        try:
            request = self.build_request()
            self.result = await self.run_pipeline(request)
            self.result_view_model.payload = self.result
            self.status.value = "Selesai"
            self.render_results()
        except Exception as exc:
            LOGGER.exception("Pipeline failed while processing uploaded files")
            self.error = str(exc)
            self.status.value = f"Error: {self.error}"
        finally:
            self.process_button.disabled = False
            self.page.update()

    async def run_pipeline(self, request: PipelineRequest) -> PipelineResult:
        async def run_pipeline_task() -> PipelineResult:
            """Adapt the synchronous business pipeline to Flet's async task API."""
            return await asyncio.to_thread(run_pipeline, request)

        return await asyncio.wrap_future(self.page.run_task(run_pipeline_task))

    def _field_value(self, key: str, default: Any = None) -> Any:
        control = self.config_fields.get(key)
        if control is None:
            return default
        value = getattr(control, "value", default)
        return default if value is None else value

    def build_request(self) -> PipelineRequest:
        attendance = self.uploads.get("attendance")
        if attendance is None:
            raise ValueError("Upload export mesin absensi terlebih dahulu.")

        def parse_date(raw: Any) -> date | None:
            if raw in (None, ""):
                return None
            if isinstance(raw, date):
                return raw
            if isinstance(raw, datetime):
                return raw.date()
            try:
                return date.fromisoformat(str(raw))
            except ValueError:
                return None

        def parse_holidays(raw: str) -> frozenset[date]:
            result: set[date] = set()
            for line in str(raw or "").splitlines():
                item = line.strip()
                if not item:
                    continue
                parsed = parse_date(item[:10])
                if parsed is not None:
                    result.add(parsed)
            return frozenset(result)

        late_mode = str(self._field_value("late_mode", "per_occurrence") or "per_occurrence")
        late_active = bool(self._field_value("use_late_rate", False))
        sales_no_out_active = bool(self._field_value("use_sales_no_out_rate", False))
        early_active = bool(self._field_value("use_early_rate", False))
        absent_active = bool(self._field_value("use_absent_rate", False))

        cfg = AppConfig(
            attendance=AttendanceConfig(
                clock_in=time.fromisoformat(str(self._field_value("clock_in", "08:00"))),
                weekday_clock_out=time.fromisoformat(str(self._field_value("weekday_out", "17:00"))),
                saturday_clock_out=time.fromisoformat(str(self._field_value("saturday_out", "14:00"))),
                grace_minutes=int(self._field_value("grace_minutes", 10) or 0),
                saturday_is_working=bool(self._field_value("saturday_working", True)),
                sunday_is_off=bool(self._field_value("sunday_off", True)),
                start_date=parse_date(self._field_value("start_date")),
                end_date=parse_date(self._field_value("end_date")),
            ),
            score=ScoreConfig(
                excellent_threshold=float(self._field_value("excellent_threshold", 90.0) or 90.0),
                good_threshold=float(self._field_value("good_threshold", 80.0) or 80.0),
                watch_threshold=float(self._field_value("watch_threshold", 70.0) or 70.0),
            ),
            payroll=PayrollConfig(
                late_deduction_mode=late_mode,
                late_deduction_per_occurrence=(
                    float(self._field_value("late_rate_per_occurrence", 0.0) or 0.0)
                    if late_active and late_mode == "per_occurrence"
                    else None
                ),
                late_deduction_per_minute=(
                    float(self._field_value("late_rate_per_minute", 0.0) or 0.0)
                    if late_active and late_mode == "per_minute"
                    else None
                ),
                sales_no_clock_out_deduction=(
                    float(self._field_value("sales_no_out_rate", 0.0) or 0.0)
                    if sales_no_out_active
                    else None
                ),
                early_leave_deduction_per_minute=(
                    float(self._field_value("early_rate", 0.0) or 0.0)
                    if early_active
                    else None
                ),
                absence_deduction_per_day=(
                    float(self._field_value("absent_rate", 0.0) or 0.0)
                    if absent_active
                    else None
                ),
            ),
            sales_score=SalesScoreConfig(
                weight_visit=float(self._field_value("w_visit", 0.15) or 0.15),
                weight_test_drive=float(self._field_value("w_test_drive", 0.15) or 0.15),
                weight_spk=float(self._field_value("w_spk", 0.30) or 0.30),
                weight_delivery=float(self._field_value("w_delivery", 0.25) or 0.25),
                weight_conversion_rate=float(self._field_value("w_conversion", 0.15) or 0.15),
            ),
        )

        return PipelineRequest(
            attendance=attendance,
            master=self.uploads.get("master"),
            leave=self.uploads.get("leave"),
            sales=self.uploads.get("sales"),
            config=cfg,
            holidays=parse_holidays(self._field_value("holidays", "")),
            overtime_hourly_rate=float(self._field_value("overtime_hourly_rate", 0.0) or 0.0),
        )

    def render_results(self) -> None:
        # Kept as a compatibility method for callers of the previous state API.
        from ui.panels.results import render_results

        render_results(self)


# For compatibility with the previous app entrypoints.
__all__ = ["FletDashboardState"]
