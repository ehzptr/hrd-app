from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import flet as ft

from ui.state import FletDashboardState


NAVY = "#0F2B46"
TEAL = "#0D9488"
SLATE_50 = "#F8FAFC"
SLATE_500 = "#64748B"
SLATE_700 = "#334155"
BORDER = "#E2E8F0"


def section_title(number: str, label: str) -> ft.Row:
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


def card(content: ft.Control) -> ft.Container:
    return ft.Container(
        content=content,
        padding=12,
        border=ft.Border.all(1, BORDER),
        border_radius=8,
        bgcolor="white",
    )


def text_field(
    state: FletDashboardState,
    key: str,
    label: str,
    value: str = "",
    *,
    width: int | None = None,
    multiline: bool = False,
    input_type: ft.KeyboardType | None = None,
) -> ft.TextField:
    field = ft.TextField(
        label=label,
        value=value,
        border=ft.OutlineInputBorder(border_radius=ft.BorderRadius.all(6)),
        text_size=13,
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=5 if multiline else 1,
        keyboard_type=input_type,
        width=width,
    )
    state.config_fields[key] = field
    return field


def number_field(
    state: FletDashboardState,
    key: str,
    label: str,
    value: float | int,
    *,
    min_value: float = 0,
    max_value: float = 10_000_000,
    step: float = 1,
) -> ft.TextField:
    field = text_field(state, key, label, str(value), input_type=ft.KeyboardType.NUMBER)
    field.helper_text = f"{min_value:g} – {max_value:g}"
    field.data = {"min": min_value, "max": max_value, "step": step}
    return field


def checkbox(state: FletDashboardState, key: str, label: str, value: bool) -> ft.Checkbox:
    control = ft.Checkbox(label=label, value=value)
    state.config_fields[key] = control
    return control


def upload_control(
    state: FletDashboardState, key: str, label: str, required: bool = False
) -> ft.Container:
    filename = ft.Text(
        "Belum dipilih", size=11, color=SLATE_500, expand=True, overflow=ft.TextOverflow.ELLIPSIS
    )
    state.upload_labels[key] = filename
    picker = ft.FilePicker()
    state.file_pickers[key] = picker
    state.page.services.append(picker)

    async def choose(_: ft.ControlEvent) -> None:
        files = await picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xlsx", "xls", "csv"],
            dialog_title=label,
            with_data=True,
        )
        await state.handle_file_pick(key, files)

    button = ft.Button("Pilih File", icon=ft.Icons.UPLOAD_FILE, on_click=choose)
    button.style = ft.ButtonStyle(
        bgcolor=TEAL if required else "white",
        color="white" if required else NAVY,
        side=ft.BorderSide(1, TEAL if required else BORDER),
    )
    return card(
        ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=SLATE_700, expand=True),
                        ft.Text(
                            "WAJIB" if required else "OPSIONAL",
                            size=9,
                            color=TEAL if required else SLATE_500,
                        ),
                    ]
                ),
                ft.Row(controls=[filename, button], spacing=8),
            ],
            spacing=8,
        )
    )


def template_button(
    label: str, icon: str, data_factory: Callable[[], bytes], state: FletDashboardState
) -> ft.Button:
    picker = ft.FilePicker()
    state.page.services.append(picker)

    async def save(_: ft.ControlEvent) -> None:
        path = await picker.save_file(file_name=f"{label}.xlsx", allowed_extensions=["xlsx"])
        if path:
            Path(path).write_bytes(data_factory())
            state.status.value = f"Template tersimpan: {Path(path).name}"
            state.page.update()

    return ft.Button(label, icon=icon, on_click=save, style=ft.ButtonStyle(color=NAVY))
