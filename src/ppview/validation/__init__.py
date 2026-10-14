"""Structured PDF preflight diagnostics, independent of rendering and UI."""
from .preflight import CheckResult, PreflightReport, PreflightSettings, Status, analyze_pdf, run_preflight

__all__ = ["CheckResult", "PreflightReport", "PreflightSettings", "Status", "analyze_pdf", "run_preflight"]
