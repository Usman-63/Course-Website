"""
Public facade for Google Sheets helper utilities.

This module re-exports functions from smaller, focused modules to keep
backwards compatibility with existing imports while making the codebase
more modular and maintainable.
"""

from sheets.sheets_attendance import format_attendance, format_attendance_to_string
from sheets.sheets_dataframe import normalize_dataframe
from sheets.sheets_email import validate_email, validate_email_list
from sheets.sheets_merge import (
    merge_register_survey,
    merge_with_admin_logs,
    detect_new_students,
)
from sheets.sheets_student_display import prepare_student_for_display

__all__ = [
    "merge_register_survey",
    "merge_with_admin_logs",
    "detect_new_students",
    "format_attendance",
    "format_attendance_to_string",
    "validate_email",
    "validate_email_list",
    "normalize_dataframe",
    "prepare_student_for_display",
]

