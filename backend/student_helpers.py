"""
Helper functions for student operations endpoints.
Extracted common patterns to reduce code duplication.
"""
from typing import Dict, List, Any, Optional, Tuple
import json
from logger import logger


def get_total_labs_count(drive_client) -> int:
    """
    Get total number of labs across all modules from course data.
    
    Args:
        drive_client: GoogleDriveClient instance (can be None)
        
    Returns:
        Total number of labs (defaults to 2 if course data unavailable)
    """
    try:
        if drive_client:
            course_data = drive_client.get_course_data()
            if course_data and 'modules' in course_data:
                total_labs = sum(module.get('labCount', 1) for module in course_data['modules'])
                return total_labs
    except Exception as e:
        logger.warning(f"Could not get course data for assignment grades: {str(e)}")
    
    return 2  # Default


def get_allowed_assignment_fields(total_labs: int) -> List[str]:
    """
    Build list of allowed assignment grade field names.
    
    Args:
        total_labs: Total number of labs/assignments
        
    Returns:
        List of allowed field names (Name, Attendance, Teacher Evaluation, Assignment grades)
    """
    allowed_fields = ['Name', 'Student Name', 'Attendance', 'Teacher Evaluation']
    for i in range(total_labs):
        allowed_fields.append(f'Assignment {i+1} Grade')
    return allowed_fields


def get_student_email(student: Dict[str, Any]) -> str:
    """
    Extract email address from student dictionary (handles multiple field name variations).
    
    Args:
        student: Student dictionary
        
    Returns:
        Email address string (empty if not found)
    """
    for key in ['Email Address', 'Email', 'email', 'email_address']:
        if key in student and student[key]:
            return str(student[key]).strip()
    return ''


def get_student_name(student: Dict[str, Any]) -> str:
    """
    Extract name from student dictionary.
    
    Args:
        student: Student dictionary
        
    Returns:
        Name string (defaults to 'Unknown' if not found)
    """
    return student.get('Name', 'Unknown')


def get_student_resume_link(student: Dict[str, Any]) -> str:
    """
    Extract resume link from student dictionary (handles multiple field name variations).
    
    Args:
        student: Student dictionary
        
    Returns:
        Resume link string (empty if not found)
    """
    resume_link = (
        student.get('Resume Link', '') or 
        student.get('Resume', '') or 
        student.get('Upload your Resume / CV (PDF preferred)', '') or
        student.get('Upload your Resume / CV (PDF preferred) ', '')
    )
    return resume_link or ''


def has_resume(resume_link: str) -> bool:
    """
    Check if a resume link is valid (not empty or N/A).
    
    Args:
        resume_link: Resume link string
        
    Returns:
        True if resume link is valid, False otherwise
    """
    if not resume_link:
        return False
    resume_link = resume_link.strip()
    return resume_link.lower() != 'n/a' and len(resume_link) > 0


def parse_attendance(attendance: Any) -> Dict[str, Any]:
    """
    Parse attendance data (can be dict, JSON string, or None).
    
    Args:
        attendance: Attendance data (dict, string, or None)
        
    Returns:
        Parsed attendance dictionary (empty dict if invalid/None)
    """
    if isinstance(attendance, dict):
        return attendance
    elif isinstance(attendance, str):
        try:
            return json.loads(attendance) if attendance else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def calculate_student_metrics(students: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate metrics from student list (total, paid count, resume count, onboarding %).
    
    Args:
        students: List of student dictionaries
        
    Returns:
        Dictionary with metrics: total_students, paid_count, unpaid_count, 
        has_resume_count, onboarding_percentage
    """
    total_students = len(students)
    paid_count = 0
    has_resume_count = 0
    
    for student in students:
        # Count paid students
        payment_status = student.get('Payment Status', '').lower()
        if payment_status == 'paid':
            paid_count += 1
        
        # Count students with resume
        resume_link = get_student_resume_link(student)
        if has_resume(resume_link):
            has_resume_count += 1
    
    onboarding_percentage = (has_resume_count / total_students * 100) if total_students > 0 else 0
    
    return {
        'total_students': total_students,
        'paid_count': paid_count,
        'unpaid_count': total_students - paid_count,
        'has_resume_count': has_resume_count,
        'onboarding_percentage': round(onboarding_percentage, 2)
    }


def calculate_student_status(students: List[Dict[str, Any]], total_labs: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculate status for students (missing payment, resume, attendance, grades).
    
    Args:
        students: List of student dictionaries
        total_labs: Total number of labs/assignments
        
    Returns:
        Dictionary with status lists: missing_payment, missing_resume, 
        missing_attendance, missing_grades
    """
    missing_payment = []
    missing_resume = []
    missing_attendance = []
    missing_grades = []
    
    for student in students:
        email = get_student_email(student)
        name = get_student_name(student)
        
        # Check payment status
        payment_status = student.get('Payment Status', '').lower()
        if payment_status != 'paid':
            missing_payment.append({
                'email': email,
                'name': name,
                'status': payment_status or 'Unpaid'
            })
        
        # Check resume
        resume_link = get_student_resume_link(student)
        if not has_resume(resume_link):
            missing_resume.append({
                'email': email,
                'name': name
            })
        
        # Check attendance
        attendance = parse_attendance(student.get('Attendance', {}))
        if not attendance or not any(attendance.values()):
            missing_attendance.append({
                'email': email,
                'name': name
            })
        
        # Check grades
        missing_assignment_grades = []
        for i in range(total_labs):
            grade_col = f'Assignment {i+1} Grade'
            grade = student.get(grade_col, '')
            if not grade or str(grade).strip() == '':
                missing_assignment_grades.append(f'Assignment {i+1}')
        
        if missing_assignment_grades:
            missing_grades.append({
                'email': email,
                'name': name,
                'missing': missing_assignment_grades
            })
    
    return {
        'missing_payment': missing_payment,
        'missing_resume': missing_resume,
        'missing_attendance': missing_attendance,
        'missing_grades': missing_grades
    }


def sort_students(students: List[Dict[str, Any]], sort_by: str = 'name', sort_order: str = 'asc') -> None:
    """
    Sort students list in-place by specified field and order.
    
    Args:
        students: List of student dictionaries (modified in-place)
        sort_by: Field to sort by ('name', 'email', 'payment', 'timestamp')
        sort_order: Sort order ('asc' or 'desc')
    """
    reverse = (sort_order == 'desc')
    
    if sort_by == 'name':
        students.sort(
            key=lambda x: (x.get('Name') or x.get('Email Address') or '').lower(),
            reverse=reverse
        )
    elif sort_by == 'email':
        students.sort(
            key=lambda x: (x.get('Email Address') or '').lower(),
            reverse=reverse
        )
    elif sort_by == 'payment':
        payment_order = {'Paid': 0, 'Unpaid': 1, 'Not Registered': 2}
        students.sort(
            key=lambda x: payment_order.get(x.get('Payment Status', 'Unpaid'), 3),
            reverse=reverse
        )
    elif sort_by == 'timestamp':
        students.sort(
            key=lambda x: x.get('Timestamp') or '',
            reverse=reverse
        )


def validate_attendance_format(attendance: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate attendance format (must be dict or JSON string).
    
    Args:
        attendance: Attendance data to validate
        
    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if attendance is None:
        return True, None
    
    if isinstance(attendance, dict):
        return True, None
    elif isinstance(attendance, str):
        try:
            json.loads(attendance)
            return True, None
        except json.JSONDecodeError:
            return False, 'Invalid Attendance format. Must be JSON string or object.'
    else:
        return False, 'Attendance must be a dictionary or JSON string.'


def validate_grade_format(grade: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate grade format (must be string or number).
    
    Args:
        grade: Grade value to validate
        
    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if grade is None:
        return True, None
    
    if isinstance(grade, (str, int, float)):
        return True, None
    else:
        return False, 'Grade must be a string or number.'

