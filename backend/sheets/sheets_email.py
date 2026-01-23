"""
Email validation helpers for sheets data.
"""
import re
from typing import List

import pandas as pd


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address string
    """
    if not email or pd.isna(email):
        return False

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_pattern, str(email).strip()))


def validate_email_list(emails: List[str]) -> List[str]:
    """
    Validate and format list of emails for export.

    Args:
        emails: List of email addresses
    """
    valid_emails: List[str] = []
    for email in emails:
        if validate_email(email):
            valid_emails.append(str(email).strip().lower())
    return valid_emails


