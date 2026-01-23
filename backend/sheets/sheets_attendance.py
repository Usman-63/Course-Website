"""
Attendance formatting helpers.
"""
import json
from typing import Dict

import pandas as pd


def format_attendance(attendance_str: str) -> Dict[str, bool]:
    """
    Convert attendance JSON string to dictionary.

    Args:
        attendance_str: JSON string like '{"Class 1": true, "Class 2": false}'
    """
    if not attendance_str or pd.isna(attendance_str):
        return {}

    try:
        if isinstance(attendance_str, dict):
            return attendance_str
        return json.loads(attendance_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def format_attendance_to_string(attendance_dict: Dict[str, bool]) -> str:
    """
    Convert attendance dictionary to JSON string.

    Args:
        attendance_dict: Dictionary with class names and boolean values
    """
    if not attendance_dict:
        return "{}"
    return json.dumps(attendance_dict)


