from flask import Blueprint, request, jsonify
from google_drive import GoogleDriveClient
from auth import (
    require_auth, 
    verify_password, 
    create_custom_token, 
    create_jwt_token,
    check_rate_limit,
    record_failed_login,
    clear_login_attempts,
    get_client_ip
)
from validators import validate_module, validate_course_data, ValidationError
from logger import logger
from student_helpers import (
    get_total_labs_count,
    get_allowed_assignment_fields,
    get_student_email,
    get_student_name,
    get_student_resume_link,
    has_resume,
    parse_attendance,
    calculate_student_metrics,
    calculate_student_status,
    sort_students,
    validate_attendance_format,
    validate_grade_format
)
import uuid
import time
import hashlib
import json

api = Blueprint('api', __name__)

def normalize_course_data(data):
    """Ensure data follows the new multi-course structure."""
    if 'courses' in data and isinstance(data['courses'], list):
        return data
    
    # Create default course from existing data
    default_course = {
        'id': 'default-course',
        'title': 'Main Course',
        'isVisible': True,
        'modules': data.get('modules', []),
        'links': data.get('links', []),
        'metadata': data.get('metadata', {
            'schedule': '',
            'pricing': {'standard': 0, 'student': 0}
        })
    }
    
    return {
        'version': data.get('version', int(time.time() * 1000)),
        'courses': [default_course]
    }

# Initialize Google Drive client
try:
    drive_client = GoogleDriveClient()
except Exception as e:
    print(f"Warning: Google Drive client not initialized: {e}")
    drive_client = None

# Initialize Google Sheets manager
try:
    from google_sheets_manager import GoogleSheetsManager
    sheets_manager = GoogleSheetsManager()
except Exception as e:
    print(f"Warning: Google Sheets manager not initialized: {e}")
    sheets_manager = None

# Public endpoints
@api.route('/notification', methods=['POST'])
def notification():
    """Handle notification signup"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        # In a real app, we would save this to a database or send an email
        print(f"Notification request for email: {email}")
        
        return jsonify({'success': True, 'message': 'We will notify you'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/course/data', methods=['GET'])
def get_course_data():
    """Get all course data (public) - Returns primary visible course for backward compatibility"""
    try:
        if not drive_client:
            return jsonify({
                "modules": [],
                "metadata": {
                    "schedule": "",
                    "pricing": {"standard": 0, "student": 0}
                }
            }), 200
        
        data = drive_client.get_course_data()
        normalized = normalize_course_data(data)
        
        # Find primary visible course (first one that is visible)
        primary_course = None
        if normalized['courses']:
            for course in normalized['courses']:
                if course.get('isVisible', True):
                    primary_course = course
                    break
            
            # If no visible course found, fallback to first one (or empty)
            if not primary_course and normalized['courses']:
                primary_course = normalized['courses'][0]
        
        if primary_course:
            # Return flattened structure for frontend compatibility
            return jsonify({
                'version': normalized.get('version', 0),
                'modules': primary_course.get('modules', []),
                'links': primary_course.get('links', []),
                'metadata': primary_course.get('metadata', {})
            }), 200
        else:
             return jsonify({
                "modules": [],
                "metadata": {}
            }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/course/version', methods=['GET'])
def get_course_version():
    """Get course data version (public)"""
    try:
        if not drive_client:
            return jsonify({'version': 0}), 200
        
        data = drive_client.get_course_data()
        version = data.get('version')
        
        # If no explicit version exists, generate a stable hash from the data
        if not version:
            try:
                # Create a copy to avoid modifying original
                data_copy = data.copy()
                # Remove version key if it exists (though it shouldn't if we are here)
                data_copy.pop('version', None)
                # Generate stable string representation
                data_str = json.dumps(data_copy, sort_keys=True)
                # Create numeric hash (use first 13 digits to simulate timestamp length)
                version = int(hashlib.sha256(data_str.encode('utf-8')).hexdigest(), 16) % (10**13)
            except Exception:
                version = 0
                
        return jsonify({'version': version}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin endpoints
@api.route('/admin/login', methods=['POST'])
def admin_login():
    """Verify admin password and return JWT token"""
    try:
        # Check rate limiting
        if not check_rate_limit():
            logger.warning(f'Rate limit exceeded for IP: {get_client_ip()}')
            return jsonify({
                'success': False, 
                'error': 'Too many login attempts. Please try again later.'
            }), 429
        
        data = request.get_json()
        password = data.get('password', '')
        
        if verify_password(password):
            # Clear failed login attempts
            clear_login_attempts(get_client_ip())
            
            # Create JWT token
            jwt_token = create_jwt_token()
            
            # Create a Firebase custom token for the admin
            # We use a fixed UID for the admin to simplify permissions
            firebase_token = create_custom_token('admin-user')
            
            logger.info(f'Admin login successful from IP: {get_client_ip()}')
            
            response = {
                'success': True, 
                'message': 'Login successful',
                'token': jwt_token,  # JWT token for API authentication
                'firebase_token': firebase_token  # Firebase token for real-time features
            }
            return jsonify(response), 200
        else:
            # Record failed login attempt
            record_failed_login()
            logger.warning(f'Failed login attempt from IP: {get_client_ip()}')
            return jsonify({'success': False, 'error': 'Invalid password'}), 401
    except Exception as e:
        logger.error(f'Error in admin login: {str(e)}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/admin/firebase-token', methods=['GET'])
@require_auth
def get_firebase_token():
    """Get a fresh Firebase custom token for authenticated admin"""
    try:
        firebase_token = create_custom_token('admin-user')
        if not firebase_token:
             # If token creation failed (e.g. no creds), return 200 with null to avoid client errors
             # The client will just have to live without Firebase or show the error
             return jsonify({'firebase_token': None}), 200
             
        return jsonify({'firebase_token': firebase_token}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/data', methods=['GET'])
@require_auth
def get_admin_data():
    """Get course data (admin view)"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        normalized = normalize_course_data(data)
        return jsonify(normalized), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/courses', methods=['POST'])
@require_auth
def add_course():
    """Add new course"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
            
        data = drive_client.get_course_data()
        data = normalize_course_data(data)
        
        req_data = request.get_json()
        if not req_data or 'title' not in req_data:
             return jsonify({'error': 'Title is required'}), 400
             
        new_course = {
            'id': str(uuid.uuid4()),
            'title': req_data['title'],
            'isVisible': req_data.get('isVisible', False), # Default hidden
            'modules': [],
            'links': [],
            'metadata': {
                'schedule': '',
                'pricing': {'standard': 0, 'student': 0}
            }
        }
        
        data['courses'].append(new_course)
        data['version'] = int(time.time() * 1000)
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'course': new_course}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/courses/<course_id>', methods=['PUT'])
@require_auth
def update_course(course_id):
    """Update course metadata (title, visibility)"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
            
        data = drive_client.get_course_data()
        data = normalize_course_data(data)
        
        req_data = request.get_json()
        
        course_found = False
        for course in data['courses']:
            if course['id'] == course_id:
                if 'title' in req_data:
                    course['title'] = req_data['title']
                if 'isVisible' in req_data:
                    course['isVisible'] = req_data['isVisible']
                if 'metadata' in req_data:
                    course['metadata'] = req_data['metadata']
                course_found = True
                break
        
        if not course_found:
             return jsonify({'error': 'Course not found'}), 404
             
        data['version'] = int(time.time() * 1000)
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'message': 'Course updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/courses/<course_id>', methods=['DELETE'])
@require_auth
def delete_course(course_id):
    """Delete a course"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        data = normalize_course_data(data)
        
        # Check if course exists
        course_exists = False
        for course in data['courses']:
            if course['id'] == course_id:
                course_exists = True
                break
        
        if not course_exists:
            return jsonify({'error': 'Course not found'}), 404
            
        # Filter out the course to delete
        data['courses'] = [c for c in data['courses'] if c['id'] != course_id]
        
        # Update version
        data['version'] = int(time.time() * 1000)
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'message': 'Course deleted successfully'}), 200
    except Exception as e:
        logger.error(f'Error deleting course: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@api.route('/admin/data', methods=['PUT'])
@require_auth
def update_course_data():
    """Update entire course data JSON"""
    try:
        if not drive_client:
            logger.error('Google Drive client not configured')
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate course data
        try:
            validate_course_data(data)
        except ValidationError as e:
            logger.warning(f'Course data validation failed: {str(e)}')
            return jsonify({'error': f'Validation failed: {str(e)}'}), 400
        
        # Update version
        data['version'] = int(time.time() * 1000)
        
        drive_client.update_course_data(data)
        logger.info('Course data updated successfully')
        return jsonify({'success': True, 'message': 'Course data updated successfully'}), 200
    except ValidationError as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 400
    except Exception as e:
        logger.error(f'Error updating course data: {str(e)}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/admin/modules', methods=['POST'])
@require_auth
def add_module():
    """Add new module"""
    try:
        if not drive_client:
            logger.error('Google Drive client not configured')
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        data = normalize_course_data(data)
        
        new_module = request.get_json()
        
        if not new_module:
            return jsonify({'error': 'Request body is required'}), 400
            
        course_id = request.args.get('courseId')
        target_course = None
        
        if not data['courses']:
             return jsonify({'error': 'No courses found'}), 500

        if course_id:
            for course in data['courses']:
                if course['id'] == course_id:
                    target_course = course
                    break
            if not target_course:
                return jsonify({'error': 'Course not found'}), 404
        else:
            # Default to first course
            target_course = data['courses'][0]
        
        # Validate module data
        try:
            validate_module(new_module)
        except ValidationError as e:
            logger.warning(f'Module validation failed: {str(e)}')
            return jsonify({'error': f'Validation failed: {str(e)}'}), 400
        
        new_module['id'] = str(uuid.uuid4())
        
        # Set order if not provided
        if 'order' not in new_module:
            new_module['order'] = len(target_course['modules']) + 1
        
        target_course['modules'].append(new_module)
        target_course['modules'].sort(key=lambda x: x.get('order', 0))
        
        # Update version
        data['version'] = int(time.time() * 1000)
        
        drive_client.update_course_data(data)
        logger.info(f'Module added: {new_module["id"]} to course {target_course["id"]}')
        return jsonify({'success': True, 'module': new_module}), 201
    except ValidationError as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 400
    except Exception as e:
        logger.error(f'Error adding module: {str(e)}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/admin/modules/<module_id>', methods=['PUT'])
@require_auth
def update_module(module_id):
    """Update module"""
    try:
        if not drive_client:
            logger.error('Google Drive client not configured')
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        data = normalize_course_data(data)
        
        updated_module = request.get_json()
        
        if not updated_module:
            return jsonify({'error': 'Request body is required'}), 400
            
        course_id = request.args.get('courseId')
        target_course = None
        
        if not data['courses']:
             return jsonify({'error': 'No courses found'}), 500

        if course_id:
            for course in data['courses']:
                if course['id'] == course_id:
                    target_course = course
                    break
            if not target_course:
                return jsonify({'error': 'Course not found'}), 404
        else:
            # Default to first course
            target_course = data['courses'][0]
        
        # Find existing module first to support partial updates
        existing_module_index = -1
        for i, module in enumerate(target_course['modules']):
            if module['id'] == module_id:
                existing_module_index = i
                break
        
        if existing_module_index == -1:
            logger.warning(f'Module not found: {module_id}')
            return jsonify({'error': 'Module not found'}), 404
            
        # Merge existing module with updates
        merged_module = target_course['modules'][existing_module_index].copy()
        merged_module.update(updated_module)
        merged_module['id'] = module_id # Ensure ID doesn't change
        
        # Validate merged module data
        try:
            validate_module(merged_module)
        except ValidationError as e:
            logger.warning(f'Module validation failed: {str(e)}')
            return jsonify({'error': f'Validation failed: {str(e)}'}), 400
        
        # Update the module in the list
        target_course['modules'][existing_module_index] = merged_module
        
        target_course['modules'].sort(key=lambda x: x.get('order', 0))
        
        # Update version
        data['version'] = int(time.time() * 1000)
        
        drive_client.update_course_data(data)
        logger.info(f'Module updated: {module_id}')
        return jsonify({'success': True, 'module': updated_module}), 200
    except ValidationError as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 400
    except Exception as e:
        logger.error(f'Error updating module: {str(e)}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/admin/modules/<module_id>', methods=['DELETE'])
@require_auth
def delete_module(module_id):
    """Delete module"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        data = normalize_course_data(data)
        
        course_id = request.args.get('courseId')
        target_course = None
        
        if not data['courses']:
             return jsonify({'error': 'No courses found'}), 500

        if course_id:
            for course in data['courses']:
                if course['id'] == course_id:
                    target_course = course
                    break
            if not target_course:
                return jsonify({'error': 'Course not found'}), 404
        else:
            # Default to first course
            target_course = data['courses'][0]
        
        target_course['modules'] = [m for m in target_course['modules'] if m['id'] != module_id]
        
        # Reorder remaining modules
        for i, module in enumerate(target_course['modules']):
            module['order'] = i + 1
        
        # Update version
        data['version'] = int(time.time() * 1000)
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'message': 'Module deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Student Operations Endpoints (Google Sheets)
@api.route('/admin/students/operations', methods=['GET'])
@require_auth
def get_all_students_operations():
    """Get all students with merged data from Survey, Register, and Admin_Logs."""
    try:
        if not sheets_manager:
            logger.error('Google Sheets manager not configured')
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        # Check force refresh
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        students = sheets_manager.get_all_students(force_refresh=force_refresh)
        
        # Get sort parameters from query string
        sort_by = request.args.get('sort_by', 'name')  # Default: sort by name
        sort_order = request.args.get('sort_order', 'asc')  # Default: ascending
        
        # Sort students
        sort_students(students, sort_by=sort_by, sort_order=sort_order)
        
        logger.info(f'Retrieved {len(students)} students for operations (sorted by {sort_by}, {sort_order})')
        return jsonify({'success': True, 'students': students}), 200
    except ValueError as e:
        logger.warning(f'Validation error getting students: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Error getting all students operations: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to fetch students: {str(e)}'}), 500

@api.route('/admin/students/operations/<email>', methods=['GET'])
@require_auth
def get_student_operations(email):
    """Get specific student data by email."""
    try:
        if not sheets_manager:
            logger.error('Google Sheets manager not configured')
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        if not email or not email.strip():
            return jsonify({'error': 'Email address is required'}), 400
        
        student = sheets_manager.get_student_by_email(email)
        if not student:
            logger.info(f'Student not found: {email}')
            return jsonify({'error': 'Student not found'}), 404
        
        return jsonify({'success': True, 'student': student}), 200
    except ValueError as e:
        logger.warning(f'Validation error getting student: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Error getting student operations: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to fetch student: {str(e)}'}), 500

@api.route('/admin/students/operations/<email>', methods=['PUT'])
@require_auth
def update_student_operations(email):
    """Update student data in Admin_Logs (attendance, grades, evaluation)."""
    try:
        if not sheets_manager:
            logger.error('Google Sheets manager not configured')
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        if not email or not email.strip():
            return jsonify({'error': 'Email address is required'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get total labs to determine allowed assignment grade fields
        total_labs = get_total_labs_count(drive_client)
        allowed_fields = get_allowed_assignment_fields(total_labs)
        
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({'error': 'No valid fields to update. Allowed fields: ' + ', '.join(allowed_fields)}), 400
        
        # Validate attendance format if provided
        if 'Attendance' in updates:
            is_valid, error_msg = validate_attendance_format(updates['Attendance'])
            if not is_valid:
                return jsonify({'error': error_msg}), 400
        
        # Validate grade fields are strings or numbers
        for grade_field in allowed_fields:
            if grade_field.startswith('Assignment') and grade_field in updates:
                is_valid, error_msg = validate_grade_format(updates[grade_field])
                if not is_valid:
                    return jsonify({'error': f'{grade_field} {error_msg}'}), 400
        
        success = sheets_manager.update_student_data(email, updates)
        if success:
            logger.info(f'Updated student operations for: {email}')
            return jsonify({'success': True, 'message': 'Student data updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update student data'}), 500
    except ValueError as e:
        logger.warning(f'Validation error updating student: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Error updating student operations: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to update student: {str(e)}'}), 500

@api.route('/admin/students/operations/bulk', methods=['POST'])
@require_auth
def bulk_update_students_operations():
    """Bulk update multiple students in Admin_Logs."""
    try:
        if not sheets_manager:
            logger.error('Google Sheets manager not configured')
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        data = request.get_json()
        if not data or 'updates' not in data:
            return jsonify({'error': 'Request body must contain "updates" array'}), 400
        
        updates = data['updates']
        if not isinstance(updates, list):
            return jsonify({'error': '"updates" must be an array'}), 400
        
        if len(updates) == 0:
            return jsonify({'error': 'Updates array cannot be empty'}), 400
        
        if len(updates) > 100:
            return jsonify({'error': 'Cannot update more than 100 students at once'}), 400
        
        # Get total labs to determine allowed assignment grade fields
        total_labs = get_total_labs_count(drive_client)
        allowed_fields = get_allowed_assignment_fields(total_labs)
        
        # Validate each update has email and valid fields
        for i, update in enumerate(updates):
            if not isinstance(update, dict):
                return jsonify({'error': f'Update at index {i} must be an object'}), 400
            if 'email' not in update:
                return jsonify({'error': f'Update at index {i} must have an "email" field'}), 400
            if not update['email'] or not str(update['email']).strip():
                return jsonify({'error': f'Update at index {i} has invalid email'}), 400
            # Check for invalid fields
            invalid_fields = [k for k in update.keys() if k != 'email' and k not in allowed_fields]
            if invalid_fields:
                return jsonify({'error': f'Update at index {i} has invalid fields: {", ".join(invalid_fields)}'}), 400
        
        success = sheets_manager.bulk_update_admin_logs(updates)
        if success:
            logger.info(f'Bulk updated {len(updates)} students')
            return jsonify({'success': True, 'message': f'Updated {len(updates)} students successfully'}), 200
        else:
            return jsonify({'error': 'Failed to bulk update students'}), 500
    except ValueError as e:
        logger.warning(f'Validation error in bulk update: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Error in bulk update: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to bulk update: {str(e)}'}), 500

@api.route('/admin/students/operations/metrics', methods=['GET'])
@require_auth
def get_students_operations_metrics():
    """Get dashboard metrics: total students, paid count, onboarding percentage."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        students = sheets_manager.get_all_students()
        metrics = calculate_student_metrics(students)
        
        return jsonify({'success': True, 'metrics': metrics}), 200
    except Exception as e:
        logger.error(f'Error getting metrics: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to fetch metrics: {str(e)}'}), 500

@api.route('/admin/students/operations/status', methods=['GET'])
@require_auth
def get_students_operations_status():
    """Get students with missing items (payment, resume, attendance, grades)."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        students = sheets_manager.get_all_students()
        total_labs = get_total_labs_count(drive_client)
        status = calculate_student_status(students, total_labs)
        
        return jsonify({'success': True, 'status': status}), 200
    except Exception as e:
        logger.error(f'Error getting status: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to fetch status: {str(e)}'}), 500

@api.route('/admin/students/operations/all', methods=['GET'])
@require_auth
def get_all_students_operations_combined():
    """Get all students data, metrics, and status in a single call."""
    try:
        if not sheets_manager:
            logger.error('Google Sheets manager not configured')
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        # Check force refresh
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Call get_all_students() ONCE
        students = sheets_manager.get_all_students(force_refresh=force_refresh)
        
        # Get sort parameters from query string
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Sort students
        sort_students(students, sort_by=sort_by, sort_order=sort_order)
        
        # Calculate metrics and status from the same data
        metrics = calculate_student_metrics(students)
        total_labs = get_total_labs_count(drive_client)
        status = calculate_student_status(students, total_labs)
        
        logger.info(f'Retrieved combined operations data for {len(students)} students (sorted by {sort_by}, {sort_order})')
        return jsonify({
            'success': True,
            'students': students,
            'metrics': metrics,
            'status': status
        }), 200
        
    except Exception as e:
        logger.error(f'Error getting combined operations data: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to fetch data: {str(e)}'}), 500

@api.route('/admin/students/operations/emails', methods=['GET'])
@require_auth
def get_students_operations_emails():
    """Export all student emails as comma-separated list."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        students = sheets_manager.get_all_students()
        
        emails = []
        for student in students:
            email = get_student_email(student)
            if email:
                emails.append(email)
        
        # Validate and format emails
        from sheets_utils import validate_email_list
        valid_emails = validate_email_list(emails)
        
        # Return as comma-separated string and as array
        emails_string = ', '.join(valid_emails)
        
        return jsonify({
            'success': True,
            'emails': valid_emails,
            'emails_string': emails_string,
            'count': len(valid_emails)
        }), 200
    except Exception as e:
        logger.error(f'Error exporting emails: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to export emails: {str(e)}'}), 500

# ==========================================
# Class Management Endpoints
# ==========================================

@api.route('/admin/classes', methods=['GET'])
@require_auth
def get_classes():
    """Get all classes."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        classes = sheets_manager.read_classes()
        return jsonify({'success': True, 'classes': classes}), 200
    except Exception as e:
        logger.error(f'Error getting classes: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@api.route('/admin/classes', methods=['POST'])
@require_auth
def add_class():
    """Add a new class."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
            
        # Generate ID if missing
        if 'id' not in data:
            import uuid
            data['id'] = str(uuid.uuid4())
            
        success = sheets_manager.add_class(data)
        if success:
            return jsonify({'success': True, 'class': data}), 201
        else:
            return jsonify({'error': 'Failed to add class'}), 500
    except Exception as e:
        logger.error(f'Error adding class: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@api.route('/admin/classes/<class_id>', methods=['DELETE'])
@require_auth
def delete_class(class_id):
    """Delete a class."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        success = sheets_manager.delete_class(class_id)
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Class not found or failed to delete'}), 404
    except Exception as e:
        logger.error(f'Error deleting class: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@api.route('/admin/classes/<class_id>/attendance', methods=['POST'])
@require_auth
def mark_class_attendance(class_id):
    """Mark attendance for a class (bulk update)."""
    try:
        if not sheets_manager:
            return jsonify({'error': 'Google Sheets manager not configured'}), 500
        
        data = request.get_json()
        present_emails = data.get('present_emails', [])
        
        success = sheets_manager.bulk_mark_attendance(class_id, present_emails)
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to mark attendance'}), 500
    except Exception as e:
        logger.error(f'Error marking attendance: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

