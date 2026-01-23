"""
Google Sheets Manager for reading and writing student operations data.
Handles 2 spreadsheets: Survey and Register.
Admin data is stored in Firestore (not Google Sheets).
"""
import os
import json
import pandas as pd
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Union

from google.oauth2 import service_account
import gspread
import gspread.exceptions

from core.logger import logger
from firestore.operations_cache import (
    get_metrics_from_firestore,
    get_students_list_from_firestore,
    sync_students_to_firestore,
)
from firestore.admin_data import (
    get_all_admin_students,
    create_admin_student,
    sync_payment_backups_to_firestore,
    get_all_classes,
    create_class,
    delete_class,
)
from sheets.sheets_utils import (
    merge_register_survey,
    merge_with_admin_logs,
    format_attendance,
    format_attendance_to_string,
    detect_new_students,
    normalize_dataframe,
    prepare_student_for_display,
)
from students.student_helpers import calculate_student_metrics


class GoogleSheetsManager:
    """Manages Google Sheets operations for student data."""
    
    def __init__(self):
        """Initialize Google Sheets client with service account credentials."""
        # Get spreadsheet IDs from environment
        self.survey_spreadsheet_id = os.getenv('GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID')
        self.register_spreadsheet_id = os.getenv('GOOGLE_SHEETS_REGISTER_SPREADSHEET_ID')
        
        # Get worksheet names (with defaults)
        self.survey_worksheet = os.getenv('GOOGLE_SHEETS_SURVEY_WORKSHEET', 'Form Responses 1')
        self.register_worksheet = os.getenv('GOOGLE_SHEETS_REGISTER_WORKSHEET', 'Form Responses 1')
        self.classes_worksheet = os.getenv('GOOGLE_SHEETS_CLASSES_WORKSHEET', 'Classes')
        
        # Validate required configuration
        if not self.survey_spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID environment variable is required")
        if not self.register_spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_REGISTER_SPREADSHEET_ID environment variable is required")
        
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
        
        # Lock for attendance marking per class_id to prevent duplicate concurrent requests
        self._attendance_locks = {}  # Dict[class_id, threading.Lock]
        self._attendance_lock_global = threading.Lock()  # Lock for managing attendance_locks dict
        
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
            
            # Use helper function that reads from Firestore
            from students.student_helpers import get_total_labs_count
            total_labs = get_total_labs_count()
            
            # Cache the result
            self._course_data_cache = total_labs
            self._course_data_cache_time = time.time()
            
            logger.info(f"Total labs across all modules: {total_labs}")
            return total_labs
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
    
    def get_admin_data_from_firestore(self) -> pd.DataFrame:
        """
        Read admin student data from Firestore and convert to DataFrame format.
        
        This replaces the old read_admin_logs() method. Converts Firestore format
        to DataFrame compatible with merge_with_admin_logs().
        
        Returns:
            DataFrame with columns: Email Address, Name, Attendance, Assignment N Grade, 
            Teacher Evaluation, Payment Screenshot, Resume Link
        """
        try:
            # Get all admin students from Firestore
            admin_students = get_all_admin_students()
            
            if not admin_students:
                logger.debug("No admin students found in Firestore")
                return pd.DataFrame()
            
            # Convert to list of dicts compatible with merge_with_admin_logs expectations
            rows = []
            for email, student_data in admin_students.items():
                row = {
                    'Email Address': email,
                }
                
                # Name
                if 'name' in student_data:
                    row['Name'] = student_data['name']
                
                # Attendance (convert dict to JSON string)
                attendance = student_data.get('attendance', {})
                if isinstance(attendance, dict):
                    import json
                    row['Attendance'] = json.dumps(attendance)
                else:
                    row['Attendance'] = str(attendance) if attendance else '{}'
                
                # Assignment grades (convert per-course/module structure to flat format)
                assignment_grades = student_data.get('assignmentGrades', {})
                if isinstance(assignment_grades, dict):
                    # Check if it's the new nested structure (course -> module -> lab)
                    is_new_format = False
                    for course_id, modules in assignment_grades.items():
                        if isinstance(modules, dict):
                            for module_id, labs in modules.items():
                                if isinstance(labs, dict):
                                    is_new_format = True
                                    break
                            if is_new_format:
                                break
                    
                    if is_new_format:
                        # New format: flatten per-course/module structure
                        assignment_num = 1
                        from firestore.course_data import get_course_data as get_course_data_from_firestore
                        from students.student_helpers import get_course_module_structure
                        course_data = get_course_data_from_firestore()
                        course_module_structure = get_course_module_structure(course_data)
                        
                        # Iterate through courses/modules in order
                        for course_id, modules in course_module_structure.items():
                            if course_id not in assignment_grades:
                                continue
                            course_grades = assignment_grades[course_id]
                            if not isinstance(course_grades, dict):
                                continue
                            
                            for module_id, lab_count in modules.items():
                                if module_id not in course_grades:
                                    # Skip missing modules, but still increment assignment_num
                                    assignment_num += lab_count
                                    continue
                                module_grades = course_grades[module_id]
                                if not isinstance(module_grades, dict):
                                    assignment_num += lab_count
                                    continue
                                
                                # Extract lab grades in order
                                for lab_num in range(1, lab_count + 1):
                                    lab_key = f"lab{lab_num}"
                                    grade_value = module_grades.get(lab_key, '')
                                    row[f"Assignment {assignment_num} Grade"] = str(grade_value) if grade_value else ''
                                    assignment_num += 1
                    else:
                        # Old format: already flat (Assignment N Grade)
                        for grade_key, grade_value in assignment_grades.items():
                            row[grade_key] = str(grade_value) if grade_value else ''
                
                # Teacher Evaluation (always include, even if empty)
                row['Teacher Evaluation'] = student_data.get('teacherEvaluation', '')
                
                # Payment Screenshot
                if 'paymentScreenshot' in student_data:
                    row['Payment Screenshot'] = student_data['paymentScreenshot']
                
                # Resume Link
                if 'resumeLink' in student_data:
                    row['Resume Link'] = student_data['resumeLink']
                
                rows.append(row)
            
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            df = normalize_dataframe(df)
            logger.info(f"Read {len(df)} admin students from Firestore")
            return df
            
        except Exception as e:
            logger.error(f"Error reading admin data from Firestore: {str(e)}", exc_info=True)
            # Return empty DataFrame on error
            return pd.DataFrame()
    
    def read_admin_logs(self) -> pd.DataFrame:
        """
        DEPRECATED: This method is kept for backward compatibility but now delegates to Firestore.
        Use get_admin_data_from_firestore() instead.
        """
        logger.warning("read_admin_logs() is deprecated, using Firestore instead")
        return self.get_admin_data_from_firestore()
    
    def get_all_students(
        self,
        use_firestore_cache: bool = True,
        force_refresh: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Merge all three spreadsheets and return complete student data.
        
        Steps:
        1. Merge Register + Survey (Register is primary, Survey data added)
        2. Merge result with Firestore admin data
        3. Return list of student dictionaries
        
        Uses locking to prevent concurrent reads and race conditions.
        """
        # 1. Try Firestore cache first (if enabled and not force-refresh)
        if use_firestore_cache and not force_refresh:
            try:
                fs_students = get_students_list_from_firestore()
                fs_metrics = get_metrics_from_firestore()
                if fs_students is not None and fs_metrics is not None:
                    logger.info(
                        f"Returning {len(fs_students)} students from Firestore cache"
                    )
                    return fs_students, fs_metrics
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(
                    f"Failed to read students from Firestore cache, falling back to Sheets: {e}"
                )

        # 2. Fallback to in-process cache + Sheets merge
        cache_key = "all_students"

        if force_refresh:
            logger.info("Force refresh requested: Clearing all student data caches")
            with self._read_lock:
                # Clear all related caches to ensure fresh data from all sheets
                keys_to_clear = [
                    cache_key,
                    f"survey_{self.survey_spreadsheet_id}",
                    f"register_{self.register_spreadsheet_id}",
                ]
                for key in keys_to_clear:
                    if key in self._cache:
                        del self._cache[key]
        
        with self._read_lock:
            cached_data, cache_time = self._get_cached_data(cache_key)
            if cached_data is not None and not force_refresh:
                logger.debug(
                    f"Returning cached student data (age: {time.time() - cache_time:.1f}s)"
                )
                # When using in-memory cache, recompute metrics cheaply from cached students
                metrics = calculate_student_metrics(cached_data)
                return cached_data, metrics
            
            # If another thread is already reading, wait for it
            if self._reading_students:
                logger.warning("Another request is already reading students, waiting...")
                # Wait a bit and check cache again
                self._read_lock.release()
                time.sleep(0.5)
                self._read_lock.acquire()
                cached_data, cache_time = self._get_cached_data(cache_key)
                if cached_data is not None:
                    logger.debug(
                        f"Returning cached student data after wait (age: {time.time() - cache_time:.1f}s)"
                    )
                    metrics = calculate_student_metrics(cached_data)
                    return cached_data, metrics
            
            # Mark that we're reading
            self._reading_students = True
        
        try:
            # Read Register and Survey spreadsheets (read-only)
            register_df = self.read_register_data()
            survey_df = self.read_survey_data()
            
            # Read admin data from Firestore
            admin_logs_df = self.get_admin_data_from_firestore()
            
            if register_df.empty and survey_df.empty:
                logger.warning(
                    "Both Register and Survey spreadsheets are empty, returning empty list"
                )
                return [], {}
            
            # Step 1: Merge Register + Survey
            merged_df = merge_register_survey(register_df, survey_df)
            
            # Step 2: Merge with Firestore admin data (with dynamic assignment grades)
            # Get total labs from course data to determine number of assignment grades needed
            total_labs = self._get_total_labs_count()
            
            # Check for new students and auto-create in Firestore
            new_student_emails = detect_new_students(merged_df, admin_logs_df)
            if new_student_emails:
                logger.info(f"Detected {len(new_student_emails)} new students. Creating in Firestore...")
                # Get existing admin students to avoid duplicates
                existing_admin = get_all_admin_students()
                for email in new_student_emails:
                    # Normalize and validate email
                    email_normalized = email.lower().strip() if email else ""
                    # Skip empty or invalid emails
                    if not email_normalized or len(email_normalized) < 3 or '@' not in email_normalized:
                        logger.warning(f"Skipping invalid email in new students list: {email}")
                        continue
                    
                    if email_normalized not in existing_admin:
                        # Get student data from merged_df for initial values
                        email_col = 'Email Address'
                        if email_col in merged_df.columns:
                            student_row = merged_df[merged_df[email_col] == email]
                            if not student_row.empty:
                                initial_data = {}
                                # Extract name if available
                                if 'Name' in student_row.columns:
                                    name_val = student_row.iloc[0].get('Name')
                                    if pd.notna(name_val):
                                        initial_data['name'] = str(name_val)
                                # Extract payment screenshot if available
                                if 'Add Payment Screenshot' in student_row.columns:
                                    screenshot_val = student_row.iloc[0].get('Add Payment Screenshot')
                                    if pd.notna(screenshot_val) and str(screenshot_val).strip():
                                        initial_data['paymentScreenshot'] = str(screenshot_val)
                                
                                # Extract Payment proved status if available (yes/no -> Paid/Unpaid)
                                payment_proved_cols = [c for c in student_row.columns if 'payment' in str(c).lower() and 'proved' in str(c).lower()]
                                if payment_proved_cols:
                                    payment_proved_val = str(student_row.iloc[0].get(payment_proved_cols[0], "")).strip().lower()
                                    if payment_proved_val and payment_proved_val != 'nan':
                                        if payment_proved_val == 'yes':
                                            initial_data['paymentStatus'] = 'Paid'
                                        elif payment_proved_val == 'no':
                                            initial_data['paymentStatus'] = 'Unpaid'
                                
                                # Extract resume link if available
                                resume_cols = [c for c in student_row.columns if 'resume' in str(c).lower()]
                                if resume_cols:
                                    resume_val = student_row.iloc[0].get(resume_cols[0])
                                    if pd.notna(resume_val) and str(resume_val).strip():
                                        initial_data['resumeLink'] = str(resume_val)
                                
                                success = create_admin_student(email, initial_data)
                                if not success:
                                    logger.warning(f"Failed to create admin student document for: {email}")
            
            # Step 3.5: Sync payment screenshots/resumes from Register to Firestore
            # This ensures that if a student registered via form, their payment/resume is backed up
            sync_payment_backups_to_firestore(register_df)
            
            # Re-read admin data after potential updates
            admin_logs_df = self.get_admin_data_from_firestore()
            
            final_df = merge_with_admin_logs(merged_df, admin_logs_df, total_labs=total_labs)

            # Deduplicate by normalized email so one student appears only once.
            # Instead of just dropping duplicates (which can lose data),
            # we coalesce rows for the same normalized email by taking the
            # last non-null value per column.
            if 'Email Address' in final_df.columns:
                final_df['__email_norm__'] = (
                    final_df['Email Address']
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

                def _coalesce_group(group: pd.DataFrame) -> pd.Series:
                    # For each column, take the last non-null value if available,
                    # otherwise leave it as NA.
                    return group.apply(
                        lambda col: col.dropna().iloc[-1] if not col.dropna().empty else pd.NA
                    )

                # Group by normalized email and coalesce columns
                final_df = (
                    final_df
                    .groupby('__email_norm__', as_index=False)
                    .apply(_coalesce_group)
                    .reset_index(drop=True)
                )

                # Drop helper column
                if '__email_norm__' in final_df.columns:
                    final_df = final_df.drop(columns=['__email_norm__'])
            
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

            # Compute metrics from merged student data
            metrics = calculate_student_metrics(students)

            # Attempt to sync to Firestore (non-fatal if it fails)
            if use_firestore_cache:
                try:
                    sync_ok = sync_students_to_firestore(students, metrics)
                    if not sync_ok:
                        logger.warning("Failed to sync students to Firestore cache")
                except Exception as sync_err:  # pragma: no cover - defensive
                    logger.error(
                        f"Unexpected error syncing students to Firestore: {sync_err}",
                        exc_info=True,
                    )

            # Cache the result
            with self._read_lock:
                self._set_cached_data(cache_key, students)
                self._reading_students = False
            
            logger.info(f"Successfully merged data for {len(students)} students")
            return students, metrics
            
        except Exception as e:
            # Release lock on error
            with self._read_lock:
                self._reading_students = False
            logger.error(f"Error getting all students: {str(e)}", exc_info=True)
            raise
    
    def get_student_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get specific student data by email address."""
        try:
            students, _metrics = self.get_all_students()
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
        Create new admin student document in Firestore.
        
        Args:
            email: Student email address
            student_data: Student data from Survey/Register (for reference)
            
        Returns:
            True if successful
        """
        try:
            # Prepare initial data from student_data if provided
            initial_data = {}
            
            # Extract name if available
            if student_data:
                name = (
                    student_data.get('Name') 
                    or student_data.get('Student Name') 
                    or student_data.get('Full Name') 
                    or (student_data.get('First Name', '') + ' ' + student_data.get('Last Name', '')).strip()
                )
                if name and name.strip():
                    initial_data['name'] = name.strip()
                
                # Extract payment screenshot if available
                payment_screenshot = (
                    student_data.get('Add Payment Screenshot')
                    or student_data.get('Payment Screenshot')
                    or student_data.get('paymentScreenshot')
                )
                if payment_screenshot and str(payment_screenshot).strip() and str(payment_screenshot).lower() != 'nan':
                    initial_data['paymentScreenshot'] = str(payment_screenshot).strip()
                
                # Extract Payment proved status if available (yes/no -> Paid/Unpaid)
                payment_proved_cols = [k for k in student_data.keys() if 'payment' in str(k).lower() and 'proved' in str(k).lower()]
                if payment_proved_cols:
                    payment_proved_val = str(student_data.get(payment_proved_cols[0], "")).strip().lower()
                    if payment_proved_val and payment_proved_val != 'nan':
                        if payment_proved_val == 'yes':
                            initial_data['paymentStatus'] = 'Paid'
                        elif payment_proved_val == 'no':
                            initial_data['paymentStatus'] = 'Unpaid'
                
                # Extract resume link if available
                resume_link = (
                    student_data.get('Resume Link')
                    or student_data.get('resumeLink')
                    or student_data.get('Upload your Resume / CV (PDF preferred)')
                )
                if resume_link and str(resume_link).strip() and str(resume_link).lower() != 'nan':
                    initial_data['resumeLink'] = str(resume_link).strip()
            
            # Create admin student in Firestore
            success = create_admin_student(email, initial_data)
            
            if success:
                logger.info(f"Created admin student document in Firestore: {email}")
            else:
                logger.warning(f"Failed to create admin student document: {email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating admin student document: {str(e)}", exc_info=True)
            raise
    
    def update_student_data(self, email: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific student's admin data in Firestore.
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
            
            # Use Firestore admin_data module
            from firestore.admin_data import update_admin_student, get_admin_student
            
            # Check if student exists, create if not
            existing = get_admin_student(email)
            if not existing:
                logger.info(f"Student {email} not in Firestore admin data, creating...")
                create_admin_student(email, {})
            
            # Update via Firestore
            success = update_admin_student(email, updates)
            
            if success:
                logger.info(f"Updated Firestore admin data for student: {email}")
                # Clear in-memory cache after update
                if 'all_students' in self._cache:
                    del self._cache['all_students']
                
                # Also clear Firestore operations cache to ensure fresh data on next read
                try:
                    from firestore.operations_cache import clear_firestore_cache
                    clear_firestore_cache()
                    logger.debug("Cleared Firestore operations cache after student update")
                except Exception as cache_err:
                    logger.warning(f"Failed to clear Firestore cache: {cache_err}")
            
            return success
            
        except ValueError as e:
            logger.warning(f"Validation error updating student data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating student data: {str(e)}", exc_info=True)
            raise
    
    def bulk_update_admin_logs(self, updates: List[Dict[str, Any]]) -> Union[bool, Dict[str, Any]]:
        """
        Bulk update admin data in Firestore for multiple students.
        """
        try:
            from firestore.admin_data import bulk_update_admin_students
            
            # Use Firestore bulk update
            result = bulk_update_admin_students(updates)
            
            success = result.get('success', False)
            if success:
                logger.info(
                    f"Bulk updated {result['updated']} students in Firestore "
                    f"({result['failed']} failed, {result['skipped']} skipped)"
                )
            else:
                logger.warning(
                    f"Bulk update had failures: {result['updated']} updated, "
                    f"{result['failed']} failed, {result['skipped']} skipped"
                )
            
            # Clear cache
            if 'all_students' in self._cache:
                del self._cache['all_students']
            
            return success
            
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
        """Read all classes from Firestore."""
        try:
            classes = get_all_classes()
            # Remove internal _id field for API compatibility
            for cls in classes:
                if '_id' in cls:
                    del cls['_id']
            logger.info(f"Read {len(classes)} classes from Firestore")
            return classes
        except Exception as e:
            logger.warning(f"Error reading classes: {str(e)}")
            return []

    def add_class(self, class_data: Dict[str, Any]) -> bool:
        """Add a new class to Firestore."""
        try:
            success = create_class(class_data)
            if success:
                logger.info(f"Added class: {class_data.get('topic')}")
            return success
        except Exception as e:
            logger.error(f"Error adding class: {str(e)}")
            raise

    def delete_class(self, class_id: str) -> bool:
        """Delete a class from Firestore."""
        try:
            success = delete_class(class_id)
            if success:
                logger.info(f"Deleted class: {class_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting class: {str(e)}")
            raise

    def bulk_mark_attendance(self, class_id: str, present_emails: List[str]) -> Dict[str, Any]:
        """
        Mark attendance for a specific class for all students.
        
        Uses locking to prevent concurrent duplicate requests and idempotency checks
        to skip unnecessary updates.
        
        Returns:
            Dict with keys:
            - 'success': bool - True if operation succeeded or was skipped
            - 'status': str - 'completed', 'duplicate_request', 'no_changes', or 'failed'
            - 'updated': int - Number of students updated
            - 'skipped': int - Number of students skipped (already correct)
            - 'message': str - Human-readable message
        """
        # Get or create lock for this specific class_id
        with self._attendance_lock_global:
            if class_id not in self._attendance_locks:
                self._attendance_locks[class_id] = threading.Lock()
            class_lock = self._attendance_locks[class_id]
        
        # Acquire lock for this class to prevent concurrent requests
        if not class_lock.acquire(blocking=False):
            logger.warning(f"Attendance marking already in progress for class {class_id}, rejecting duplicate request")
            return {
                'success': False,
                'status': 'duplicate_request',
                'updated': 0,
                'skipped': 0,
                'message': 'Attendance marking already in progress for this class'
            }
        
        try:
            logger.info(f"Marking attendance for class {class_id}, {len(present_emails)} present students")
            
            # Normalize present_emails for comparison
            present_emails_set = {email.lower().strip() for email in present_emails if email}
            
            # 1. Try to use cached students data first (much faster)
            # Check if we have recent cached data
            cache_key = 'all_students'
            cached_data = self._cache.get(cache_key)
            cache_time = self._cache.get(f'{cache_key}_time', 0)
            current_time = time.time()
            
            if cached_data and (current_time - cache_time) < self._cache_ttl:
                logger.debug(f"Using cached students data for attendance marking (age: {current_time - cache_time:.1f}s)")
                students = cached_data
            else:
                # Fallback to fetching if cache is stale or missing
                logger.debug("Cache miss or stale, fetching fresh students data")
                students, _metrics = self.get_all_students()
            
            logger.info(f"Found {len(students)} total students to check")
            
            if not students:
                logger.warning("No students found to mark attendance")
                return {
                    'success': False,
                    'status': 'failed',
                    'updated': 0,
                    'skipped': 0,
                    'message': 'No students found to mark attendance'
                }
            
            # 2. Build updates with idempotency check - only update if attendance actually changed
            updates = []
            skipped_count = 0
            
            for student in students:
                email = student.get('Email Address', '')
                if not email:
                    logger.debug("Skipping student with no email")
                    continue
                
                email_normalized = email.lower().strip()
                
                # Get current attendance (already parsed as dict by get_all_students)
                attendance = student.get('Attendance')
                if not isinstance(attendance, dict):
                    attendance = {}
                
                # Check current status
                current_status = attendance.get(class_id, False)
                desired_status = email_normalized in present_emails_set
                
                # Idempotency check: skip if already set correctly
                if current_status == desired_status:
                    skipped_count += 1
                    continue
                
                # Update status for this class
                attendance[class_id] = desired_status
                
                updates.append({
                    'email': email,
                    'Attendance': attendance
                })
            
            # 3. If no updates needed, return early (but still clear cache to ensure fresh data)
            if not updates:
                logger.info(
                    f"Attendance already set correctly for class {class_id}. "
                    f"Skipped {skipped_count} students, no updates needed"
                )
                
                # Still clear cache to ensure we have the latest data (in case it was stale)
                if 'all_students' in self._cache:
                    del self._cache['all_students']
                
                return {
                    'success': True,
                    'status': 'no_changes',
                    'updated': 0,
                    'skipped': skipped_count,
                    'message': f'Attendance already set correctly for all {skipped_count} students'
                }
            
            logger.info(
                f"Prepared {len(updates)} attendance updates "
                f"({skipped_count} already correct, skipped)"
            )
            
            # 4. Bulk update via Firestore
            result = self.bulk_update_admin_logs(updates)
            
            # Handle both boolean and dict return types
            if isinstance(result, dict):
                success = result.get('success', False)
                updated_count = result.get('updated', 0)
                failed_count = result.get('failed', 0)
            else:
                success = result
                updated_count = len(updates) if success else 0
                failed_count = 0 if success else len(updates)
            
            if success:
                logger.info(
                    f"Successfully marked attendance for class {class_id}: "
                    f"{updated_count} updated, {skipped_count} already correct"
                )
                
                # Invalidate caches to ensure fresh data on next read
                if 'all_students' in self._cache:
                    del self._cache['all_students']
                
                # Also clear Firestore operations cache
                try:
                    from firestore.operations_cache import clear_firestore_cache
                    clear_firestore_cache()
                except Exception as cache_err:
                    logger.warning(f"Failed to clear Firestore cache: {cache_err}")
                
                return {
                    'success': True,
                    'status': 'completed',
                    'updated': updated_count,
                    'skipped': skipped_count,
                    'failed': failed_count,
                    'message': f'Successfully updated attendance for {updated_count} students'
                }
            else:
                logger.error(f"Failed to mark attendance for class {class_id}: {failed_count} failed")
                return {
                    'success': False,
                    'status': 'failed',
                    'updated': updated_count,
                    'skipped': skipped_count,
                    'failed': failed_count,
                    'message': f'Failed to update attendance: {failed_count} students failed'
                }
            
        except Exception as e:
            logger.error(f"Error marking attendance for class {class_id}: {str(e)}", exc_info=True)
            raise
        finally:
            # Always release the lock
            class_lock.release()

    def bulk_add_students_to_admin_logs(self, new_students_df: pd.DataFrame) -> bool:
        """
        Bulk create new admin student documents in Firestore.
        """
        try:
            if new_students_df.empty:
                return True
            
            # Get existing admin students to avoid duplicates
            existing_admin = get_all_admin_students()
            
            # Prepare updates for Firestore
            students_to_create = []
            
            for _, student_row in new_students_df.iterrows():
                student_dict = student_row.to_dict()
                email = str(student_dict.get('Email Address', '')).strip()
                
                if not email or email.lower() == 'nan':
                    continue
                
                email_normalized = email.lower().strip()
                
                # Skip if already exists
                if email_normalized in existing_admin:
                    continue
                
                # Prepare initial data
                initial_data = {}
                
                # Extract name
                name = (
                    student_dict.get('Name')
                    or student_dict.get('Student Name')
                    or student_dict.get('Full Name')
                )
                if name and pd.notna(name) and str(name).strip():
                    initial_data['name'] = str(name).strip()
                
                # Extract payment screenshot
                payment_screenshot = (
                    student_dict.get('Add Payment Screenshot')
                    or student_dict.get('Payment Screenshot')
                    or student_dict.get('paymentScreenshot')
                )
                if payment_screenshot and pd.notna(payment_screenshot) and str(payment_screenshot).strip() and str(payment_screenshot).lower() != 'nan':
                    initial_data['paymentScreenshot'] = str(payment_screenshot).strip()
                
                # Extract Payment proved status if available (yes/no -> Paid/Unpaid)
                payment_proved_cols = [k for k in student_dict.keys() if 'payment' in str(k).lower() and 'proved' in str(k).lower()]
                if payment_proved_cols:
                    payment_proved_val = str(student_dict.get(payment_proved_cols[0], "")).strip().lower()
                    if payment_proved_val and payment_proved_val != 'nan':
                        if payment_proved_val == 'yes':
                            initial_data['paymentStatus'] = 'Paid'
                        elif payment_proved_val == 'no':
                            initial_data['paymentStatus'] = 'Unpaid'
                
                # Extract resume link
                resume_link = (
                    student_dict.get('Resume Link')
                    or student_dict.get('resumeLink')
                    or student_dict.get('Upload your Resume / CV (PDF preferred)')
                )
                if resume_link and pd.notna(resume_link) and str(resume_link).strip() and str(resume_link).lower() != 'nan':
                    initial_data['resumeLink'] = str(resume_link).strip()
                
                # Create student in Firestore
                success = create_admin_student(email, initial_data)
                if success:
                    students_to_create.append(email)
                    # Update existing_admin to avoid duplicates in same batch
                    existing_admin[email_normalized] = {}
            
            if students_to_create:
                logger.info(f"Created {len(students_to_create)} new admin student documents in Firestore")
                # Clear cache
                if 'all_students' in self._cache:
                    del self._cache['all_students']
            
            return True
        except Exception as e:
            logger.error(f"Error creating admin student documents in Firestore: {str(e)}", exc_info=True)
            return False

    def sync_payment_screenshots(self, register_df: pd.DataFrame):
        """
        Sync payment screenshots and resume links from Register to Firestore admin_students.
        This ensures existing students have their payment/resume data backed up in Firestore.
        """
        try:
            if register_df.empty:
                return
            
            # Use the existing Firestore sync function
            # This function already handles the logic of syncing payment/resume from Register to Firestore
            success = sync_payment_backups_to_firestore(register_df)
            
            if success:
                logger.info("Synced payment screenshots and resume links to Firestore")
                # Clear cache
                if 'all_students' in self._cache:
                    del self._cache['all_students']
            else:
                logger.warning("Failed to sync payment screenshots/resumes to Firestore")
            
        except Exception as e:
            logger.error(f"Error syncing payment screenshots to Firestore: {str(e)}", exc_info=True)
            # Don't fail the whole request
    
    def invalidate_course_data_cache(self):
        """
        Invalidate course data cache (lab count cache).
        Call this when modules are added/updated/deleted.
        """
        self._course_data_cache = None
        self._course_data_cache_time = 0
        logger.debug("Course data cache invalidated")
    
    def invalidate_all_caches(self):
        """
        Invalidate all caches (course data, student data, sheets data).
        Call this when course structure changes significantly.
        """
        # Clear course data cache
        self.invalidate_course_data_cache()
        
        # Clear student data cache
        if 'all_students' in self._cache:
            del self._cache['all_students']
        
        # Clear sheet-specific caches
        keys_to_clear = [
            f"survey_{self.survey_spreadsheet_id}",
            f"register_{self.register_spreadsheet_id}",
        ]
        for key in keys_to_clear:
            if key in self._cache:
                del self._cache[key]
        
        logger.info("All caches invalidated")

