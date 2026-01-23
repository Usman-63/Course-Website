"""
Utilities for merging Google Sheets data (Register, Survey) with Firestore admin data.
"""
from typing import List, Optional

import pandas as pd


def merge_register_survey(register_df: pd.DataFrame, survey_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge Register and Survey spreadsheets using a "master key ring" approach.
    
    This function treats Register as the authoritative source for payment data and builds
    a lookup dictionary (key ring) indexed by both email columns (Google email and student
    email if present). It then processes Survey rows, matching them against the key ring
    using a prioritized search strategy.
    
    Strategy:
    1. Phase 1 (Setup): Build a "master key ring" from Register, indexing payment data
       by both the Google Forms email column and any explicit student email column.
    2. Phase 2 (Merge): For each Survey row, search the key ring first by student email,
       then by Google email. Inject payment data when a match is found.
    
    Cases handled:
    - Case A: Same email everywhere - matches on first try
    - Case B: Missing typed email in Register, but Google email present - matches via Google ID
    - Case C: Different emails between forms - matches if at least one email appears in both
    
    Returns:
        DataFrame with all Survey columns plus payment-related columns from Register.
        Payment Status is set to "Paid" if payment screenshot exists, "Unpaid" otherwise.
    """
    # Normalize email column names (handle variations)
    register_email_col = _find_email_column(register_df) if not register_df.empty else None
    survey_email_col = _find_email_column(survey_df) if not survey_df.empty else None
    
    # Find student email column in Register (if present) - typically "Student Email" or similar
    register_student_email_col = _find_student_email_column(register_df) if not register_df.empty else None
    
    # Handle case where one or both are empty
    if register_df.empty and survey_df.empty:
        return pd.DataFrame()

    if register_df.empty:
        # Only Survey has data - all students are "Unpaid"
        survey_df = survey_df.copy()
        survey_df["Payment Status"] = "Unpaid"
        return survey_df

    if survey_df.empty or not survey_email_col:
        # Only Register has data - return Register with Payment Status set
        return _process_register_only(register_df, register_email_col)

    if not register_email_col:
        raise ValueError("Register spreadsheet must have an 'Email Address' column")

    # Find student email column in Survey (if present)
    survey_student_email_col = _find_student_email_column(survey_df)

    # Phase 1: Build the "Master Key Ring" from Register
    # This is a dictionary where keys are email addresses and values are payment data
    key_ring = _build_register_key_ring(
        register_df, 
        register_email_col, 
        register_student_email_col
    )

    # Phase 2: Process Survey rows and inject payment data from key ring
    merged_survey, matched_register_keys = _merge_survey_with_key_ring(
        survey_df,
        survey_email_col,
        survey_student_email_col,
        key_ring,
    )

    # Phase 3: Append Register-only students who never filled the Survey
    register_only_df = _process_register_only(
        register_df, register_email_col, register_student_email_col
    )

    if not register_only_df.empty:
        # Rows in register_only_df carry an internal "_register_key" column used
        # to detect which register rows were already matched via the Survey.
        if "_register_key" in register_only_df.columns:
            unmatched = register_only_df[
                ~register_only_df["_register_key"].isin(matched_register_keys)
            ].drop(columns=["_register_key"])
        else:
            # Fallback: if for some reason the internal key is missing, treat all as unmatched
            unmatched = register_only_df

        if not unmatched.empty:
            merged = pd.concat([merged_survey, unmatched], ignore_index=True, sort=False)
        else:
            merged = merged_survey
    else:
        merged = merged_survey

    # Normalize name columns (same logic as before for downstream compatibility)
    merged = _normalize_name_columns(merged)

    return merged


def _find_student_email_column(df: pd.DataFrame) -> Optional[str]:
    """
    Find a \"student email\" style column in a DataFrame.

    Handles variations in naming like:
    - \"Student Email\"
    - \"student_email\"
    - \"Student E-mail\"
    """
    if df is None or df.empty:
        return None

    keywords = ["student email", "student_email", "student e-mail"]
    return _find_column_by_keywords(df, keywords)


def _build_register_key_ring(
    register_df: pd.DataFrame,
    email_col: str,
    student_email_col: Optional[str],
) -> dict:
    """
    Phase 1: Build the \"Master Key Ring\" from Register data.

    For each register row, we capture ONLY the specified fields and index them
    in a dictionary by:
      - primary key: Email Address (Google default)
      - secondary key: Student Email (if present and non-empty)

    If the same email appears multiple times, the last row wins (latest data).
    """
    if register_df is None or register_df.empty:
        return {}

    # Map canonical names -> actual DataFrame column names
    def _match_column(possible_names: list[str]) -> Optional[str]:
        for col in register_df.columns:
            col_norm = str(col).lower().strip().replace(".", "")
            for name in possible_names:
                name_norm = name.lower().strip().replace(".", "")
                if col_norm == name_norm:
                    return col
        return None

    field_to_source_col: dict[str, Optional[str]] = {
        # The real sheet label includes a trailing period. We still match both
        # variants defensively, but normalize to the canonical name with period.
        "Choose The Tiered Program.": _match_column(
            ["Choose The Tiered Program.", "Choose The Tiered Program"]
        ),
        "Payment Method": _match_column(["Payment Method"]),
        # Screenshot may be with or without trailing period, or other slight variants
        "Add Payment Screenshot": _match_column(
            ["Add Payment Screenshot.", "Add Payment Screenshot"]
        ),
        "Email Address": email_col,
        "Student Email": student_email_col,
        "Onboarding": _match_column(["Onboarding"]),
    }

    key_ring: dict[str, dict] = {}

    for _, row in register_df.iterrows():
        # Build a small dict with canonical keys
        payment_data: dict = {}
        for field, source_col in field_to_source_col.items():
            if source_col and source_col in register_df.columns:
                val = row.get(source_col)
            else:
                val = None
            payment_data[field] = val

        # Normalize keys for lookup (lowercase trimmed emails)
        primary_email = str(row.get(email_col, "")).strip().lower() if email_col else ""
        student_email = (
            str(row.get(student_email_col, "")).strip().lower()
            if student_email_col
            else ""
        )

        # Internal canonical key for this register row (used to detect matches)
        register_key = primary_email or student_email
        payment_data["_register_key"] = register_key

        # Index by primary email if available
        if primary_email:
            key_ring[primary_email] = payment_data

        # Index by student email as secondary key if available
        if student_email:
            key_ring[student_email] = payment_data

    return key_ring


def _merge_survey_with_key_ring(
    survey_df: pd.DataFrame,
    email_col: Optional[str],
    student_email_col: Optional[str],
    key_ring: dict,
) -> tuple[pd.DataFrame, set[str]]:
    """
    Phase 2: Treat Survey as primary and inject Register payment data using the key ring.

    Lookup priority per row:
      1. Student Email (if available)
      2. Email Address (Google default)

    If no match is found, payment-related fields remain empty for that row.
    """
    if survey_df is None or survey_df.empty:
        return pd.DataFrame(), set()

    df = survey_df.copy()
    # Mark all these rows as having a survey response
    df["Has Survey Response"] = True
    matched_register_keys: set[str] = set()

    # Ensure the payment-related columns exist in the Survey DataFrame
    payment_columns = [
        "Choose The Tiered Program.",
        "Payment Method",
        "Add Payment Screenshot",
        "Email Address",   # canonical email column for downstream
        "Student Email",
        "Onboarding",
        "Payment Status",
    ]
    for col in payment_columns:
        if col not in df.columns:
            df[col] = None

    # Iterate rows and fill from key ring
    for idx, row in df.iterrows():
        # Get candidate emails from Survey
        survey_student_email = (
            str(row.get(student_email_col, "")).strip().lower()
            if student_email_col
            else ""
        )
        survey_email = (
            str(row.get(email_col, "")).strip().lower() if email_col else ""
        )

        payment_data = None

        # First try Student Email
        if survey_student_email and survey_student_email in key_ring:
            payment_data = key_ring[survey_student_email]
        # Fallback to Email Address (Google)
        elif survey_email and survey_email in key_ring:
            payment_data = key_ring[survey_email]

        if payment_data:
            # Inject payment fields into the row
            for field in [
                "Choose The Tiered Program.",
                "Payment Method",
                "Add Payment Screenshot",
                "Onboarding",
            ]:
                df.at[idx, field] = payment_data.get(field)

            # Ensure canonical email columns are set from the payment data if missing
            if not df.at[idx, "Email Address"]:
                df.at[idx, "Email Address"] = payment_data.get("Email Address")
            if not df.at[idx, "Student Email"]:
                df.at[idx, "Student Email"] = payment_data.get("Student Email")

            # Determine Payment Status based on screenshot presence
            screenshot_val = payment_data.get("Add Payment Screenshot")
            has_screenshot = (
                pd.notna(screenshot_val) and str(screenshot_val).strip() != ""
            )
            df.at[idx, "Payment Status"] = "Paid" if has_screenshot else "Unpaid"
            # Track which register entry this survey row matched
            register_key = payment_data.get("_register_key")
            if isinstance(register_key, str) and register_key:
                matched_register_keys.add(register_key)
        else:
            # No match in key ring → mark as Unpaid
            df.at[idx, "Payment Status"] = "Unpaid"

        # Ensure Email Address field has at least the Survey Google email
        if not df.at[idx, "Email Address"] and email_col:
            df.at[idx, "Email Address"] = row.get(email_col)

    return df, matched_register_keys


def _process_register_only(
    register_df: pd.DataFrame,
    email_col: str,
    student_email_col: Optional[str],
) -> pd.DataFrame:
    """
    Handle the case where only Register has data.

    We still build the key ring and then convert it back into a DataFrame of
    payment-related fields, ensuring downstream code has the expected columns.
    """
    key_ring = _build_register_key_ring(
        register_df, email_col, student_email_col
    )

    if not key_ring:
        return pd.DataFrame()

    records = list(key_ring.values())
    df = pd.DataFrame(records)

    # Compute Payment Status in the same way as for the Survey merge
    screenshot_col = "Add Payment Screenshot"
    if screenshot_col not in df.columns:
        df[screenshot_col] = None

    def _status_from_screenshot(val):
        if pd.notna(val) and str(val).strip() != "":
            return "Paid"
        return "Unpaid"

    df["Payment Status"] = df[screenshot_col].apply(_status_from_screenshot)
    # These rows have no corresponding survey response
    df["Has Survey Response"] = False

    return df


def _normalize_name_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize various name-related columns into a canonical 'Name' column.

    Priority:
      1. Existing 'Name'
      2. 'Student Full Name'
      3. 'Student Name'
      4. 'Full Name'
      5. 'First Name' + 'Last Name'
      6. Fallback to 'First Name' or 'Last Name'
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    if "Name" not in df.columns:
        df["Name"] = pd.NA

    # 2. Fill from other explicit name columns
    for col in ["Student Full Name", "Student Name", "Full Name"]:
        if col in df.columns:
            df["Name"] = df["Name"].fillna(df[col])

    # 3. Combine First/Last Name
    if "First Name" in df.columns and "Last Name" in df.columns:
        first = df["First Name"].fillna("").astype(str).str.strip()
        last = df["Last Name"].fillna("").astype(str).str.strip()
        full_name = (first + " " + last).str.strip()
        full_name = full_name.replace("", pd.NA)
        df["Name"] = df["Name"].fillna(full_name)

    # 4. Fallbacks for single name fields
    if "First Name" in df.columns:
        df["Name"] = df["Name"].fillna(df["First Name"])
    if "Last Name" in df.columns:
        df["Name"] = df["Name"].fillna(df["Last Name"])

    return df


def merge_with_admin_logs(
    merged_df: pd.DataFrame, admin_logs_df: pd.DataFrame, total_labs: int = 2
) -> pd.DataFrame:
    """
    Merge (Survey + Register) result with Firestore admin data on Email Address.
    If student not in admin data → Initialize with default values.
    Assignment grades are dynamically created based on total_labs count.
    
    Note: Function name kept for backward compatibility, but now merges with Firestore data.
    """
    if merged_df.empty:
        return pd.DataFrame()

    # Normalize email column names
    merged_email_col = _find_email_column(merged_df)
    admin_email_col = _find_email_column(admin_logs_df)

    if not merged_email_col:
        raise ValueError("Merged data must have an 'Email Address' column")

    # Generate assignment grade column names based on total labs
    assignment_columns = [f"Assignment {i+1} Grade" for i in range(total_labs)]

    if admin_logs_df.empty or not admin_email_col:
        # If admin data is empty, initialize all students with defaults
        return _initialize_default_admin_fields(merged_df, total_labs=total_labs)

    # Outer join with admin data to include students manually added there
    final = merged_df.merge(
        admin_logs_df,
        left_on=merged_email_col,
        right_on=admin_email_col,
        how="outer",
        suffixes=("", "_admin"),
    )

    # Handle students only in admin data (who have NaN for Register columns)
    # Coalesce Name
    if "Name" in final.columns and "Name_admin" in final.columns:
        final["Name"] = final["Name"].fillna(final["Name_admin"])
    elif "Name" not in final.columns and "Name_admin" in final.columns:
        final["Name"] = final["Name_admin"]

    # Coalesce Payment Status
    # Priority: 1) Admin-set paymentStatus from Firestore, 2) Screenshot-based status from Register, 3) Default to Unpaid
    if "Payment Status_admin" in final.columns:
        # Admin-set payment status takes priority - use it if not null, otherwise fall back to Register status
        # combine_first uses the first non-null value, so admin status takes priority
        final["Payment Status"] = final["Payment Status_admin"].combine_first(
            final.get("Payment Status", pd.Series(index=final.index, dtype=object))
        )
        # Fill any remaining NaN with "Unpaid"
        final["Payment Status"] = final["Payment Status"].fillna("Unpaid")
    elif "Payment Status" not in final.columns:
        final["Payment Status"] = "Unpaid"
    else:
        final["Payment Status"] = final["Payment Status"].fillna("Unpaid")
    
    # Coalesce Payment Comment (from admin data)
    if "Payment Comment_admin" in final.columns:
        final["Payment Comment"] = final["Payment Comment_admin"].fillna("")
    elif "Payment Comment" not in final.columns:
        final["Payment Comment"] = ""

    # Coalesce Teacher Evaluation (prefer admin data)
    if "Teacher Evaluation" in final.columns and "Teacher Evaluation_admin" in final.columns:
        # Use admin value if available, otherwise use merged value
        final["Teacher Evaluation"] = final["Teacher Evaluation_admin"].fillna(final["Teacher Evaluation"])
    elif "Teacher Evaluation_admin" in final.columns:
        final["Teacher Evaluation"] = final["Teacher Evaluation_admin"]
    elif "Teacher Evaluation" not in final.columns:
        final["Teacher Evaluation"] = None

    # Initialize default values for students not in admin data
    admin_columns = ["Attendance"] + assignment_columns + ["Teacher Evaluation"]
    for col in admin_columns:
        if col not in final.columns:
            final[col] = None
        # Fill NaN with defaults
        if col == "Attendance":
            final[col] = final[col].fillna("{}")
        elif "Grade" in col:
            final[col] = final[col].fillna("")
        elif col == "Teacher Evaluation":
            final[col] = final[col].fillna("")

    # Remove duplicate columns from admin (keep original merged columns)
    columns_to_drop = [col for col in final.columns if col.endswith("_admin")]
    final = final.drop(columns=columns_to_drop, errors="ignore")
    
    # Ensure Payment Comment column exists (even if empty)
    if "Payment Comment" not in final.columns:
        final["Payment Comment"] = ""

    return final


def _initialize_default_admin_fields(df: pd.DataFrame, total_labs: int = 2) -> pd.DataFrame:
    """Initialize default admin fields for students not in admin data."""
    df = df.copy()
    df["Attendance"] = "{}"
    # Create assignment grade columns based on total labs
    for i in range(total_labs):
        df[f"Assignment {i+1} Grade"] = ""
    df["Teacher Evaluation"] = ""
    return df


def detect_new_students(register_survey_df: pd.DataFrame, admin_logs_df: pd.DataFrame) -> List[str]:
    """
    Find students in Register/Survey but not in admin data.

    Args:
        register_survey_df: Merged Register + Survey DataFrame (Register is primary)
        admin_logs_df: Admin data DataFrame (from Firestore)

    Returns:
        List of email addresses for new students
    """
    if register_survey_df.empty:
        return []

    email_col = _find_email_column(register_survey_df)
    if not email_col:
        return []

    # Normalize and filter out empty/invalid emails
    register_emails_raw = register_survey_df[email_col].dropna().str.lower().str.strip()
    register_emails = {
        email for email in register_emails_raw 
        if email and len(email) >= 3 and '@' in email  # Basic email validation
    }

    if admin_logs_df.empty:
        return list(register_emails)

    admin_email_col = _find_email_column(admin_logs_df)
    if not admin_email_col:
        return list(register_emails)

    # Normalize and filter out empty/invalid emails
    admin_emails_raw = admin_logs_df[admin_email_col].dropna().str.lower().str.strip()
    admin_emails = {
        email for email in admin_emails_raw 
        if email and len(email) >= 3 and '@' in email  # Basic email validation
    }

    new_students = register_emails - admin_emails
    return list(new_students)


def _find_email_column(df: pd.DataFrame) -> Optional[str]:
    """Find email column in DataFrame (handles variations in naming)."""
    email_keywords = ["email", "e-mail", "email address"]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in email_keywords):
            return col
    return None


def _find_column_by_keywords(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Find column containing any of the given keywords."""
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in keywords):
            return col
    return None


