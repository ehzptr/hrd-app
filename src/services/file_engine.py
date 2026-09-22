from __future__ import annotations

"""Spreadsheet/file input engine used by the HR dashboard.

All user-uploaded tabular files are normalized through this module.

Supported extensions:
    .xlsx
    .xls
    .csv
"""

import io
import warnings
from pathlib import Path
from typing import Any

import polars as pl

SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv")


class UnsupportedFileTypeError(ValueError):
    """Raised when an uploaded file has an unsupported extension."""


def extension_of(filename: str | None) -> str:
    """Return the lowercase file extension."""
    return Path(filename or "").suffix.lower()


def validate_extension(filename: str | None) -> str:
    """Validate and return the uploaded file extension."""
    ext = extension_of(filename)

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Format file '{ext or '(tanpa ekstensi)'}' tidak didukung. "
            f"Gunakan {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    return ext


def _read_excel(file_bytes: bytes, **kwargs: Any) -> Any:
    """Read Excel bytes using Polars + Calamine.

    Polars currently emits a FutureWarning from its internal
    Arrow conversion path with some fastexcel/pyarrow combinations.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)

        return pl.read_excel(
            io.BytesIO(file_bytes),
            engine="calamine",
            **kwargs,
        )


def _normalize_dataframe(value: Any) -> pl.DataFrame:
    """Guarantee that an Excel result is a Polars DataFrame."""
    if isinstance(value, pl.DataFrame):
        return value

    return pl.DataFrame(value)


def read_table(
    file_bytes: bytes,
    filename: str | None,
) -> pl.DataFrame:
    """Read one uploaded tabular file into a Polars DataFrame."""
    ext = validate_extension(filename)

    # CSV
    if ext == ".csv":
        try:
            return pl.read_csv(
                io.BytesIO(file_bytes),
                infer_schema_length=1000,
            )
        except Exception as exc:
            raise ValueError(
                f"Gagal membaca {filename or 'file CSV'}: {exc}"
            ) from exc

    # XLS / XLSX
    try:
        result = _read_excel(file_bytes)

        return _normalize_dataframe(result)

    except Exception as exc:
        raise ValueError(
            f"Gagal membaca {filename or 'file Excel'}: {exc}"
        ) from exc


def read_workbook_sheets(
    file_bytes: bytes,
    filename: str | None,
) -> dict[str, pl.DataFrame]:
    """Read all sheets from an Excel workbook.

    For CSV:
        Returns one sheet named ``Sheet1``.

    For Excel:
        Returns a dictionary containing sheet names and
        Polars DataFrames.
    """
    ext = validate_extension(filename)

    # CSV has no workbook/sheet concept.
    if ext == ".csv":
        return {
            "Sheet1": read_table(
                file_bytes,
                filename,
            )
        }

    # XLS / XLSX
    try:
        sheets: Any = _read_excel(
            file_bytes,
            sheet_id=0,
        )

        # Polars returned a single DataFrame.
        if isinstance(sheets, pl.DataFrame):
            return {
                "Sheet1": sheets
            }

        # Polars returned multiple sheets.
        if isinstance(sheets, dict):
            return {
                str(sheet_name): _normalize_dataframe(sheet_data)
                for sheet_name, sheet_data in sheets.items()
            }

        # Defensive fallback.
        return {
            "Sheet1": _normalize_dataframe(sheets)
        }

    except Exception as exc:
        raise ValueError(
            f"Gagal membaca workbook "
            f"{filename or 'file Excel'}: {exc}"
        ) from exc