"""
Google Sheets Manager for reading and writing student operations data.
Handles 3 spreadsheets: Survey, Register, and Admin_Logs.
"""
import os
import json
import pandas as pd
import time
import threading
from typing import Dict, List, Any, Optional
from google.oauth2 import service_account
import gspread
import gspread.exceptions
from logger import logger
from sheets_utils import (
    merge_register_survey,
    merge_with_admin_logs,
    format_attendance,
    format_attendance_to_string,
    detect_new_students,
    normalize_dataframe,
    prepare_student_for_display
)


class GoogleSheetsManager:
    """Manages Google Sheets operations for student data."""
    
    def __init__(self):
        """Initialize Google Sheets client with service account credentials."""
        # Get spreadsheet IDs from environment
        self.survey_spreadsheet_id = os.getenv('GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID')
        self.register_spreadsheet_id = os.getenv('GOOGLE_SHEETS_REGISTER_SPREADSHEET_ID')
        self.admin_logs_spreadsheet_id = os.getenv('GOOGLE_SHEETS_ADMIN_LOGS_SPREADSHEET_ID')
        
        # Get worksheet names (with defaults)
        self.survey_worksheet = os.getenv('GOOGLE_SHEETS_SURVEY_WORKSHEET', 'Form Responses 1')
        self.register_worksheet = os.getenv('GOOGLE_SHEETS_REGISTER_WORKSHEET', 'Form Responses 1')
        self.admin_logs_worksheet = os.getenv('GOOGLE_SHEETS_ADMIN_LOGS_WORKSHEET', 'Admin_Logs')
        self.classes_worksheet = os.getenv('GOOGLE_SHEETS_CLASSES_WORKSHEET', 'Classes')
        
        # Validate required configuration
        if not self.survey_spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID environment variable is required")
        if not self.register_spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_REGISTER_SPREADSHEET_ID environment variable is required")
        if not self.admin_logs_spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_ADMIN_LOGS_SPREADSHEET_ID environment variable is required")
        
        # Initialize credentials (same pattern as GoogleDriveClient)
        self.client = self._initialize_client()
        
        # Simple cache to reduce API calls (helps with rate limits)
        self._cache = {}
        self._cache_ttl = 300  # Cache for 5 minutes (300 seconds) to reduce API calls and avoid rate limits
        
        # Rate limiting: track last request time to throttle requests
        self._last_request_time = 0
        self._min_request_interval = 0.2  # Minimum 200ms between requests (5 requests/second max) - more conservative
        
        # Cache for course data (to get lab count)
        self._course_data_cache = None
        self._course_data_cache_time = 0
        
        # Lock to prevent concurrent reads of the same data (prevents race conditions)
        self._read_lock = threading.Lock()
        self._reading_students = False  # Flag to prevent concurrent get_all_students calls
        
        # Cache for spreadsheets/worksheets objects to avoid re-fetching metadata (reduces API calls significantly)
        self._spreadsheets_cache = {}
        self._worksheets_cache = {}
    
    def _initialize_client(self) -> gspread.Client:
        """Initialize gspread client with service account credentials."""
        try:
            # 1. Try Base64 encoded JSON (Best for Render/Production)
            service_account_base64 = os.getenv('SERVICE_ACCOUNT_BASE64')
            # 2. Try Raw JSON string
            service_account_json = os.getenv('SERVICE_ACCOUNT_JSON')
            
            if service_account_base64:
                try:
                    import base64
                    decoded_json = base64.b64decode(service_account_base64).decode('utf-8')
                    service_account_info = json.loads(decoded_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        service_account_info,
                        scopes=[
                            'https://www.googleapis.com/auth/spreadsheets',
                            'https://www.googleapis.com/auth/drive'
                        ]
                    )
                except Exception as e:
                    raise ValueError(f"Invalid SERVICE_ACCOUNT_BASE64: {e}")
            elif service_account_json:
                # Parse JSON from environment variable
                try:
                    service_account_info = json.loads(service_account_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        service_account_info,
                        scopes=[
                            'https://www.googleapis.com/auth/spreadsheets',
                            'https://www.googleapis.com/auth/drive'
                        ]
                    )
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid SERVICE_ACCOUNT_JSON format: {e}")
            else:
                # Fall back to file path (for local development)
                service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH', './service_account.json')
                
                if not os.path.exists(service_account_path):
                    raise FileNotFoundError(
                        f"Service account file not found: {service_account_path}. "
                        "Either set SERVICE_ACCOUNT_JSON environment variable or provide a valid file path."
                    )
                
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
            
            # Initialize gspread client
            client = gspread.authorize(credentials)
            logger.info("Google Sheets client initialized successfully")
            return client
            
        except Exception as e:
            logger.error(f"Error initializing Google Sheets client: {str(e)}", exc_info=True)
            raise
    
    def _get_worksheet(self, spreadsheet_id: str, worksheet_name: str) -> gspread.Worksheet:
        """Get worksheet by name, checking object cache first."""
        cache_key = f"{spreadsheet_id}_{worksheet_name}"
        
        # Check object cache first
        if cache_key in self._worksheets_cache:
            return self._worksheets_cache[cache_key]
            
        try:
            # Check spreadsheet cache
            if spreadsheet_id in self._spreadsheets_cache:
                spreadsheet = self._spreadsheets_cache[spreadsheet_id]
            else:
                self._throttle_request()
                spreadsheet = self.client.open_by_key(spreadsheet_id)
                self._spreadsheets_cache[spreadsheet_id] = spreadsheet
            
            try:
                self._throttle_request()
                worksheet = spreadsheet.worksheet(worksheet_name)
                self._worksheets_cache[cache_key] = worksheet
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                # Try to get the first worksheet as fallback
                self._throttle_request()
                worksheets = spreadsheet.worksheets()
                if worksheets:
                    first_worksheet = worksheets[0]
                    logger.warning(
                        f"Worksheet '{worksheet_name}' not found in spreadsheet {spreadsheet_id}. "
                        f"Available worksheets: {[ws.title for ws in worksheets]}. "
                        f"Using first worksheet: '{first_worksheet.title}'"
                    )
                    # Cache the fallback result to avoid repeated lookups
                    self._worksheets_cache[cache_key] = first_worksheet
                    return first_worksheet
                else:
                    # List available worksheets in error
                    available = [ws.title for ws in worksheets] if worksheets else []
                    error_msg = (
                        f"Worksheet '{worksheet_name}' not found in spreadsheet {spreadsheet_id}. "
                        f"Available worksheets: {available if available else 'None (spreadsheet is empty)'}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found: {spreadsheet_id}")
            raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
        except ValueError:
            # Re-raise ValueError (our custom error)
            raise
        except Exception as e:
            logger.error(f"Error accessing worksheet: {str(e)}", exc_info=True)
            raise
    
    def _get_cached_data(self, cache_key: str) -> tuple[Any, float]:
        """Get cached data if still valid. Returns (data, timestamp) or (None, 0) if not cached."""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return data, timestamp
            else:
                del self._cache[cache_key]
        return None, 0
    
    def _set_cached_data(self, cache_key: str, data: Any):
        """Cache data with timestamp. Can cache DataFrames or lists."""
        self._cache[cache_key] = (data, time.time())
    
    def _get_total_labs_count(self) -> int:
        """Get total number of labs across all modules from course data."""
        try:
            # Check cache first
            if self._course_data_cache and (time.time() - self._course_data_cache_time) < 300:  # Cache for 5 minutes
                return self._course_data_cache
            
            # Try to get course data from Google Drive
            try:
                from google_drive import GoogleDriveClient
                drive_client = GoogleDriveClient()
                course_data = drive_client.get_course_data()
                
                total_labs = 0
                if course_data and 'modules' in course_data:
                    for module in course_data['modules']:
                        lab_count = module.get('labCount', 1)  # Default to 1 if not specified
                        total_labs += lab_count
                
                # Cache the result
                self._course_data_cache = total_labs
                self._course_data_cache_time = time.time()
                
                logger.info(f"Total labs across all modules: {total_labs}")
                return total_labs
            except Exception as e:
                logger.warning(f"Could not fetch course data for lab count: {str(e)}")
                # Default to 2 if we can't get course data
                return 2
        except Exception as e:
            logger.warning(f"Error getting total labs count: {str(e)}")
            return 2  # Default to 2 assignments
    
    def _throttle_request(self):
        """Throttle requests to avoid hitting rate limits."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    def _retry_with_backoff(self, func, max_retries=3, initial_delay=5):
        """
        Retry a function with exponential backoff on rate limit errors.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds (doubles each retry) - starts at 5s for rate limits
        """
        for attempt in range(max_retries):
            try:
                return func()
            except (ValueError, gspread.exceptions.APIError) as e:
                # Check if it's a rate limit error
                is_rate_limit = False
                if isinstance(e, gspread.exceptions.APIError):
                    error_dict = e.response if isinstance(e.response, dict) else {}
                    if error_dict.get('status') == 'RESOURCE_EXHAUSTED' or '429' in str(error_dict.get('code', '')):
                        is_rate_limit = True
                elif isinstance(e, ValueError) and ('Rate limit' in str(e) or '429' in str(e) or 'quota' in str(e).lower()):
                    is_rate_limit = True
                
                if is_rate_limit and attempt < max_retries - 1:
                    # For rate limits, use longer delays: 5s, 10s, 20s
                    delay = initial_delay * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                    logger.warning(
                        f"Rate limit hit (429), retrying in {delay} seconds "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Not a rate limit error, or max retries reached
                    raise
    
    def read_survey_data(self) -> pd.DataFrame:
        """
        Read data from Survey spreadsheet (READ-ONLY).
        Spreadsheet: "Pre-Course Survey of GEMINI 3 MASTERCLASS (Responses)"
        """
        cache_key = f"survey_{self.survey_spreadsheet_id}"
        cached_data, _ = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.debug("Using cached Survey data")
            return cached_data
        
        def _fetch_survey():
            self._throttle_request()
            worksheet = self._get_worksheet(self.survey_spreadsheet_id, self.survey_worksheet)
            
            try:
                records = worksheet.get_all_records()
            except (gspread.exceptions.APIError, IndexError) as e:
                # Handle completely empty worksheet (no headers) or API errors
                if isinstance(e, IndexError) or 'Unable to parse range' in str(e) or 'No data found' in str(e):
                    logger.warning("Survey spreadsheet appears to be empty or has no data")
                    return pd.DataFrame()
                # Re-raise to be handled by retry logic
                raise
            
            if not records:
                logger.warning("Survey spreadsheet is empty")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df = normalize_dataframe(df)
            logger.info(f"Read {len(df)} records from Survey spreadsheet")
            self._set_cached_data(cache_key, df)
            return df
        
        try:
            return self._retry_with_backoff(_fetch_survey)
        except gspread.exceptions.APIError as e:
            # Check for rate limit errors
            if e.response and e.response.get('status') == 'RESOURCE_EXHAUSTED':
                logger.error("Google Sheets API rate limit exceeded after retries.")
                raise ValueError("Rate limit exceeded. Please wait a minute and try again.")
            logger.error(f"Google Sheets API error reading Survey data: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to read Survey spreadsheet: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading Survey data: {str(e)}", exc_info=True)
            raise
    
    def read_register_data(self) -> pd.DataFrame:
        """
        Read data from Register spreadsheet (READ-ONLY, payment status).
        Spreadsheet: "GEMINI 3 MASTERCLASS (Responses)"
        """
        cache_key = f"register_{self.register_spreadsheet_id}"
        cached_data, _ = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.debug("Using cached Register data")
            return cached_data
        
        def _fetch_register():
            self._throttle_request()
            worksheet = self._get_worksheet(self.register_spreadsheet_id, self.register_worksheet)
            
            try:
                records = worksheet.get_all_records()
            except (gspread.exceptions.APIError, IndexError) as e:
                # Handle completely empty worksheet (no headers) or API errors
                if isinstance(e, IndexError) or 'Unable to parse range' in str(e) or 'No data found' in str(e):
                    logger.warning("Register spreadsheet appears to be empty or has no data")
                    return pd.DataFrame()
                # Re-raise to be handled by retry logic
                raise
            
            if not records:
                logger.warning("Register spreadsheet is empty")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df = normalize_dataframe(df)
            logger.info(f"Read {len(df)} records from Register spreadsheet")
            self._set_cached_data(cache_key, df)
            return df
        
        try:
            return self._retry_with_backoff(_fetch_register)
        except gspread.exceptions.APIError as e:
            # Check for rate limit errors
            if e.response and e.response.get('status') == 'RESOURCE_EXHAUSTED':
                logger.error("Google Sheets API rate limit exceeded after retries.")
                raise ValueError("Rate limit exceeded. Please wait a minute and try again.")
            logger.error(f"Google Sheets API error reading Register data: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to read Register spreadsheet: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading Register data: {str(e)}", exc_info=True)
            raise
    
    def read_admin_logs(self) -> pd.DataFrame:
        """
        Read data from Admin_Logs spreadsheet (READ/WRITE).
        Spreadsheet: "Dashboard Admin Logs"
        This is the only spreadsheet that can be modified.
        """
        cache_key = f"admin_logs_{self.admin_logs_spreadsheet_id}"
        cached_data, _ = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.debug("Using cached Admin_Logs data")
            return cached_data
        
        def _fetch_admin_logs():
            self._throttle_request()
            worksheet = self._get_worksheet(self.admin_logs_spreadsheet_id, self.admin_logs_worksheet)
            
            try:
                records = worksheet.get_all_records()
            except (gspread.exceptions.APIError, IndexError) as e:
                # Handle completely empty worksheet (no headers) or API errors
                if isinstance(e, IndexError) or 'Unable to parse range' in str(e) or 'No data found' in str(e):
                    logger.warning("Admin_Logs spreadsheet appears to be empty or has no data")
                    return pd.DataFrame()
                # Re-raise to be handled by retry logic
                raise
            
            if not records:
                logger.warning("Admin_Logs spreadsheet is empty")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df = normalize_dataframe(df)
            logger.info(f"Read {len(df)} records from Admin_Logs spreadsheet")
            self._set_cached_data(cache_key, df)
            return df
        
        try:
            return self._retry_with_backoff(_fetch_admin_logs)
        except gspread.exceptions.APIError as e:
            # Check for rate limit errors
            if e.response and e.response.get('status') == 'RESOURCE_EXHAUSTED':
                logger.error("Google Sheets API rate limit exceeded after retries.")
                raise ValueError("Rate limit exceeded. Please wait a minute and try again.")
            logger.error(f"Google Sheets API error reading Admin_Logs data: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to read Admin_Logs spreadsheet: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading Admin_Logs data: {str(e)}", exc_info=True)
            raise
    
    def get_all_students(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Merge all three spreadsheets and return complete student data.
        
        Steps:
        1. Merge Register + Survey (Register is primary, Survey data added)
        2. Merge result with Admin_Logs
        3. Return list of student dictionaries
        
        Uses locking to prevent concurrent reads and race conditions.
        """
        # Check cache first (with lock to prevent race conditions)
        cache_key = 'all_students'
        
        if force_refresh:
            logger.info("Force refresh requested: Clearing all student data caches")
            with self._read_lock:
                # Clear all related caches to ensure fresh data from all sheets
                keys_to_clear = [
                    cache_key,
                    f"survey_{self.survey_spreadsheet_id}",
                    f"register_{self.register_spreadsheet_id}",
                    f"admin_logs_{self.admin_logs_spreadsheet_id}"
                ]
                for key in keys_to_clear:
                    if key in self._cache:
                        del self._cache[key]
        
        with self._read_lock:
            cached_data, cache_time = self._get_cached_data(cache_key)
            if cached_data is not None and not force_refresh:
                logger.debug(f"Returning cached student data (age: {time.time() - cache_time:.1f}s)")
                return cached_data
            
            # If another thread is already reading, wait for it
            if self._reading_students:
                logger.warning("Another request is already reading students, waiting...")
                # Wait a bit and check cache again
                self._read_lock.release()
                time.sleep(0.5)
                self._read_lock.acquire()
                cached_data, cache_time = self._get_cached_data(cache_key)
                if cached_data is not None:
                    logger.debug(f"Returning cached student data after wait (age: {time.time() - cache_time:.1f}s)")
                    return cached_data
            
            # Mark that we're reading
            self._reading_students = True
        
        try:
            # Read all three spreadsheets
            register_df = self.read_register_data()
            survey_df = self.read_survey_data()
            admin_logs_df = self.read_admin_logs()
            
            if register_df.empty and survey_df.empty:
                logger.warning("Both Register and Survey spreadsheets are empty, returning empty list")
                return []
            
            # Step 1: Merge Register + Survey
            merged_df = merge_register_survey(register_df, survey_df)
            
            # Step 2: Merge with Admin_Logs (with dynamic assignment grades)
            # Get total labs from course data to determine number of assignment grades needed
            total_labs = self._get_total_labs_count()
            
            # Check for new students and auto-sync to Admin_Logs
            new_student_emails = detect_new_students(merged_df, admin_logs_df)
            if new_student_emails:
                logger.info(f"Detected {len(new_student_emails)} new students. Syncing to Admin_Logs...")
                # Filter merged_df to get details for these students
                # Note: merged_df has 'Email Address' normalized
                email_col = 'Email Address'
                if email_col in merged_df.columns:
                    new_students_data = merged_df[merged_df[email_col].isin(new_student_emails)]
                    if not new_students_data.empty:
                        # Perform bulk append in background (or synchronous for now)
                        self.bulk_add_students_to_admin_logs(new_students_data)
            
            # Step 3.5: Sync payment screenshots from Register to Admin_Logs for existing students
            # This ensures that if a student registered via form, their payment screenshot is saved in Admin_Logs
            self.sync_payment_screenshots(merged_df, admin_logs_df)
            
            final_df = merge_with_admin_logs(merged_df, admin_logs_df, total_labs=total_labs)
            
            # Sort by Name (if available) or Email Address
            if 'Name' in final_df.columns:
                final_df = final_df.sort_values('Name', na_position='last')
            elif 'Email Address' in final_df.columns:
                final_df = final_df.sort_values('Email Address', na_position='last')
            
            # Convert to list of dictionaries
            students = []
            for _, row in final_df.iterrows():
                student_dict = prepare_student_for_display(row)
                students.append(student_dict)
            
            # Cache the result
            with self._read_lock:
                self._set_cached_data(cache_key, students)
                self._reading_students = False
            
            logger.info(f"Successfully merged data for {len(students)} students")
            return students
            
        except Exception as e:
            # Release lock on error
            with self._read_lock:
                self._reading_students = False
            logger.error(f"Error getting all students: {str(e)}", exc_info=True)
            raise
    
    def get_student_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get specific student data by email address."""
        try:
            students = self.get_all_students()
            email_lower = email.lower().strip()
            
            for student in students:
                # Find email column
                student_email = None
                for key in ['Email Address', 'Email', 'email', 'email_address']:
                    if key in student and student[key]:
                        student_email = str(student[key]).lower().strip()
                        break
                
                if student_email == email_lower:
                    return student
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting student by email: {str(e)}", exc_info=True)
            raise
    
    def initialize_student_row(self, email: str, student_data: Dict[str, Any]) -> bool:
        """
        Create new row in Admin_Logs for new student.
        
        Args:
            email: Student email address
            student_data: Student data from Survey/Register (for reference)
            
        Returns:
            True if successful
        """
        try:
            worksheet = self._get_worksheet(self.admin_logs_spreadsheet_id, self.admin_logs_worksheet)
            
            # Get headers
            headers = worksheet.row_values(1)
            
            # Find email column index
            email_col_idx = None
            for i, header in enumerate(headers):
                if 'email' in header.lower():
                    email_col_idx = i + 1  # gspread uses 1-based indexing
                    break
            
            if email_col_idx is None:
                # Add Email Address column if it doesn't exist
                headers.append('Email Address')
                worksheet.update('A1', [headers])
                email_col_idx = len(headers)
            
            # Prepare new row with default values
            new_row = [''] * len(headers)
            new_row[email_col_idx - 1] = email
            
            # Get total labs to determine assignment grade columns
            total_labs = self._get_total_labs_count()
            
            # Set default values for admin columns (dynamic based on lab count)
            admin_columns = {'Attendance': '{}', 'Teacher Evaluation': ''}
            
            # Add Name if available in student_data (to persist it in Admin Logs)
            name = student_data.get('Name') or student_data.get('Student Name') or student_data.get('Full Name') or student_data.get('First Name', '') + ' ' + student_data.get('Last Name', '')
            if name and name.strip():
                admin_columns['Name'] = name.strip()
            
            for i in range(total_labs):
                admin_columns[f'Assignment {i+1} Grade'] = ''
            
            for col_name, default_value in admin_columns.items():
                if col_name in headers:
                    col_idx = headers.index(col_name)
                    new_row[col_idx] = default_value
                else:
                    # Add new column
                    headers.append(col_name)
                    new_row.append(default_value)
                    # Update worksheet headers
                    worksheet.update('A1', [headers])
            
            # Append new row
            worksheet.append_row(new_row)
            logger.info(f"Initialized Admin_Logs row for student: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing student row: {str(e)}", exc_info=True)
            raise
    
    def update_student_data(self, email: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific student's data in Admin_Logs (WRITE-ONLY to Admin_Logs).
        Survey and Register spreadsheets are never modified.
        
        Args:
            email: Student email address
            updates: Dictionary of fields to update (Attendance, grades, evaluation)
            
        Returns:
            True if successful
        """
        try:
            if not email or not email.strip():
                raise ValueError("Email address is required")
            
            if not updates:
                raise ValueError("No updates provided")
            
            worksheet = self._get_worksheet(self.admin_logs_spreadsheet_id, self.admin_logs_worksheet)
            
            # Get all records to find the row
            try:
                records = worksheet.get_all_records()
            except Exception as e:
                logger.warning(f"Error reading records, trying to initialize worksheet: {str(e)}")
                # If worksheet is empty, create headers (dynamic based on lab count)
                total_labs = self._get_total_labs_count()
                headers = ['Email Address', 'Attendance']
                for i in range(total_labs):
                    headers.append(f'Assignment {i+1} Grade')
                headers.append('Teacher Evaluation')
                worksheet.update('A1', [headers])
                records = []
            
            headers = worksheet.row_values(1)
            if not headers:
                raise ValueError("Admin_Logs worksheet has no headers")
            
            # Find email column
            email_col = None
            for col in headers:
                if 'email' in col.lower():
                    email_col = col
                    break
            
            if not email_col:
                # Add email column if missing
                headers.append('Email Address')
                worksheet.update('A1', [headers])
                email_col = 'Email Address'
            
            # Find row index for this email
            row_idx = None
            email_lower = email.lower().strip()
            for i, record in enumerate(records):
                record_email = str(record.get(email_col, '')).lower().strip()
                if record_email == email_lower:
                    row_idx = i + 2  # +2 because: 1 for header, 1 for 0-based to 1-based
                    break
            
            if row_idx is None:
                # Student not in Admin_Logs, initialize first
                logger.info(f"Student {email} not in Admin_Logs, initializing row")
                self.initialize_student_row(email, {})
                # Re-read to get updated row index
                records = worksheet.get_all_records()
                headers = worksheet.row_values(1)
                for i, record in enumerate(records):
                    record_email = str(record.get(email_col, '')).lower().strip()
                    if record_email == email_lower:
                        row_idx = i + 2
                        break
                
                if row_idx is None:
                    raise ValueError(f"Failed to create row for student: {email}")
            
            # Prepare updates
            cells_to_update = []
            for field, value in updates.items():
                if field not in headers:
                    # Add new column
                    headers.append(field)
                    worksheet.update('A1', [headers])
                
                col_idx = headers.index(field) + 1  # Convert to 1-based
                cell_address = gspread.utils.rowcol_to_a1(row_idx, col_idx)
                
                # Format attendance as JSON string
                if field == 'Attendance' and isinstance(value, dict):
                    value = format_attendance_to_string(value)
                elif value is None:
                    value = ''
                
                cells_to_update.append({
                    'range': cell_address,
                    'values': [[str(value)]]
                })
            
            # Batch update all cells at once
            if cells_to_update:
                batch_data = [{'range': cell['range'], 'values': cell['values']} for cell in cells_to_update]
                worksheet.batch_update(batch_data)
            
            logger.info(f"Updated Admin_Logs for student: {email}")
            # Clear cache after update
            cache_key = f"admin_logs_{self.admin_logs_spreadsheet_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Also clear the combined students cache so updates show up immediately
            if 'all_students' in self._cache:
                del self._cache['all_students']
                
            return True
            
        except ValueError as e:
            logger.warning(f"Validation error updating student data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating student data: {str(e)}", exc_info=True)
            raise
    
    def bulk_update_admin_logs(self, updates: List[Dict[str, Any]]) -> bool:
        """
        Bulk update Admin_Logs for multiple students.
        Optimized to use a single batch update call to avoid quota limits.
        """
        try:
            # 1. Read all headers and data with retry
            def _fetch_admin_data():
                worksheet = self._get_worksheet(self.admin_logs_spreadsheet_id, self.admin_logs_worksheet)
                return worksheet, worksheet.row_values(1), worksheet.get_all_records()
            
            worksheet, headers, records = self._retry_with_backoff(_fetch_admin_data)
            
            # Find email column index
            email_col_idx = -1
            email_header = None
            for i, h in enumerate(headers):
                if h.lower() in ['email', 'email address', 'e-mail']:
                    email_col_idx = i
                    email_header = h
                    break
            
            if email_col_idx == -1:
                # Try to find by content? No, risky.
                # Fallback to 'Email Address' if it exists in headers
                if 'Email Address' in headers:
                    email_header = 'Email Address'
                else:
                    raise ValueError("Email column not found in Admin_Logs")
            
            # Map email to row index (2-based)
            email_row_map = {}
            for i, record in enumerate(records):
                # record keys are headers
                email_val = str(record.get(email_header, '')).lower().strip()
                if email_val:
                    email_row_map[email_val] = i + 2
            
            # 2. Prepare updates
            cells_to_update = []
            
            for update in updates:
                email = str(update.get('email', '')).lower().strip()
                if not email:
                    continue
                    
                # If student not in map, maybe sync didn't run? 
                # For now, skip. Or we could initialize row here, but that complicates bulk.
                if email not in email_row_map:
                    logger.warning(f"Student {email} not found in Admin_Logs during bulk update. Skipping.")
                    continue
                
                row_idx = email_row_map[email]
                
                for field, value in update.items():
                    if field == 'email': continue
                    
                    if field not in headers:
                        logger.warning(f"Field {field} not in Admin_Logs headers, skipping.")
                        continue
                        
                    col_idx = headers.index(field) + 1
                    
                    if field == 'Attendance' and isinstance(value, dict):
                        value = format_attendance_to_string(value)
                    elif value is None:
                        value = ''
                        
                    cells_to_update.append({
                        'range': gspread.utils.rowcol_to_a1(row_idx, col_idx),
                        'values': [[str(value)]]
                    })
            
            # 3. Batch update with retry
            if cells_to_update:
                def _do_update():
                    worksheet.batch_update(cells_to_update)
                
                self._retry_with_backoff(_do_update)
                logger.info(f"Bulk updated {len(cells_to_update)} cells for {len(updates)} students")
            
            # Clear cache
            cache_key = f"admin_logs_{self.admin_logs_spreadsheet_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            if 'all_students' in self._cache:
                del self._cache['all_students']
                
            return True
            
        except Exception as e:
            logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
            raise

    def _get_or_create_worksheet(self, spreadsheet_id: str, worksheet_name: str) -> gspread.Worksheet:
        """Get worksheet by name, or create it if it doesn't exist."""
        cache_key = f"{spreadsheet_id}_{worksheet_name}"
        if cache_key in self._worksheets_cache:
            return self._worksheets_cache[cache_key]
            
        try:
            if spreadsheet_id in self._spreadsheets_cache:
                spreadsheet = self._spreadsheets_cache[spreadsheet_id]
            else:
                spreadsheet = self.client.open_by_key(spreadsheet_id)
                self._spreadsheets_cache[spreadsheet_id] = spreadsheet
                
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                self._worksheets_cache[cache_key] = worksheet
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Creating new worksheet '{worksheet_name}' in spreadsheet {spreadsheet_id}")
                # Create with headers row
                ws = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=10)
                ws.append_row(['id', 'date', 'topic', 'description'])
                self._worksheets_cache[cache_key] = ws
                return ws
        except Exception as e:
            logger.error(f"Error getting/creating worksheet: {str(e)}")
            raise

    def read_classes(self) -> List[Dict[str, Any]]:
        """Read all classes from the Classes worksheet."""
        cache_key = f"classes_{self.admin_logs_spreadsheet_id}"
        cached_data, _ = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"Returning cached classes: {len(cached_data)} records")
            return cached_data
            
        def _fetch_classes():
            self._throttle_request()
            # Use get_or_create to ensure we don't fall back to Sheet1
            worksheet = self._get_or_create_worksheet(self.admin_logs_spreadsheet_id, self.classes_worksheet)
            return worksheet.get_all_records()
            
        try:
            records = self._retry_with_backoff(_fetch_classes)
            logger.info(f"Read {len(records)} classes from sheet '{self.classes_worksheet}'")
            self._set_cached_data(cache_key, records)
            return records
        except Exception as e:
            logger.warning(f"Error reading classes: {str(e)}")
            return []

    def add_class(self, class_data: Dict[str, Any]) -> bool:
        """Add a new class to the Classes worksheet."""
        try:
            # Use get_or_create
            worksheet = self._get_or_create_worksheet(self.admin_logs_spreadsheet_id, self.classes_worksheet)
            
            # Get headers or initialize if empty (get_or_create initializes, but double check)
            try:
                headers = worksheet.row_values(1)
            except:
                headers = []
                
            if not headers:
                logger.info("Initializing Classes sheet headers")
                headers = ['id', 'date', 'topic', 'description']
                worksheet.update('A1', [headers])
            
            # Prepare row
            row = []
            for header in headers:
                row.append(class_data.get(header, ''))
            
            logger.info(f"Appending new class: {class_data.get('topic')}")
            worksheet.append_row(row)
            
            # Clear cache
            cache_key = f"classes_{self.admin_logs_spreadsheet_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info("Cleared classes cache")
                
            return True
        except Exception as e:
            logger.error(f"Error adding class: {str(e)}")
            raise

    def delete_class(self, class_id: str) -> bool:
        """Delete a class from the Classes worksheet."""
        try:
            worksheet = self._get_or_create_worksheet(self.admin_logs_spreadsheet_id, self.classes_worksheet)
            records = worksheet.get_all_records()
            
            row_idx = None
            for i, record in enumerate(records):
                if str(record.get('id', '')) == str(class_id):
                    row_idx = i + 2 # 1-based + header
                    break
            
            if row_idx:
                worksheet.delete_rows(row_idx)
                # Clear cache
                cache_key = f"classes_{self.admin_logs_spreadsheet_id}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting class: {str(e)}")
            raise

    def bulk_mark_attendance(self, class_id: str, present_emails: List[str]) -> bool:
        """Mark attendance for a specific class for all students."""
        try:
            # 1. Get all students (merged from all sources)
            # We use get_all_students to ensure we include students who are in Register/Survey 
            # but not yet in Admin_Logs
            students = self.get_all_students()
            
            updates = []
            
            for student in students:
                email = student.get('Email Address', '')
                if not email:
                    continue
                
                # Get current attendance (already parsed as dict by get_all_students)
                attendance = student.get('Attendance')
                if not isinstance(attendance, dict):
                    attendance = {}
                
                # Update status for this class
                is_present = email in present_emails
                # Use class_id (topic) as key
                attendance[class_id] = is_present
                
                updates.append({
                    'email': email,
                    'Attendance': attendance
                })
            
            # 2. Bulk update
            return self.bulk_update_admin_logs(updates)
            
        except Exception as e:
            logger.error(f"Error marking attendance: {str(e)}")
            raise

    def bulk_add_students_to_admin_logs(self, new_students_df: pd.DataFrame) -> bool:
        """Append new students to Admin_Logs worksheet."""
        try:
            worksheet = self._get_worksheet(self.admin_logs_spreadsheet_id, self.admin_logs_worksheet)
            
            # Get headers
            try:
                headers = worksheet.row_values(1)
            except:
                headers = []
            
            # If headers missing, initialize them
            total_labs = self._get_total_labs_count()
            if not headers:
                headers = ['Email Address', 'Name', 'Payment Screenshot', 'Attendance', 'Teacher Evaluation']
                for i in range(total_labs):
                    headers.append(f'Assignment {i+1} Grade')
                worksheet.update('A1', [headers])
            else:
                # Ensure Payment Screenshot column exists
                screenshot_header_exists = False
                for h in headers:
                    if 'payment' in str(h).lower() and 'screenshot' in str(h).lower():
                        screenshot_header_exists = True
                        break
                
                if not screenshot_header_exists:
                    logger.info("Adding 'Payment Screenshot' column to Admin_Logs (bulk sync)")
                    headers.append('Payment Screenshot')
                    worksheet.update('1:1', [headers])
            
            # Prepare rows
            rows_to_append = []
            
            # Default values
            default_vals = {
                'Attendance': '{}',
                'Teacher Evaluation': ''
            }
            # Add grades defaults
            for i in range(total_labs):
                default_vals[f'Assignment {i+1} Grade'] = ''
            
            for _, student in new_students_df.iterrows():
                row = []
                # Map student data to headers
                student_dict = student.to_dict()
                
                for header in headers:
                    val = ''
                    if header == 'Email Address':
                        val = student_dict.get('Email Address', '')
                    elif header == 'Name':
                        val = student_dict.get('Name', '')
                    elif 'payment' in str(header).lower() and 'screenshot' in str(header).lower():
                        # Sync screenshot from Register/Survey if available
                        val = student_dict.get('Add Payment Screenshot', '') or student_dict.get('Payment Screenshot', '')
                    elif header in default_vals:
                        val = default_vals[header]
                    elif header in student_dict:
                        val = student_dict[header]
                    
                    row.append(str(val) if pd.notna(val) else '')
                
                rows_to_append.append(row)
            
            if rows_to_append:
                worksheet.append_rows(rows_to_append)
                # Clear cache for Admin Logs
                cache_key = f"admin_logs_{self.admin_logs_spreadsheet_id}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                logger.info(f"Appended {len(rows_to_append)} new students to Admin_Logs")
            
            return True
        except Exception as e:
            logger.error(f"Error syncing students to Admin_Logs: {str(e)}")
            return False

    def sync_payment_screenshots(self, register_df: pd.DataFrame, admin_logs_df: pd.DataFrame):
        """
        Sync payment screenshots from Register (Form Responses) to Admin_Logs.
        This ensures existing students have their payment links backed up in Admin_Logs.
        """
        try:
            if register_df.empty: return
            
            # Find Register screenshot column
            # In merged_df (which is passed as register_df here from get_all_students), 
            # the column is standardized to 'Add Payment Screenshot' by merge_register_survey
            # However, we need to be robust against variations (spaces, case, etc.)
            reg_col = None
            
            # 1. Try exact match first
            if 'Add Payment Screenshot' in register_df.columns:
                reg_col = 'Add Payment Screenshot'
            else:
                # 2. Search for column containing keywords
                for c in register_df.columns:
                    c_lower = str(c).lower()
                    if 'payment' in c_lower and 'screenshot' in c_lower:
                        reg_col = c
                        break
            
            if not reg_col:
                logger.warning("Could not find Payment Screenshot column in Register data")
                # return # Don't return, check for Resume as well
            
            # --- Resume Sync Logic ---
            # Find Register resume column
            resume_col = None
            if 'Upload your Resume / CV (PDF preferred)' in register_df.columns:
                resume_col = 'Upload your Resume / CV (PDF preferred)'
            else:
                for c in register_df.columns:
                    c_lower = str(c).lower()
                    if 'resume' in c_lower and 'upload' in c_lower:
                        resume_col = c
                        break
            
            # Find Admin_Logs screenshot column
            admin_screenshot_col = 'Payment Screenshot'
            admin_screenshot_header_exists = False
            
            # Find Admin_Logs resume column
            admin_resume_col = 'Resume Link'
            admin_resume_header_exists = False
            
            # Check actual columns if admin_logs_df is not empty
            if not admin_logs_df.empty:
                for c in admin_logs_df.columns:
                    c_lower = str(c).lower()
                    if 'payment' in c_lower and 'screenshot' in c_lower:
                        admin_screenshot_col = c
                        admin_screenshot_header_exists = True
                    if 'resume' in c_lower and 'link' in c_lower:
                         admin_resume_col = c
                         admin_resume_header_exists = True
            
            # If headers don't exist and we have students in Admin Logs, add the columns
            if (not admin_screenshot_header_exists or not admin_resume_header_exists) and not admin_logs_df.empty:
                try:
                    worksheet = self._get_worksheet(self.admin_logs_spreadsheet_id, self.admin_logs_worksheet)
                    # Get current headers to be safe and avoid duplicates
                    current_headers = worksheet.row_values(1)
                    
                    # Check screenshot
                    if not admin_screenshot_header_exists:
                        header_found = False
                        for h in current_headers:
                            if 'payment' in str(h).lower() and 'screenshot' in str(h).lower():
                                header_found = True
                                admin_screenshot_col = h
                                admin_screenshot_header_exists = True
                                break
                        if not header_found:
                            logger.info("Adding 'Payment Screenshot' column to Admin_Logs (sync)")
                            # Check grid limits before adding
                            if len(current_headers) + 1 > worksheet.col_count:
                                 worksheet.resize(cols=len(current_headers) + 5) # Add buffer
                            worksheet.update_cell(1, len(current_headers) + 1, 'Payment Screenshot')
                            admin_screenshot_col = 'Payment Screenshot'
                            admin_screenshot_header_exists = True
                            current_headers.append('Payment Screenshot') # Update local list for next check

                    
                    # Check resume
                    if not admin_resume_header_exists:
                        header_found = False
                        for h in current_headers:
                            if 'resume' in str(h).lower() and 'link' in str(h).lower():
                                header_found = True
                                admin_resume_col = h
                                admin_resume_header_exists = True
                                break
                        if not header_found:
                            logger.info("Adding 'Resume Link' column to Admin_Logs (sync)")
                            # Check grid limits before adding
                            if len(current_headers) + 1 > worksheet.col_count:
                                 worksheet.resize(cols=len(current_headers) + 5) # Add buffer
                            worksheet.update_cell(1, len(current_headers) + 1, 'Resume Link')
                            admin_resume_col = 'Resume Link'
                            admin_resume_header_exists = True
                            current_headers.append('Resume Link') # Update local list for consistency

                    # Clear cache since we modified the sheet
                    cache_key = f"admin_logs_{self.admin_logs_spreadsheet_id}"
                    if cache_key in self._cache:
                        del self._cache[cache_key]
                except Exception as e:
                    logger.error(f"Failed to add columns to Admin_Logs: {e}")

            # Create a map of existing admin data
            admin_map = {} # email -> {'screenshot': ..., 'resume': ...}
            
            if not admin_logs_df.empty:
                 email_col = None
                 for c in admin_logs_df.columns:
                    if str(c).lower() in ['email', 'email address', 'e-mail']:
                        email_col = c
                        break
                 if email_col:
                    for _, row in admin_logs_df.iterrows():
                        e = str(row[email_col]).lower().strip()
                        if e:
                            admin_map[e] = {
                                'screenshot': str(row[admin_screenshot_col]) if admin_screenshot_header_exists and pd.notna(row.get(admin_screenshot_col)) else '',
                                'resume': str(row[admin_resume_col]) if admin_resume_header_exists and pd.notna(row.get(admin_resume_col)) else ''
                            }
            
            updates = []
            for _, row in register_df.iterrows():
                email = str(row.get('Email Address', '')).lower().strip()
                if not email: continue
                
                # Check screenshot update need
                reg_screenshot = ''
                if reg_col:
                    reg_screenshot = str(row.get(reg_col, '')).strip()
                    if reg_screenshot.lower() == 'nan': reg_screenshot = ''

                # Check resume update need
                reg_resume = ''
                if resume_col:
                    reg_resume = str(row.get(resume_col, '')).strip()
                    if reg_resume.lower() == 'nan': reg_resume = ''

                if not reg_screenshot and not reg_resume: continue

                # Check if we need to sync
                if email in admin_map:
                    current_data = admin_map[email]
                    student_updates = {'email': email}
                    has_update = False
                    
                    # Update Screenshot if missing in Admin but present in Register
                    if reg_screenshot and not current_data['screenshot'] and admin_screenshot_header_exists:
                        student_updates[admin_screenshot_col] = reg_screenshot
                        has_update = True
                    
                    # Update Resume if missing in Admin but present in Register
                    if reg_resume and not current_data['resume'] and admin_resume_header_exists:
                        student_updates[admin_resume_col] = reg_resume
                        has_update = True
                        
                    if has_update:
                        updates.append(student_updates)
            
            if updates:
                logger.info(f"Syncing {len(updates)} missing data (screenshots/resumes) to Admin_Logs")
                self.bulk_update_admin_logs(updates)
            
        except Exception as e:
            logger.error(f"Error syncing payment screenshots: {str(e)}")
            # Don't fail the whole request

