"""CUPS integration via pycups.

STRICTLY read + submit-job only. This module never creates, deletes,
renames, or reconfigures printers, and never touches /etc/cups or restarts
any service. Printers are treated as an external, pre-configured
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

import cups


@dataclass(frozen=True)
class PrinterInfo:
    name: str
    is_default: bool
    state: int
    state_message: str
    location: str
    make_and_model: str
    accepting_jobs: bool


class CupsError(RuntimeError):
    pass


def _connection() -> cups.Connection:
    try:
        return cups.Connection()
    except RuntimeError as exc:  # cupsd not reachable
        raise CupsError(f"Cannot reach CUPS: {exc}") from exc


def list_printers() -> list[PrinterInfo]:
    """Enumerate printers already configured in CUPS. Read-only."""
    conn = _connection()
    dests = conn.getPrinters()
    default_name = conn.getDefault()
    printers = []
    for name, attrs in dests.items():
        printers.append(
            PrinterInfo(
                name=name,
                is_default=(name == default_name),
                state=attrs.get("printer-state", 0),
                state_message=attrs.get("printer-state-message", ""),
                location=attrs.get("printer-location", ""),
                make_and_model=attrs.get("printer-make-and-model", ""),
                accepting_jobs=attrs.get("printer-is-accepting-jobs", False),
            )
        )
    return printers


def get_printer_attributes(printer_name: str) -> dict:
    """Full IPP attribute dict for a printer (paper sizes, media types,
    resolutions, color modes, etc.), read-only."""
    conn = _connection()
    return conn.getPrinterAttributes(printer_name)


def print_pdf(
    printer_name: str,
    pdf_path: str,
    job_title: str = "Photo Print Wizard",
    options: dict[str, str] | None = None,
) -> int:
    """Submits an already-rendered PDF as a print job. Returns the CUPS job ID.

    `options` maps directly to IPP job attributes, e.g.
    {"media": "iso_a4_210x297mm", "print-quality": "5", "print-color-mode": "color"}.
    """
    conn = _connection()
    job_id = conn.printFile(printer_name, pdf_path, job_title, options or {})
    return job_id


def get_job_status(job_id: int) -> dict:
    conn = _connection()
    jobs = conn.getJobAttributes(job_id)
    return jobs


def cancel_job(job_id: int) -> None:
    """Cancels a job submitted by this application. Does not touch printer
    configuration."""
    conn = _connection()
    conn.cancelJob(job_id)
