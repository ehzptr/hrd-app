import logging
import sys
import threading
from pathlib import Path

import flet as ft

from ui.page import build_page


def configure_logging() -> Path:
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "hrd-app.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
    return log_path


def _log_uncaught_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("hrd_app").critical(
        "Uncaught desktop application exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def _log_thread_exception(args: threading.ExceptHookArgs) -> None:
    logging.getLogger("hrd_app").critical(
        "Uncaught background thread exception",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def main(page: ft.Page) -> None:
    logging.getLogger("hrd_app").info("Building page with native Flet DataTable")
    page.title = "HR Attendance, Payroll & Sales Dashboard"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    build_page(page)


if __name__ == "__main__":
    log_path = configure_logging()
    sys.excepthook = _log_uncaught_exception
    threading.excepthook = _log_thread_exception
    logging.getLogger("hrd_app").info("Starting HR dashboard; log file=%s", log_path)
    try:
        ft.run(main)
    except BaseException:
        logging.getLogger("hrd_app").exception("Flet desktop runtime failed")
        raise