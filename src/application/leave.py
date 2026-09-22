"""
hrdash.leave
============
Modul terintegrasi untuk menangani template Excel dan pemrosesan data Cuti,
Lembur & Kegiatan Bersama (Lembur Bersama / Libur Bersama).
"""

from __future__ import annotations

import datetime as dt
import io
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
import polars as pl

from reporting.excel_utils import style_guide_sheet, style_template_sheet
from services.file_engine import read_workbook_sheets, extension_of, validate_extension

NAVY = "1F4E78"
WHITE = "FFFFFF"
LIGHT_GRAY = "F2F2F2"

# --------------------------------------------------------------------------
# Constant & Enum Definitions
# --------------------------------------------------------------------------

SHEET_CUTI_IZIN = "Cuti_Izin"
SHEET_LEMBUR_KARYAWAN = "Lembur_Karyawan"
SHEET_KEGIATAN_BERSAMA = "Kegiatan_Bersama"


class ApprovalStatus(str, Enum):
    APPROVED = "Approved"
    PENDING = "Pending"
    REJECTED = "Rejected"

    @classmethod
    def parse(cls, raw: object) -> Optional["ApprovalStatus"]:
        if raw is None:
            return None
        text = str(raw).strip().lower()
        for member in cls:
            if member.value.lower() == text:
                return member
        if text in ("ya", "yes", "setuju", "disetujui", "ok", "1", "true"):
            return cls.APPROVED
        if text in ("tidak", "no", "ditolak", "reject"):
            return cls.REJECTED
        return None


class GroupEventType(str, Enum):
    LIBUR_BERSAMA = "Libur Bersama"
    LEMBUR_BERSAMA = "Lembur Bersama"

    @classmethod
    def parse(cls, raw: object) -> Optional["GroupEventType"]:
        if raw is None:
            return None
        text = str(raw).strip().lower()
        if "lembur" in text or "event" in text or "kegiatan" in text or "pameran" in text:
            return cls.LEMBUR_BERSAMA
        if "libur" in text or "cuti" in text:
            return cls.LIBUR_BERSAMA
        for member in cls:
            if member.value.lower() == text:
                return member
        return None


# --------------------------------------------------------------------------
# Dataclasses
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class LeaveRecord:
    employee_id: str
    name: Optional[str]
    start_date: dt.date
    end_date: dt.date
    leave_type: str
    status: ApprovalStatus
    note: Optional[str]
    source_row: int

    def dates(self) -> list[dt.date]:
        return _date_range(self.start_date, self.end_date)


@dataclass(frozen=True)
class OvertimeRecord:
    employee_id: str
    name: Optional[str]
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    duration_hours: float
    status: ApprovalStatus
    note: Optional[str]
    source_row: int


@dataclass(frozen=True)
class GroupEvent:
    start_date: dt.date
    end_date: dt.date
    name: str
    event_type: GroupEventType
    duration_hours: float = 8.0
    scope: str = "Semua Karyawan"
    note: Optional[str] = None
    source_row: int = 0

    def dates(self) -> list[dt.date]:
        return _date_range(self.start_date, self.end_date)


@dataclass(frozen=True)
class RejectedRow:
    sheet: str
    row: int
    reason: str
    raw: dict


@dataclass
class LeaveLoadResult:
    leaves: list[LeaveRecord] = field(default_factory=list)
    overtimes: list[OvertimeRecord] = field(default_factory=list)
    group_events: list[GroupEvent] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)


# --------------------------------------------------------------------------
# Template Generator
# --------------------------------------------------------------------------

def build_leave_template() -> bytes:
    """Membuat template Excel 3 sheet profesional:
    1. Cuti_Izin (per karyawan)
    2. Lembur_Karyawan (per karyawan)
    3. Kegiatan_Bersama (global: Lembur Bersama / Libur Bersama)
    4. Petunjuk
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default blank sheet

    def _style_sheet(ws, widths: dict[str, int]):
        style_template_sheet(ws, widths)

    # 1. Cuti_Izin
    ws_cuti = wb.create_sheet(title=SHEET_CUTI_IZIN)
    ws_cuti.append(["No.", "Nama", "Tanggal Mulai", "Tanggal Selesai", "Jumlah Hari", "Leave Type", "Status Approval", "Keterangan"])
    ws_cuti.append(["EMP001", "Budi Santoso", "2026-09-10", "2026-09-11", 2, "Cuti Tahunan", "Approved", "Cuti tahunan keperluan keluarga"])
    ws_cuti.append(["EMP002", "Sari Wijaya", "2026-09-18", "2026-09-18", 1, "Izin Sakit", "Approved", "Surat dokter terlampir"])
    _style_sheet(ws_cuti, {"A": 14, "B": 22, "C": 16, "D": 16, "E": 14, "F": 18, "G": 16, "H": 30})

    dv_status = DataValidation(type="list", formula1='"Approved,Pending,Rejected"', allow_blank=True)
    ws_cuti.add_data_validation(dv_status)
    dv_status.add("G2:G500")

    # 2. Lembur_Karyawan
    ws_lembur = wb.create_sheet(title=SHEET_LEMBUR_KARYAWAN)
    ws_lembur.append(["No.", "Nama", "Tanggal", "Jam Mulai Lembur", "Jam Selesai Lembur", "Durasi (Jam)", "Status Approval", "Keterangan / Alasan Lembur"])
    ws_lembur.append(["EMP001", "Budi Santoso", "2026-09-12", "17:00", "20:00", 3.0, "Approved", "Closing rekap akhir pekan"])
    ws_lembur.append(["EMP002", "Sari Wijaya", "2026-09-21", "17:00", "19:30", 2.5, "Approved", "Rekap payroll bulanan"])
    _style_sheet(ws_lembur, {"A": 14, "B": 22, "C": 16, "D": 18, "E": 18, "F": 14, "G": 16, "H": 35})

    dv_lembur_status = DataValidation(type="list", formula1='"Approved,Pending,Rejected"', allow_blank=True)
    ws_lembur.add_data_validation(dv_lembur_status)
    dv_lembur_status.add("G2:G500")

    # 3. Kegiatan_Bersama
    ws_kegiatan = wb.create_sheet(title=SHEET_KEGIATAN_BERSAMA)
    ws_kegiatan.append(["Tanggal Mulai", "Tanggal Selesai", "Nama Kegiatan / Event", "Jenis Pencatatan", "Durasi Lembur (Jam)", "Cakupan Karyawan", "Keterangan"])
    ws_kegiatan.append(["2026-09-15", "2026-09-15", "Pameran Launching Mall", "Lembur Bersama", 8.0, "Semua Karyawan", "Event pameran mobil di mall, karyawan tidak scan di kantor"])
    ws_kegiatan.append(["2026-12-24", "2026-12-24", "Cuti Bersama Nasional", "Libur Bersama", 0.0, "Semua Karyawan", "Hari libur / cuti bersama perusahaan"])
    _style_sheet(ws_kegiatan, {"A": 16, "B": 16, "C": 28, "D": 20, "E": 20, "F": 20, "G": 40})

    dv_jenis = DataValidation(type="list", formula1='"Lembur Bersama,Libur Bersama"', allow_blank=True)
    ws_kegiatan.add_data_validation(dv_jenis)
    dv_jenis.add("D2:D500")

    # 4. Petunjuk
    guide = wb.create_sheet("Petunjuk")
    guide.append(["PANDUAN TEMPLATE CUTI, LEMBUR & KEGIATAN BERSAMA"])
    guide_rows = [
        ["1. Sheet Cuti_Izin", "Digunakan untuk perizinan dan cuti individual per karyawan berdasarkan No. (Employee ID). Status 'Approved' akan membebaskan karyawan dari status Mangkir dan potongan mangkir."],
        ["2. Sheet Lembur_Karyawan", "Digunakan untuk pencatatan lembur individual di luar jam kantor normal per karyawan berdasarkan No. (Employee ID). Durasi lembur otomatis diakumulasikan."],
        ["3. Sheet Kegiatan_Bersama", "Berlaku global untuk seluruh karyawan (atau divisi terkait) tanpa memerlukan scan absensi fingerprint di kantor."],
        ["   - Jenis 'Lembur Bersama'", "Contoh: Pameran launching di Mall / pameran otomotif. Seluruh karyawan yang bertugas TIDAK dianggap mangkir meskipun tidak ada scan di kantor, dan jam lembur akan ditambahkan."],
        ["   - Jenis 'Libur Bersama'", "Contoh: Cuti bersama perusahaan atau libur khusus. Seluruh karyawan otomatis berstatus Libur Bersama dan tidak dianggap mangkir."],
        ["Format Tanggal & Jam", "Gunakan format YYYY-MM-DD untuk tanggal (contoh: 2026-09-15) dan HH:MM untuk jam (contoh: 17:00)."],
    ]
    for row in guide_rows:
        guide.append(row)

    style_guide_sheet(guide)
    guide.column_dimensions["A"].width = 28
    guide.column_dimensions["B"].width = 85

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------
# File Parser / Loader
# --------------------------------------------------------------------------

def load_leave_file(file_bytes: bytes, filename: str | None) -> LeaveLoadResult:
    """Load leave/overtime/group-event data from .xlsx, .xls or .csv.

    XLS is read with the Calamine engine and converted in-memory to an
    openpyxl workbook so the existing multi-sheet leave parser can be reused.
    CSV is treated as a single Cuti/Izin table.
    """
    ext = validate_extension(filename)

    if ext == ".xlsx":
        return load_leave_workbook(io.BytesIO(file_bytes))

    sheets = read_workbook_sheets(file_bytes, filename)
    if ext == ".csv":
        df = sheets.get("Sheet1", pl.DataFrame())
        return _load_leave_csv_dataframe(df)

    # .xls: reconstruct a temporary XLSX workbook from all sheets.
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name, df in sheets.items():
        safe_name = str(sheet_name)[:31] or "Sheet1"
        ws = wb.create_sheet(safe_name)
        if df.columns:
            ws.append(list(df.columns))
            for row in df.rows():
                ws.append(list(row))
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return load_leave_workbook(buffer)


def _load_leave_csv_dataframe(df: pl.DataFrame) -> LeaveLoadResult:
    """CSV leave input uses the same approved-leave normalization path."""
    result = LeaveLoadResult()
    if df.is_empty():
        return result

    # Convert the normalized CSV rows to LeaveRecord directly.
    cols = {str(c).strip().lower(): c for c in df.columns}
    def col(*names: str):
        for name in names:
            if name.lower() in cols:
                return cols[name.lower()]
        return None

    id_col = col("No.", "Employee ID", "ID", "NIK")
    name_col = col("Nama", "Name")
    start_col = col("Tanggal Mulai", "Mulai", "Start Date", "Tanggal")
    end_col = col("Tanggal Selesai", "Selesai", "End Date")
    type_col = col("Leave Type", "Type", "Jenis")
    status_col = col("Status Approval", "Status")
    note_col = col("Keterangan", "Note", "Catatan")

    if not id_col or not start_col:
        result.rejected.append(RejectedRow("CSV", 1, "CSV Cuti/Izin harus memiliki No. dan Tanggal Mulai/Tanggal.", {}))
        return result

    for idx, row in enumerate(df.rows(), start=2):
        data = dict(zip(df.columns, row))
        emp_id = data.get(id_col)
        if emp_id is None or str(emp_id).strip() == "":
            result.rejected.append(RejectedRow("CSV", idx, "No. (Employee ID) kosong", data))
            continue
        start_date = _to_date(data.get(start_col))
        end_date = _to_date(data.get(end_col)) if end_col else start_date
        if start_date is None:
            result.rejected.append(RejectedRow("CSV", idx, "Tanggal Mulai tidak valid", data))
            continue
        status = ApprovalStatus.parse(data.get(status_col)) if status_col else ApprovalStatus.APPROVED
        status = status or ApprovalStatus.APPROVED
        if status is not ApprovalStatus.APPROVED:
            result.rejected.append(RejectedRow("CSV", idx, f"Status '{status.value}' (Bukan Approved)", data))
            continue
        result.leaves.append(
            LeaveRecord(
                employee_id=str(emp_id).strip(),
                name=str(data.get(name_col)).strip() if name_col and data.get(name_col) is not None else None,
                start_date=start_date,
                end_date=end_date or start_date,
                leave_type=str(data.get(type_col)).strip() if type_col and data.get(type_col) is not None else "Cuti/Izin",
                status=status,
                note=str(data.get(note_col)).strip() if note_col and data.get(note_col) is not None else None,
                source_row=idx,
            )
        )
    return result


def _find_sheet(wb: openpyxl.Workbook, aliases: list[str]) -> Optional[str]:
    cleaned = {s.lower().replace(" ", "").replace("_", "").replace("/", ""): s for s in wb.sheetnames}
    for alias in aliases:
        key = alias.lower().replace(" ", "").replace("_", "").replace("/", "")
        if key in cleaned:
            return cleaned[key]
    for alias in aliases:
        key = alias.lower().replace(" ", "").replace("_", "").replace("/", "")
        for k, orig in cleaned.items():
            if key in k or k in key:
                return orig
    return None


def load_leave_workbook(path: str | Path | object) -> LeaveLoadResult:
    """Membaca file Excel Cuti, Lembur & Kegiatan Bersama dengan toleransi variasi nama sheet."""
    if hasattr(path, "seek"):
        path.seek(0)

    result = LeaveLoadResult()
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as exc:
        result.rejected.append(RejectedRow("Workbook", 1, f"File tidak dapat dibaca sebagai Excel: {exc}", {}))
        return result

    cuti_sheet = _find_sheet(wb, ["Cuti_Izin", "Cuti/Izin", "Cuti", "Data Cuti", "Izin", "Leave"])
    lembur_sheet = _find_sheet(wb, ["Lembur_Karyawan", "Lembur Karyawan", "Lembur", "Overtime"])
    kegiatan_sheet = _find_sheet(
        wb,
        [
            "Kegiatan_Bersama",
            "Kegiatan/Event/Lembur Bersama/Cuti Bersama",
            "Kegiatan Bersama",
            "Event",
            "Kegiatan",
            "Lembur Bersama",
            "Cuti Bersama",
        ],
    )

    # Fallback: if none matched by alias, check if active sheet is single-sheet cuti/leave table
    if not cuti_sheet and not lembur_sheet and not kegiatan_sheet and wb.sheetnames:
        first_ws = wb.active
        first_row = [str(c).lower() for c in next(first_ws.iter_rows(min_row=1, max_row=1, values_only=True), []) if c]
        if any("cuti" in c or "leave" in c or "tanggal" in c or "date" in c for c in first_row):
            cuti_sheet = first_ws.title

    if cuti_sheet and cuti_sheet in wb.sheetnames:
        _load_cuti_izin(wb[cuti_sheet], result)
    if lembur_sheet and lembur_sheet in wb.sheetnames:
        _load_lembur_karyawan(wb[lembur_sheet], result)
    if kegiatan_sheet and kegiatan_sheet in wb.sheetnames:
        _load_kegiatan_bersama(wb[kegiatan_sheet], result)

    return result


def _load_cuti_izin(ws, result: LeaveLoadResult) -> None:
    headers = [str(c).strip() if c else "" for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), [])]
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if _row_is_blank(row):
            continue
        emp_id, name, start_raw, end_raw, _, leave_type, status_raw, note = _pad(row, 8)
        raw = dict(zip(headers or ["No.", "Nama", "Mulai", "Selesai", "Jumlah", "Type", "Status", "Ket"], row))

        if _is_blank(emp_id):
            result.rejected.append(RejectedRow(ws.title, row_idx, "No. (Employee ID) kosong", raw))
            continue

        start_date = _to_date(start_raw)
        end_date = _to_date(end_raw) or start_date
        if start_date is None:
            result.rejected.append(RejectedRow(ws.title, row_idx, "Tanggal Mulai tidak valid", raw))
            continue

        status = ApprovalStatus.parse(status_raw) or ApprovalStatus.APPROVED
        if status is not ApprovalStatus.APPROVED:
            result.rejected.append(RejectedRow(ws.title, row_idx, f"Status '{status.value}' (Bukan Approved)", raw))
            continue

        result.leaves.append(
            LeaveRecord(
                employee_id=str(emp_id).strip(),
                name=str(name).strip() if not _is_blank(name) else None,
                start_date=start_date,
                end_date=end_date,
                leave_type=str(leave_type).strip() if not _is_blank(leave_type) else "Cuti/Izin",
                status=status,
                note=str(note).strip() if not _is_blank(note) else None,
                source_row=row_idx,
            )
        )


def _load_lembur_karyawan(ws, result: LeaveLoadResult) -> None:
    headers = [str(c).strip() if c else "" for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), [])]
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if _row_is_blank(row):
            continue
        emp_id, name, date_raw, start_raw, end_raw, dur_raw, status_raw, note = _pad(row, 8)
        raw = dict(zip(headers or ["No.", "Nama", "Tanggal", "Mulai", "Selesai", "Durasi", "Status", "Ket"], row))

        if _is_blank(emp_id):
            result.rejected.append(RejectedRow(ws.title, row_idx, "No. (Employee ID) kosong", raw))
            continue

        the_date = _to_date(date_raw)
        start_time = _to_time(start_raw)
        end_time = _to_time(end_raw)
        if the_date is None:
            result.rejected.append(RejectedRow(ws.title, row_idx, "Tanggal tidak valid", raw))
            continue

        # Parse duration
        duration = 0.0
        if dur_raw is not None and not _is_blank(dur_raw):
            try:
                duration = float(dur_raw)
            except (ValueError, TypeError):
                duration = 0.0

        if duration <= 0.0 and start_time and end_time:
            duration = _hours_between(start_time, end_time)

        if duration <= 0.0:
            duration = 1.0  # fallback 1 jam jika terisi

        status = ApprovalStatus.parse(status_raw) or ApprovalStatus.APPROVED
        if status is not ApprovalStatus.APPROVED:
            result.rejected.append(RejectedRow(ws.title, row_idx, f"Status '{status.value}' (Bukan Approved)", raw))
            continue

        result.overtimes.append(
            OvertimeRecord(
                employee_id=str(emp_id).strip(),
                name=str(name).strip() if not _is_blank(name) else None,
                date=the_date,
                start_time=start_time or dt.time(17, 0),
                end_time=end_time or dt.time(20, 0),
                duration_hours=round(duration, 2),
                status=status,
                note=str(note).strip() if not _is_blank(note) else None,
                source_row=row_idx,
            )
        )


def _load_kegiatan_bersama(ws, result: LeaveLoadResult) -> None:
    headers = [str(c).strip() if c else "" for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), [])]
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if _row_is_blank(row):
            continue
        start_raw, end_raw, name, jenis_raw, dur_raw, scope, note = _pad(row, 7)
        raw = dict(zip(headers or ["Mulai", "Selesai", "Event", "Jenis", "Durasi", "Cakupan", "Ket"], row))

        start_date = _to_date(start_raw)
        end_date = _to_date(end_raw) or start_date
        event_type = GroupEventType.parse(jenis_raw)

        if start_date is None or event_type is None or _is_blank(name):
            result.rejected.append(RejectedRow(ws.title, row_idx, "Data kegiatan tidak lengkap/valid", raw))
            continue

        duration_hours = 8.0 if event_type == GroupEventType.LEMBUR_BERSAMA else 0.0
        if dur_raw is not None and not _is_blank(dur_raw):
            try:
                duration_hours = float(dur_raw)
            except (ValueError, TypeError):
                pass

        result.group_events.append(
            GroupEvent(
                start_date=start_date,
                end_date=end_date,
                name=str(name).strip(),
                event_type=event_type,
                duration_hours=round(duration_hours, 2),
                scope=str(scope).strip() if not _is_blank(scope) else "Semua Karyawan",
                note=str(note).strip() if not _is_blank(note) else None,
                source_row=row_idx,
            )
        )


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Enrichment Engine Integrator
# --------------------------------------------------------------------------

def _ensure_polars(df: object) -> pl.DataFrame:
    if isinstance(df, pl.DataFrame):
        return df
    if hasattr(df, "to_dict"):
        return pl.from_pandas(df)
    if isinstance(df, list):
        return pl.DataFrame(df)
    return pl.DataFrame(df)


def _to_time(val: object) -> Optional[dt.time]:
    if val is None:
        return None
    if isinstance(val, dt.datetime):
        return val.time()
    if isinstance(val, dt.time):
        return val
    # Penanganan angka float desimal jam dari Excel (0.0 - 1.0)
    if isinstance(val, (float, int)) and 0 <= val <= 1:
        total_seconds = int(val * 86400)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return dt.time(hours % 24, minutes)
    s = str(val).strip().replace(".", ":")
    if not s or s.lower() in ("nan", "none", "nat", "<null>"):
        return None
    parts = s.split(":")
    if len(parts) >= 2:
        try:
            return dt.time(int(parts[0]), int(parts[1]))
        except ValueError:
            return None
    return None


def apply_leave_kegiatan(daily_input: pl.DataFrame | object, leave_result: LeaveLoadResult | None) -> pl.DataFrame:
    """Integrate Cuti, Lembur, and Kegiatan Bersama into the daily attendance table.

    Vectorized with Polars expressions (joins + ``when``/``then``) instead of
    iterating the table row-by-row, so this matches the rest of the engine
    (see ``attendance/engine.py``) and doesn't risk dtype drift from
    reconstructing a schema-less ``pl.DataFrame`` out of Python dicts.

    Priority per employee-day (mirrors the original row-by-row behavior
    exactly -- each case is mutually exclusive, first match wins):
        1. Libur Bersama (group holiday)
        2. Approved individual leave (Cuti)
        3. Lembur Bersama (group overtime event)
    Individual overtime (Lembur_Karyawan, sheet-based) is independent of the
    three cases above and always applied when present; a matching Lembur
    Bersama event adds its hours on top of it.

    Known limitation, preserved as-is from the original implementation:
    group events are matched by date only. ``GroupEvent.scope`` is parsed
    when the workbook is loaded but is not yet applied here to restrict an
    event to specific departments/employees -- every event currently
    applies to all employees on its date(s).
    """
    daily = _ensure_polars(daily_input)
    if daily.is_empty() or leave_result is None:
        return daily

    id_col = "No." if "No." in daily.columns else "Employee_ID"
    date_col = "Tanggal" if "Tanggal" in daily.columns else "Date"

    # These columns are only ever produced by this function -- make sure
    # they exist (with a stable dtype) before joins/expressions reference them.
    for col, default, dtype in (
        ("Group_Event", "", pl.String),
        ("Leave_Type", "", pl.String),
        ("Overtime_Hours", 0.0, pl.Float64),
        ("Overtime_Status", "", pl.String),
    ):
        if col not in daily.columns:
            daily = daily.with_columns(pl.lit(default, dtype=dtype).alias(col))

    # ---- Build small lookup frames from the (few) leave/overtime/event
    # records, then join them onto the (many) employee x date rows. This
    # keeps the row-count-heavy work vectorized while the lookup-building
    # itself stays as plain Python over a small list, same as before.

    # Individual overtime: sum duration per (employee, date).
    if leave_result.overtimes:
        ot_records = [
            {"_emp": str(ot.employee_id).strip(), "_date": ot.date, "_hours": float(ot.duration_hours)}
            for ot in leave_result.overtimes
        ]
        ot_df = (
            pl.DataFrame(ot_records, schema={"_emp": pl.String, "_date": pl.Date, "_hours": pl.Float64})
            .group_by(["_emp", "_date"])
            .agg(pl.col("_hours").sum().alias("_ind_ot_hours"))
        )
    else:
        ot_df = pl.DataFrame(schema={"_emp": pl.String, "_date": pl.Date, "_ind_ot_hours": pl.Float64})

    # Approved individual leave: last record wins per (employee, date),
    # same as the original dict-comprehension semantics.
    leave_pairs: dict[tuple[str, dt.date], str] = {}
    for lr in leave_result.leaves:
        emp = str(lr.employee_id).strip()
        for d in lr.dates():
            leave_pairs[(emp, d)] = lr.leave_type
    leave_df = pl.DataFrame(
        [{"_emp": emp, "_date": d, "_leave_type": lt} for (emp, d), lt in leave_pairs.items()],
        schema={"_emp": pl.String, "_date": pl.Date, "_leave_type": pl.String},
    )

    # Group events: last event wins per date, split by type (same as before).
    holiday_by_date: dict[dt.date, GroupEvent] = {}
    overtime_event_by_date: dict[dt.date, GroupEvent] = {}
    for ev in leave_result.group_events:
        target = holiday_by_date if ev.event_type == GroupEventType.LIBUR_BERSAMA else overtime_event_by_date
        for d in ev.dates():
            target[d] = ev
    holiday_df = pl.DataFrame(
        [{"_date": d, "_holiday_name": ev.name} for d, ev in holiday_by_date.items()],
        schema={"_date": pl.Date, "_holiday_name": pl.String},
    )
    overtime_event_df = pl.DataFrame(
        [
            {"_date": d, "_event_name": ev.name, "_event_hours": float(ev.duration_hours or 8.0)}
            for d, ev in overtime_event_by_date.items()
        ],
        schema={"_date": pl.Date, "_event_name": pl.String, "_event_hours": pl.Float64},
    )

    # Join key: employee id, trimmed the same way the original lookup keys were.
    daily = daily.with_columns(pl.col(id_col).cast(pl.String).str.strip_chars().alias("_join_emp"))
    daily = daily.join(ot_df, left_on=["_join_emp", date_col], right_on=["_emp", "_date"], how="left")
    daily = daily.join(leave_df, left_on=["_join_emp", date_col], right_on=["_emp", "_date"], how="left")
    daily = daily.join(holiday_df, left_on=date_col, right_on="_date", how="left")
    daily = daily.join(overtime_event_df, left_on=date_col, right_on="_date", how="left")

    is_holiday_case = pl.col("_holiday_name").is_not_null()
    is_leave_case = (~is_holiday_case) & pl.col("_leave_type").is_not_null()
    is_overtime_event_case = (~is_holiday_case) & (~is_leave_case) & pl.col("_event_name").is_not_null()
    has_individual_ot = pl.col("_ind_ot_hours").is_not_null()
    no_scan = pl.col("Scan_Count").fill_null(0) == 0
    any_case_no_scan = (is_holiday_case | is_leave_case | is_overtime_event_case) & no_scan

    ind_ot = pl.col("_ind_ot_hours").fill_null(0.0).round(2)
    event_hours = pl.col("_event_hours").fill_null(0.0)

    daily = daily.with_columns(
        Group_Event=pl.when(is_holiday_case)
        .then(pl.col("_holiday_name"))
        .when(is_overtime_event_case)
        .then(pl.col("_event_name"))
        .otherwise(pl.col("Group_Event")),
        Leave_Type=pl.when(is_leave_case).then(pl.col("_leave_type")).otherwise(pl.col("Leave_Type")),
        Overtime_Hours=pl.when(is_overtime_event_case).then((ind_ot + event_hours).round(2)).otherwise(ind_ot),
        Overtime_Status=pl.when(has_individual_ot | is_overtime_event_case)
        .then(pl.lit("Approved"))
        .otherwise(pl.col("Overtime_Status")),
    )

    daily = daily.with_columns(
        Absent_Flag=pl.when(is_holiday_case | is_leave_case | (is_overtime_event_case & no_scan))
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.col("Absent_Flag")),
        Is_Working_Day=pl.when(is_holiday_case).then(pl.lit(False)).otherwise(pl.col("Is_Working_Day")),
        Work_Day_Flag=pl.when(is_holiday_case)
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.col("Work_Day_Flag")),
        Present_Flag=pl.when(is_leave_case | (is_overtime_event_case & no_scan))
        .then(pl.lit(1, dtype=pl.Int64))
        .otherwise(pl.col("Present_Flag")),
    )

    daily = daily.with_columns(
        Status_Masuk=pl.when(is_holiday_case & no_scan)
        .then(pl.lit("Libur Bersama"))
        .when(is_leave_case & no_scan)
        .then(pl.lit("Cuti Disetujui"))
        .when(is_overtime_event_case & no_scan)
        .then(pl.lit("Lembur Bersama"))
        .otherwise(pl.col("Status_Masuk")),
        Status_Pulang=pl.when(is_holiday_case & no_scan)
        .then(pl.lit("Libur Bersama"))
        .when(is_leave_case & no_scan)
        .then(pl.col("_leave_type"))
        .when(is_overtime_event_case & no_scan)
        .then(pl.lit("Lembur Bersama"))
        .otherwise(pl.col("Status_Pulang")),
        Menit_Telat=pl.when(any_case_no_scan).then(pl.lit(0, dtype=pl.Int64)).otherwise(pl.col("Menit_Telat")),
        Menit_Pulang_Cepat=pl.when(any_case_no_scan)
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.col("Menit_Pulang_Cepat")),
        Is_Anomali=pl.when(any_case_no_scan).then(pl.lit(0, dtype=pl.Int64)).otherwise(pl.col("Is_Anomali")),
        Late_Flag=pl.when((is_holiday_case | is_leave_case) & no_scan)
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.col("Late_Flag")),
        Early_Leave_Flag=pl.when((is_holiday_case | is_leave_case) & no_scan)
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.col("Early_Leave_Flag")),
    )

    return daily.drop(
        ["_join_emp", "_ind_ot_hours", "_leave_type", "_holiday_name", "_event_name", "_event_hours"]
    )



# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _pad(row: tuple, length: int) -> tuple:
    return row[:length] if len(row) >= length else row + (None,) * (length - len(row))

def _is_blank(val: object) -> bool:
    return val is None or (isinstance(val, str) and val.strip() == "")

def _row_is_blank(row: tuple) -> bool:
    return all(_is_blank(v) for v in row)

def _to_date(val: object) -> Optional[dt.date]:
    if val is None:
        return None
    if isinstance(val, dt.datetime):
        return val.date()
    if isinstance(val, dt.date):
        return val
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "nat", "<null>"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    return None

def _hours_between(start: dt.time, end: dt.time) -> float:
    s = start.hour + start.minute / 60.0
    e = end.hour + end.minute / 60.0
    return e - s if e >= s else (e + 24) - s

def _date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
