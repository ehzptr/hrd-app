"""Typed view models used by the Flet UI panels.

These models intentionally contain presentation state only; pipeline and
configuration business rules remain in :mod:`ui.state`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.models import UploadedFile


@dataclass
class UploadViewModel:
    files: dict[str, UploadedFile | None] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)


@dataclass
class ConfigViewModel:
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultViewModel:
    """Result payload exposed to the results panel."""

    payload: dict[str, Any] | None = None
