"""
Helpers to prepare student rows for API responses.
"""
from typing import Any, Dict

import pandas as pd

from sheets.sheets_attendance import format_attendance


def prepare_student_for_display(student_row: pd.Series) -> Dict[str, Any]:
    """
    Convert student DataFrame row to dictionary for API response.
    Handles attendance JSON parsing and data type conversion.
    """
    student_dict = student_row.to_dict()

    # Ensure Name field is set (try multiple name field variations)
    if (
        "Name" not in student_dict
        or pd.isna(student_dict.get("Name"))
        or str(student_dict.get("Name", "")).strip() == ""
    ):
        # Try to get name from other fields
        if "Student Full Name" in student_dict and not pd.isna(student_dict.get("Student Full Name")):
            student_dict["Name"] = str(student_dict["Student Full Name"]).strip()
        elif "First Name" in student_dict and "Last Name" in student_dict:
            first = (
                str(student_dict.get("First Name", "")).strip()
                if not pd.isna(student_dict.get("First Name"))
                else ""
            )
            last = (
                str(student_dict.get("Last Name", "")).strip()
                if not pd.isna(student_dict.get("Last Name"))
                else ""
            )
            if first or last:
                student_dict["Name"] = f"{first} {last}".strip()
        elif "First Name" in student_dict and not pd.isna(student_dict.get("First Name")):
            student_dict["Name"] = str(student_dict["First Name"]).strip()
        elif "Last Name" in student_dict and not pd.isna(student_dict.get("Last Name")):
            student_dict["Name"] = str(student_dict["Last Name"]).strip()

    # Standardize Resume Link
    # Look for the specific upload column if 'Resume Link' is missing
    # Handle variations with trailing spaces as well
    if "Resume Link" not in student_dict or not student_dict.get("Resume Link"):
        if (
            "Upload your Resume / CV (PDF preferred)" in student_dict
            and student_dict["Upload your Resume / CV (PDF preferred)"]
        ):
            student_dict["Resume Link"] = student_dict["Upload your Resume / CV (PDF preferred)"]
        elif (
            "Upload your Resume / CV (PDF preferred) " in student_dict
            and student_dict["Upload your Resume / CV (PDF preferred) "]
        ):
            student_dict["Resume Link"] = student_dict["Upload your Resume / CV (PDF preferred) "]

    # Parse attendance JSON string
    if "Attendance" in student_dict:
        attendance_str = student_dict.get("Attendance", "{}")
        student_dict["Attendance"] = format_attendance(attendance_str)

    # Convert NaN to None for JSON serialization, and handle empty strings
    for key, value in list(student_dict.items()):
        if pd.isna(value):
            student_dict[key] = None
        elif isinstance(value, str) and value.strip() == "":
            # Keep empty strings as empty strings (not None) for some fields
            if key not in ["Name", "Email Address"]:
                student_dict[key] = None
        elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
            student_dict[key] = value.isoformat()

    return student_dict


