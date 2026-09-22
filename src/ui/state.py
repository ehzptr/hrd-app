from __future__ import annotations

import flet as ft

from services.models import PipelineRequest, PipelineResult
from services.pipeline import run_attendance_pipeline


class FletDashboardState:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.result: PipelineResult | None = None
        self.error: str | None = None

        self.status = ft.Text("Menunggu upload data...")

        self.process_button = ft.Button(
            content="Proses Data",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.process,
            style=ft.ButtonStyle(
                bgcolor="#0d9488",
                color="#ffffff",
            ),
        )

        self.results_view = ft.Column(expand=True)

    async def process(self, event: ft.ControlEvent) -> None:
        self.process_button.disabled = True
        self.status.value = "Memproses..."
        self.page.update()

        try:
            request = self.build_request()
            self.result = await self.run_pipeline(request)
            self.status.value = "Selesai"
            self.render_results()
        except Exception as exc:
            self.error = str(exc)
            self.status.value = f"Error: {self.error}"
        finally:
            self.process_button.disabled = False
            self.page.update()

    async def run_pipeline(self, request: PipelineRequest) -> PipelineResult:
        return await self.page.run_task(run_attendance_pipeline, request)

    def build_request(self) -> PipelineRequest:
        raise NotImplementedError

    def render_results(self) -> None:
        self.results_view.controls.clear()

        if self.result is not None:
            self.results_view.controls.append(
                ft.Text(
                    f"Periode: {self.result.period_label}",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                )
            )

        self.page.update()