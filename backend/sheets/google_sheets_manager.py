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
from firestore.admin_data import (
    get_all_classes,
    create_class,
    delete_class,
    get_all_users_admin_data,
    update_user_admin_data_by_email,
    bulk_update_users_admin_data,
    sync_payment_backups_to_firestore,
)
from sheets.sheets_utils import (
    format_attendance,
    format_attendance_to_string,
    normalize_dataframe,
    prepare_student_for_display,
)


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
        to DataFrame for admin data operations.
        
        Returns:
            DataFrame with columns: Email Address, Name, Attendance, Assignment N Grade, 
            Teacher Evaluation, Payment Screenshot, Resume Link
        """
        try:
            # Get all users with admin data from Firestore
            users = get_all_users_admin_data()
            
            if not users:
                logger.debug("No users found in Firestore")
                return pd.DataFrame()
            
            # Convert to list of dicts for DataFrame conversion
            rows = []
            for user_data in users:
                email = user_data.get('email', '')
                if not email:
                    continue
                row = {
                    'Email Address': email,
                }
                
                # Name
                if 'name' in user_data:
                    row['Name'] = user_data['name']
                
                # Attendance (convert dict to JSON string)
                attendance = user_data.get('attendance', {})
                if isinstance(attendance, dict):
                    import json
                    row['Attendance'] = json.dumps(attendance)
                else:
                    row['Attendance'] = str(attendance) if attendance else '{}'
                
                # Assignment grades (convert per-course/module structure to flat format)
                assignment_grades = user_data.get('assignmentGrades', {})
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
                row['Teacher Evaluation'] = user_data.get('teacherEvaluation', '')
                
                # Payment Status (admin-set, takes priority)
                if 'paymentStatus' in user_data:
                    row['Payment Status'] = user_data['paymentStatus']
                
                # Payment Comment
                if 'paymentComment' in user_data:
                    row['Payment Comment'] = user_data['paymentComment']
                
                # Payment Screenshot
                if 'paymentScreenshot' in user_data:
                    row['Payment Screenshot'] = user_data['paymentScreenshot']
                
                # Resume Link
                if 'resumeLink' in user_data:
                    row['Resume Link'] = user_data['resumeLink']
                
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
    
    def get_register_students(
        self,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get Register form data only (no merging).
        
        Returns:
            List of student dictionaries from Register form
        """
        cache_key = f"register_students_{self.register_spreadsheet_id}"
        
        if force_refresh:
            with self._read_lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                if f"register_{self.register_spreadsheet_id}" in self._cache:
                    del self._cache[f"register_{self.register_spreadsheet_id}"]
        
        with self._read_lock:
            cached_data, cache_time = self._get_cached_data(cache_key)
            if cached_data is not None and not force_refresh:
                logger.debug(f"Returning cached Register data (age: {time.time() - cache_time:.1f}s)")
                return cached_data
        
        try:
            # Read Register spreadsheet
            register_df = self.read_register_data()
            
            if register_df.empty:
                logger.debug("Register spreadsheet is empty")
                return []
            
            # Sort by Name (if available) or Email Address
            if 'Name' in register_df.columns:
                register_df = register_df.sort_values('Name', na_position='last')
            elif 'Email Address' in register_df.columns:
                register_df = register_df.sort_values('Email Address', na_position='last')
            
            # Convert to list of dictionaries
            students = []
            for _, row in register_df.iterrows():
                student_dict = prepare_student_for_display(row)
                students.append(student_dict)
            
            # Cache the result
            with self._read_lock:
                self._set_cached_data(cache_key, students)
            
            logger.info(f"Successfully loaded {len(students)} Register form entries")
            return students
            
        except Exception as e:
            logger.error(f"Error getting Register students: {str(e)}", exc_info=True)
            raise
    
    def get_survey_students(
        self,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get Survey form data only (no merging).
        
        Returns:
            List of student dictionaries from Survey form
        """
        cache_key = f"survey_students_{self.survey_spreadsheet_id}"
        
        if force_refresh:
            with self._read_lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                if f"survey_{self.survey_spreadsheet_id}" in self._cache:
                    del self._cache[f"survey_{self.survey_spreadsheet_id}"]
        
        with self._read_lock:
            cached_data, cache_time = self._get_cached_data(cache_key)
            if cached_data is not None and not force_refresh:
                logger.debug(f"Returning cached Survey data (age: {time.time() - cache_time:.1f}s)")
                return cached_data
        
        try:
            # Read Survey spreadsheet
            survey_df = self.read_survey_data()
            
            if survey_df.empty:
                logger.debug("Survey spreadsheet is empty")
                return []
            
            # Sort by Name (if available) or Email Address
            if 'Name' in survey_df.columns:
                survey_df = survey_df.sort_values('Name', na_position='last')
            elif 'Email Address' in survey_df.columns:
                survey_df = survey_df.sort_values('Email Address', na_position='last')
            
            # Convert to list of dictionaries
            students = []
            for _, row in survey_df.iterrows():
                student_dict = prepare_student_for_display(row)
                students.append(student_dict)
            
            # Cache the result
            with self._read_lock:
                self._set_cached_data(cache_key, students)
            
            logger.info(f"Successfully loaded {len(students)} Survey form entries")
            return students
            
        except Exception as e:
            logger.error(f"Error getting Survey students: {str(e)}", exc_info=True)
            raise
    
    def get_all_students(
        self,
        use_firestore_cache: bool = True,
        force_refresh: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        DEPRECATED: This method is deprecated. Use get_register_students() or get_survey_students() instead.
        
        Returns empty list for backward compatibility.
        """
        logger.warning("get_all_students() is deprecated. Use get_register_students() or get_survey_students() instead.")
        return [], {}
    
    def get_student_by_email(self, email: str, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get specific student data by email address from Register or Survey.
        
        Args:
            email: Email address to search for
            source: 'register', 'survey', or None to search both (default: None)
        
        Returns:
            Student dictionary if found, None otherwise
        """
        try:
            email_lower = email.lower().strip()
            
            if source == 'register':
                students = self.get_register_students()
            elif source == 'survey':
                students = self.get_survey_students()
            else:
                # Search both if source not specified
                register_students = self.get_register_students()
                for student in register_students:
                    student_email = None
                    for key in ['Email Address', 'Email', 'email', 'email_address']:
                        if key in student and student[key]:
                            student_email = str(student[key]).lower().strip()
                            break
                    if student_email == email_lower:
                        return student
                
                survey_students = self.get_survey_students()
                for student in survey_students:
                    student_email = None
                    for key in ['Email Address', 'Email', 'email', 'email_address']:
                        if key in student and student[key]:
                            student_email = str(student[key]).lower().strip()
                            break
                    if student_email == email_lower:
                        return student
                return None
            
            for student in students:
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
        Initialize admin fields for a Firebase user (if user exists).
        
        Args:
            email: Student email address
            student_data: Student data from Survey/Register (for reference)
            
        Returns:
            True if successful (or user doesn't exist - not an error)
        """
        try:
            # Find Firebase user by email
            from firestore.admin_data import _find_user_by_email, get_user_admin_data, _ensure_user_admin_fields
            uid = _find_user_by_email(email)
            
            if not uid:
                logger.debug(f"No Firebase user found for email: {email}")
                return True  # Not an error - user might not be registered yet
            
            # Ensure admin fields are initialized
            _ensure_user_admin_fields(uid)
            
            # Get existing user data
            user_data = get_user_admin_data(uid)
            if not user_data:
                logger.debug(f"User {uid} not found in Firestore")
                return True
            
            # Prepare updates from student_data if provided
            updates: Dict[str, Any] = {}
            
            # Extract name if available and not already set
            if student_data and not user_data.get('name'):
                name = (
                    student_data.get('Name') 
                    or student_data.get('Student Name') 
                    or student_data.get('Full Name') 
                    or (student_data.get('First Name', '') + ' ' + student_data.get('Last Name', '')).strip()
                )
                if name and name.strip():
                    updates['name'] = name.strip()
            
            # Extract payment screenshot if available and not already set
            if student_data and not user_data.get('paymentScreenshot'):
                payment_screenshot = (
                    student_data.get('Add Payment Screenshot')
                    or student_data.get('Payment Screenshot')
                    or student_data.get('paymentScreenshot')
                )
                if payment_screenshot and str(payment_screenshot).strip() and str(payment_screenshot).lower() != 'nan':
                    updates['paymentScreenshot'] = str(payment_screenshot).strip()
            
            # Extract Payment proved status if available and not already set
            if student_data and not user_data.get('paymentStatus'):
                payment_proved_cols = [k for k in student_data.keys() if 'payment' in str(k).lower() and 'proved' in str(k).lower()]
                if payment_proved_cols:
                    payment_proved_val = str(student_data.get(payment_proved_cols[0], "")).strip().lower()
                    if payment_proved_val and payment_proved_val != 'nan':
                        if payment_proved_val == 'yes':
                            updates['paymentStatus'] = 'Paid'
                        elif payment_proved_val == 'no':
                            updates['paymentStatus'] = 'Unpaid'
            
            # Extract resume link if available and not already set
            if student_data and not user_data.get('resumeLink'):
                resume_link = (
                    student_data.get('Resume Link')
                    or student_data.get('resumeLink')
                    or student_data.get('Upload your Resume / CV (PDF preferred)')
                )
                if resume_link and str(resume_link).strip() and str(resume_link).lower() != 'nan':
                    updates['resumeLink'] = str(resume_link).strip()
            
            # Update if there are changes
            if updates:
                from firestore.admin_data import update_user_admin_data
                success = update_user_admin_data(uid, updates)
                if success:
                    logger.info(f"Initialized admin fields for user: {email}")
                else:
                    logger.warning(f"Failed to initialize admin fields for user: {email}")
                return success
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing admin fields for user: {str(e)}", exc_info=True)
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
            from firestore.admin_data import update_user_admin_data_by_email
            
            # Update via Firestore (will find user by email)
            success = update_user_admin_data_by_email(email, updates)
            
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
            from firestore.admin_data import bulk_update_users_admin_data
            
            # Use Firestore bulk update (supports both uid and email in updates)
            result = bulk_update_users_admin_data(updates)
            
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
            
            # 1. Fetch all Firebase users with admin data
            users = get_all_users_admin_data()
            
            logger.info(f"Found {len(users)} total users to check")
            
            if not users:
                logger.warning("No users found to mark attendance")
                return {
                    'success': False,
                    'status': 'failed',
                    'updated': 0,
                    'skipped': 0,
                    'message': 'No users found to mark attendance'
                }
            
            # 2. Build updates with idempotency check - only update if attendance actually changed
            updates = []
            skipped_count = 0
            
            for user in users:
                email = user.get('email', '')
                if not email:
                    logger.debug("Skipping user with no email")
                    continue
                
                email_normalized = email.lower().strip()
                
                # Get current attendance
                attendance = user.get('attendance', {})
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
        Bulk initialize admin fields for Firebase users from new students DataFrame.
        """
        try:
            if new_students_df.empty:
                return True
            
            # Get existing users to check
            existing_users = get_all_users_admin_data()
            existing_emails = {user.get('email', '').lower() for user in existing_users if user.get('email')}
            
            # Prepare updates for Firestore
            updates = []
            
            for _, student_row in new_students_df.iterrows():
                student_dict = student_row.to_dict()
                email = str(student_dict.get('Email Address', '')).strip()
                
                if not email or email.lower() == 'nan':
                    continue
                
                email_normalized = email.lower().strip()
                
                # Find Firebase user by email
                from firestore.admin_data import _find_user_by_email
                uid = _find_user_by_email(email_normalized)
                
                if not uid:
                    logger.debug(f"No Firebase user found for email: {email}")
                    continue
                
                # Get existing user data
                from firestore.admin_data import get_user_admin_data
                user_data = get_user_admin_data(uid)
                if not user_data:
                    logger.debug(f"User {uid} not found in Firestore")
                    continue
                
                # Prepare update data (only set if not already set)
                update_data: Dict[str, Any] = {'uid': uid}
                
                # Extract name if not already set
                if not user_data.get('name'):
                    name = (
                        student_dict.get('Name')
                        or student_dict.get('Student Name')
                        or student_dict.get('Full Name')
                    )
                    if name and pd.notna(name) and str(name).strip():
                        update_data['name'] = str(name).strip()
                
                # Extract payment screenshot if not already set
                if not user_data.get('paymentScreenshot'):
                    payment_screenshot = (
                        student_dict.get('Add Payment Screenshot')
                        or student_dict.get('Payment Screenshot')
                        or student_dict.get('paymentScreenshot')
                    )
                    if payment_screenshot and pd.notna(payment_screenshot) and str(payment_screenshot).strip() and str(payment_screenshot).lower() != 'nan':
                        update_data['paymentScreenshot'] = str(payment_screenshot).strip()
                
                # Extract Payment proved status if available and not already set
                if not user_data.get('paymentStatus'):
                    payment_proved_cols = [k for k in student_dict.keys() if 'payment' in str(k).lower() and 'proved' in str(k).lower()]
                    if payment_proved_cols:
                        payment_proved_val = str(student_dict.get(payment_proved_cols[0], "")).strip().lower()
                        if payment_proved_val and payment_proved_val != 'nan':
                            if payment_proved_val == 'yes':
                                update_data['paymentStatus'] = 'Paid'
                            elif payment_proved_val == 'no':
                                update_data['paymentStatus'] = 'Unpaid'
                
                # Extract resume link if not already set
                if not user_data.get('resumeLink'):
                    resume_link = (
                        student_dict.get('Resume Link')
                        or student_dict.get('resumeLink')
                        or student_dict.get('Upload your Resume / CV (PDF preferred)')
                    )
                    if resume_link and pd.notna(resume_link) and str(resume_link).strip() and str(resume_link).lower() != 'nan':
                        update_data['resumeLink'] = str(resume_link).strip()
                
                # Only add if there are updates
                if len(update_data) > 1:  # More than just 'uid'
                    updates.append(update_data)
            
            if updates:
                result = bulk_update_users_admin_data(updates)
                logger.info(f"Initialized admin fields for {len(updates)} users in Firestore")
                # Clear cache
                if 'all_students' in self._cache:
                    del self._cache['all_students']
            
            return True
        except Exception as e:
            logger.error(f"Error initializing admin fields for users: {str(e)}", exc_info=True)
            return False

    def sync_payment_screenshots(self, register_df: pd.DataFrame):
        """
        Sync payment screenshots and resume links from Register to Firestore users collection.
        This ensures existing users have their payment/resume data backed up in Firestore.
        """
        try:
            if register_df.empty:
                return
            
            # Use the existing Firestore sync function
            # This function already handles the logic of syncing payment/resume from Register to Firestore users
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

