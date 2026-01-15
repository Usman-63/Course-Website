"""
Helper functions for Google Sheets data processing and merging.
"""
import pandas as pd
import json
import re
from typing import Dict, List, Any, Optional


def merge_register_survey(register_df: pd.DataFrame, survey_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge Register and Survey spreadsheets on Email Address.
    - From Register: Only keeps specific columns (Timestamp, Choose The Tiered Program, 
      Payment Method, Add Payment Screenshot, Email Address, Onboarding)
    - From Survey: Keeps ALL columns
    - Payment Status: "Unpaid" if Add Payment Screenshot is empty OR student only in Survey
    
    Args:
        register_df: DataFrame from Register spreadsheet
        survey_df: DataFrame from Survey spreadsheet
        
    Returns:
        Merged DataFrame with all Survey columns + selected Register columns
    """
    # Normalize email column name (handle variations)
    register_email_col = _find_email_column(register_df) if not register_df.empty else None
    survey_email_col = _find_email_column(survey_df) if not survey_df.empty else None
    
    # Handle case where one or both are empty
    if register_df.empty and survey_df.empty:
        return pd.DataFrame()
    
    if register_df.empty:
        # Only Survey has data - all students are "Unpaid"
        survey_df = survey_df.copy()
        survey_df['Payment Status'] = 'Unpaid'
        return survey_df
    
    if survey_df.empty or not survey_email_col:
        # Only Register has data - filter to only needed columns
        register_df = register_df.copy()
        # Keep only specified columns from Register
        register_columns_to_keep = [
            'Timestamp',
            'Choose The Tiered Program',
            'Payment Method',
            'Add Payment Screenshot.',
            'Add Payment Screenshot',  # Handle with/without period
            'Onboarding',
            'Name',
            'Student Name',
            'Student Full Name',
            'First Name',
            'Last Name',
            'Full Name'
        ]
        
        # Find actual column names (case-insensitive, handle variations)
        register_keep_cols = []
        for col in register_df.columns:
            col_lower = str(col).lower().strip()
            for keep_col in register_columns_to_keep:
                if keep_col.lower().strip() == col_lower or keep_col.lower().strip().replace('.', '') == col_lower.replace('.', ''):
                    register_keep_cols.append(col)
                    break
        
        # Always include email column
        if register_email_col and register_email_col not in register_keep_cols:
            register_keep_cols.append(register_email_col)
        
        # Filter register to only keep needed columns
        if register_keep_cols:
            register_df = register_df[register_keep_cols]
        
        # Set Payment Status based on Add Payment Screenshot
        payment_screenshot_col = None
        for col in register_df.columns:
            if 'payment' in col.lower() and 'screenshot' in col.lower():
                payment_screenshot_col = col
                break
        
        if payment_screenshot_col:
            # Unpaid if screenshot is empty
            register_df['Payment Status'] = register_df[payment_screenshot_col].apply(
                lambda x: 'Paid' if pd.notna(x) and str(x).strip() != '' else 'Unpaid'
            )
        else:
            register_df['Payment Status'] = 'Unpaid'
        
        return register_df
    
    if not register_email_col:
        raise ValueError("Register spreadsheet must have an 'Email Address' column")
    
    # Filter Register to only keep specified columns
    register_columns_to_keep = [
        'Timestamp',
        'Choose The Tiered Program',
        'Payment Method',
        'Add Payment Screenshot.',
        'Add Payment Screenshot',  # Handle with/without period
        'Onboarding',
        'Upload your Resume / CV (PDF preferred)',
        'Name',
        'Student Name',
        'Student Full Name',
        'First Name',
        'Last Name',
        'Full Name'
    ]
    
    # Find actual column names (case-insensitive, handle variations)
    register_keep_cols = []
    for col in register_df.columns:
        col_lower = str(col).lower().strip()
        for keep_col in register_columns_to_keep:
            keep_col_clean = keep_col.lower().strip().replace('.', '')
            col_clean = col_lower.replace('.', '')
            if keep_col_clean == col_clean:
                register_keep_cols.append(col)
                break
    
    # Always include email column
    if register_email_col not in register_keep_cols:
        register_keep_cols.append(register_email_col)
    
    # Filter register to only keep needed columns
    register_filtered = register_df[register_keep_cols].copy() if register_keep_cols else pd.DataFrame()
    
    # Create copies for merging
    register_copy = register_filtered.copy()
    survey_copy = survey_df.copy()
    
    # Standardize email column names for merging
    register_copy = register_copy.rename(columns={register_email_col: 'Email Address'})
    survey_copy = survey_copy.rename(columns={survey_email_col: 'Email Address'})
    
    # Add source indicator to track which students came from where
    register_copy['_from_register'] = True
    survey_copy['_from_survey'] = True
    
    # Outer join to include all students from both sources
    # Use suffixes to handle column name conflicts (Survey columns keep original names)
    merged = survey_copy.merge(
        register_copy,
        on='Email Address',
        how='outer',
        suffixes=('', '_from_register')
    )
    
    # Determine Payment Status based on Add Payment Screenshot
    payment_screenshot_col = None
    for col in merged.columns:
        if 'payment' in col.lower() and 'screenshot' in col.lower():
            payment_screenshot_col = col
            break
    
    # Set Payment Status
    has_register = merged['_from_register'].fillna(False)
    
    if payment_screenshot_col:
        # Check if payment screenshot exists and is not empty
        has_payment_screenshot = merged[payment_screenshot_col].apply(
            lambda x: pd.notna(x) and str(x).strip() != ''
        )
        
        # Initialize Payment Status
        merged['Payment Status'] = 'Unpaid'  # Default
        
        # For register students: Paid if screenshot exists, Unpaid if empty
        merged.loc[has_register & has_payment_screenshot, 'Payment Status'] = 'Paid'
        merged.loc[has_register & ~has_payment_screenshot, 'Payment Status'] = 'Unpaid'
        
        # For survey-only students (not in register): Always Unpaid
        merged.loc[~has_register, 'Payment Status'] = 'Unpaid'
    else:
        # No payment screenshot column found - default all to Unpaid
        merged['Payment Status'] = 'Unpaid'
    
    # Clean up columns: Remove source indicators and handle duplicate column names
    merged = merged.drop(columns=['_from_register', '_from_survey'], errors='ignore')
    
    # For columns that exist in both (with _from_register suffix), keep the Register version
    # and rename to remove suffix (these are the specific Register columns we want)
    register_specific_cols = [
        'Timestamp', 
        'Choose The Tiered Program', 
        'Payment Method', 
        'Add Payment Screenshot', 
        'Onboarding',
        'Upload your Resume / CV (PDF preferred)'
    ]
    
    for col in list(merged.columns):
        if col.endswith('_from_register'):
            base_col = col.replace('_from_register', '').strip()
            # If this is a Register-specific column we want, keep it and remove suffix
            if any(reg_col.lower().replace('.', '') == base_col.lower().replace('.', '') for reg_col in register_specific_cols):
                merged = merged.rename(columns={col: base_col})
            # If base column exists from Survey, drop the Register version (Survey takes priority)
            elif base_col in merged.columns:
                merged = merged.drop(columns=[col], errors='ignore')
            else:
                # Unique Register column, keep it without suffix
                merged = merged.rename(columns={col: base_col})
    
    # Map name columns: Create a standard "Name" column from various name fields
    # We use coalesce logic to fill 'Name' from available columns in priority order
    
    # 1. Start with existing 'Name' column or create empty one
    if 'Name' not in merged.columns:
        merged['Name'] = pd.NA
    
    # 2. Fill missing Names from other potential columns
    potential_name_cols = ['Student Full Name', 'Student Name', 'Full Name']
    for col in potential_name_cols:
        if col in merged.columns:
            # If Name is null, try to fill from this column
            merged['Name'] = merged['Name'].fillna(merged[col])
            
    # 3. Fill missing Names from First/Last Name combination
    if 'First Name' in merged.columns and 'Last Name' in merged.columns:
        # Create full name only where both exist (or at least one)
        first = merged['First Name'].fillna('').astype(str).str.strip()
        last = merged['Last Name'].fillna('').astype(str).str.strip()
        full_name = (first + ' ' + last).str.strip()
        # Replace empty strings with NA so fillna works
        full_name = full_name.replace('', pd.NA)
        merged['Name'] = merged['Name'].fillna(full_name)
    
    # 4. Fallbacks for single name columns
    if 'First Name' in merged.columns:
        merged['Name'] = merged['Name'].fillna(merged['First Name'])
    if 'Last Name' in merged.columns:
        merged['Name'] = merged['Name'].fillna(merged['Last Name'])
        
    return merged


def merge_with_admin_logs(merged_df: pd.DataFrame, admin_logs_df: pd.DataFrame, total_labs: int = 2) -> pd.DataFrame:
    """
    Merge (Survey + Register) result with Admin_Logs on Email Address.
    If student not in Admin_Logs → Initialize with default values.
    Assignment grades are dynamically created based on total_labs count.
    
    Args:
        merged_df: DataFrame from Survey + Register merge
        admin_logs_df: DataFrame from Admin_Logs spreadsheet
        total_labs: Total number of labs across all modules (determines number of assignment grades)
        
    Returns:
        Complete merged DataFrame with all student data
    """
    if merged_df.empty:
        return pd.DataFrame()
    
    # Normalize email column names
    merged_email_col = _find_email_column(merged_df)
    admin_email_col = _find_email_column(admin_logs_df)
    
    if not merged_email_col:
        raise ValueError("Merged data must have an 'Email Address' column")
    
    # Generate assignment grade column names based on total labs
    assignment_columns = [f'Assignment {i+1} Grade' for i in range(total_labs)]
    
    if admin_logs_df.empty or not admin_email_col:
        # If Admin_Logs is empty, initialize all students with defaults
        return _initialize_default_admin_fields(merged_df, total_labs=total_labs)
    
    # Outer join with Admin_Logs to include students manually added there
    final = merged_df.merge(
        admin_logs_df,
        left_on=merged_email_col,
        right_on=admin_email_col,
        how='outer',
        suffixes=('', '_admin')
    )
    
    # Handle students only in Admin Logs (who have NaN for Register columns)
    # Coalesce Name
    if 'Name' in final.columns and 'Name_admin' in final.columns:
        final['Name'] = final['Name'].fillna(final['Name_admin'])
    elif 'Name' not in final.columns and 'Name_admin' in final.columns:
        final['Name'] = final['Name_admin']
        
    # Coalesce Payment Status
    # If Payment Status is NaN (because not in Register), default to Unpaid, 
    # UNLESS Admin Logs has a screenshot (we need to check for that column if we add it)
    if 'Payment Status' not in final.columns:
        final['Payment Status'] = 'Unpaid'
    else:
        final['Payment Status'] = final['Payment Status'].fillna('Unpaid')
        
    # Check if we have Payment Screenshot in Admin Logs (passed via add_student)
    # We look for a column that might contain 'screenshot' in _admin columns or regular columns
    # But merge_with_admin_logs doesn't know the exact column name in Admin Logs unless we find it.
    
    # Initialize default values for students not in Admin_Logs
    admin_columns = ['Attendance'] + assignment_columns + ['Teacher Evaluation']
    for col in admin_columns:
        if col not in final.columns:
            final[col] = None
        # Fill NaN with defaults
        if col == 'Attendance':
            final[col] = final[col].fillna('{}')
        elif 'Grade' in col:
            final[col] = final[col].fillna('')
        elif col == 'Teacher Evaluation':
            final[col] = final[col].fillna('')
    
    # Remove duplicate columns from admin (keep original merged columns)
    columns_to_drop = [col for col in final.columns if col.endswith('_admin')]
    final = final.drop(columns=columns_to_drop, errors='ignore')
    
    return final


def _initialize_default_admin_fields(df: pd.DataFrame, total_labs: int = 2) -> pd.DataFrame:
    """Initialize default Admin_Logs fields for students not in Admin_Logs."""
    df = df.copy()
    df['Attendance'] = '{}'
    # Create assignment grade columns based on total labs
    for i in range(total_labs):
        df[f'Assignment {i+1} Grade'] = ''
    df['Teacher Evaluation'] = ''
    return df


def format_attendance(attendance_str: str) -> Dict[str, bool]:
    """
    Convert attendance JSON string to dictionary.
    
    Args:
        attendance_str: JSON string like '{"Class 1": true, "Class 2": false}'
        
    Returns:
        Dictionary with class names as keys and boolean values
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
        
    Returns:
        JSON string representation
    """
    if not attendance_dict:
        return '{}'
    return json.dumps(attendance_dict)


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address string
        
    Returns:
        True if valid, False otherwise
    """
    if not email or pd.isna(email):
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, str(email).strip()))


def validate_email_list(emails: List[str]) -> List[str]:
    """
    Validate and format list of emails for export.
    
    Args:
        emails: List of email addresses
        
    Returns:
        List of valid, formatted emails
    """
    valid_emails = []
    for email in emails:
        if validate_email(email):
            valid_emails.append(str(email).strip().lower())
    return valid_emails


def detect_new_students(register_survey_df: pd.DataFrame, admin_logs_df: pd.DataFrame) -> List[str]:
    """
    Find students in Register/Survey but not in Admin_Logs.
    
    Args:
        register_survey_df: Merged Register + Survey DataFrame (Register is primary)
        admin_logs_df: Admin_Logs DataFrame
        
    Returns:
        List of email addresses for new students
    """
    if register_survey_df.empty:
        return []
    
    email_col = _find_email_column(register_survey_df)
    if not email_col:
        return []
    
    register_emails = set(register_survey_df[email_col].dropna().str.lower().str.strip())
    
    if admin_logs_df.empty:
        return list(register_emails)
    
    admin_email_col = _find_email_column(admin_logs_df)
    if not admin_email_col:
        return list(register_emails)
    
    admin_emails = set(admin_logs_df[admin_email_col].dropna().str.lower().str.strip())
    
    new_students = register_emails - admin_emails
    return list(new_students)


def _find_email_column(df: pd.DataFrame) -> Optional[str]:
    """Find email column in DataFrame (handles variations in naming)."""
    email_keywords = ['email', 'e-mail', 'email address']
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


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize DataFrame: strip whitespace, handle NaN values.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Normalized DataFrame
    """
    df = df.copy()
    
    # Strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' strings with actual NaN
            df[col] = df[col].replace(['nan', 'None', ''], pd.NA)
    
    return df


def prepare_student_for_display(student_row: pd.Series) -> Dict[str, Any]:
    """
    Convert student DataFrame row to dictionary for API response.
    Handles attendance JSON parsing and data type conversion.
    
    Args:
        student_row: Single row from merged DataFrame
        
    Returns:
        Dictionary with student data ready for JSON serialization
    """
    student_dict = student_row.to_dict()
    
    # Ensure Name field is set (try multiple name field variations)
    if 'Name' not in student_dict or pd.isna(student_dict.get('Name')) or str(student_dict.get('Name', '')).strip() == '':
        # Try to get name from other fields
        if 'Student Full Name' in student_dict and not pd.isna(student_dict.get('Student Full Name')):
            student_dict['Name'] = str(student_dict['Student Full Name']).strip()
        elif 'First Name' in student_dict and 'Last Name' in student_dict:
            first = str(student_dict.get('First Name', '')).strip() if not pd.isna(student_dict.get('First Name')) else ''
            last = str(student_dict.get('Last Name', '')).strip() if not pd.isna(student_dict.get('Last Name')) else ''
            if first or last:
                student_dict['Name'] = f"{first} {last}".strip()
        elif 'First Name' in student_dict and not pd.isna(student_dict.get('First Name')):
            student_dict['Name'] = str(student_dict['First Name']).strip()
        elif 'Last Name' in student_dict and not pd.isna(student_dict.get('Last Name')):
            student_dict['Name'] = str(student_dict['Last Name']).strip()

    # Standardize Resume Link
    # Look for the specific upload column if 'Resume Link' is missing
    # Handle variations with trailing spaces as well
    if 'Resume Link' not in student_dict or not student_dict.get('Resume Link'):
        if 'Upload your Resume / CV (PDF preferred)' in student_dict and student_dict['Upload your Resume / CV (PDF preferred)']:
             student_dict['Resume Link'] = student_dict['Upload your Resume / CV (PDF preferred)']
        elif 'Upload your Resume / CV (PDF preferred) ' in student_dict and student_dict['Upload your Resume / CV (PDF preferred) ']:
             student_dict['Resume Link'] = student_dict['Upload your Resume / CV (PDF preferred) ']
    
    # Parse attendance JSON string
    if 'Attendance' in student_dict:
        attendance_str = student_dict.get('Attendance', '{}')
        student_dict['Attendance'] = format_attendance(attendance_str)
    
    # Convert NaN to None for JSON serialization, and handle empty strings
    for key, value in student_dict.items():
        if pd.isna(value):
            student_dict[key] = None
        elif isinstance(value, str) and value.strip() == '':
            # Keep empty strings as empty strings (not None) for some fields
            if key not in ['Name', 'Email Address']:
                student_dict[key] = None
        elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
            student_dict[key] = value.isoformat()
    
    return student_dict

