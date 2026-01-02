from flask import Blueprint, request, jsonify
from google_drive import GoogleDriveClient
from auth import require_auth, verify_password
import uuid

api = Blueprint('api', __name__)

# Initialize Google Drive client
try:
    drive_client = GoogleDriveClient()
except Exception as e:
    print(f"Warning: Google Drive client not initialized: {e}")
    drive_client = None

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
    """Get all course data (public)"""
    try:
        if not drive_client:
            return jsonify({
                "modules": [],
                "links": [],
                "metadata": {
                    "schedule": "",
                    "pricing": {"standard": 0, "student": 0}
                }
            }), 200
        
        data = drive_client.get_course_data()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin endpoints
@api.route('/admin/login', methods=['POST'])
def admin_login():
    """Verify admin password"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if verify_password(password):
            return jsonify({'success': True, 'message': 'Login successful'}), 200
        else:
            return jsonify({'success': False, 'error': 'Invalid password'}), 401
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
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/data', methods=['PUT'])
@require_auth
def update_course_data():
    """Update entire course data JSON"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = request.get_json()
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'message': 'Course data updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/modules', methods=['POST'])
@require_auth
def add_module():
    """Add new module"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        new_module = request.get_json()
        new_module['id'] = str(uuid.uuid4())
        
        # Set order if not provided
        if 'order' not in new_module:
            new_module['order'] = len(data['modules']) + 1
        
        data['modules'].append(new_module)
        data['modules'].sort(key=lambda x: x.get('order', 0))
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'module': new_module}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/modules/<module_id>', methods=['PUT'])
@require_auth
def update_module(module_id):
    """Update module"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        updated_module = request.get_json()
        
        for i, module in enumerate(data['modules']):
            if module['id'] == module_id:
                updated_module['id'] = module_id
                data['modules'][i] = updated_module
                break
        else:
            return jsonify({'error': 'Module not found'}), 404
        
        data['modules'].sort(key=lambda x: x.get('order', 0))
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'module': updated_module}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/modules/<module_id>', methods=['DELETE'])
@require_auth
def delete_module(module_id):
    """Delete module"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        data['modules'] = [m for m in data['modules'] if m['id'] != module_id]
        
        # Reorder remaining modules
        for i, module in enumerate(data['modules']):
            module['order'] = i + 1
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'message': 'Module deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/links', methods=['POST'])
@require_auth
def add_link():
    """Add new link"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        new_link = request.get_json()
        new_link['id'] = str(uuid.uuid4())
        
        # Set order if not provided
        if 'order' not in new_link:
            new_link['order'] = len(data['links']) + 1
        
        data['links'].append(new_link)
        data['links'].sort(key=lambda x: x.get('order', 0))
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'link': new_link}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/links/<link_id>', methods=['PUT'])
@require_auth
def update_link(link_id):
    """Update link"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        updated_link = request.get_json()
        
        for i, link in enumerate(data['links']):
            if link['id'] == link_id:
                updated_link['id'] = link_id
                data['links'][i] = updated_link
                break
        else:
            return jsonify({'error': 'Link not found'}), 404
        
        data['links'].sort(key=lambda x: x.get('order', 0))
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'link': updated_link}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/admin/links/<link_id>', methods=['DELETE'])
@require_auth
def delete_link(link_id):
    """Delete link"""
    try:
        if not drive_client:
            return jsonify({'error': 'Google Drive client not configured'}), 500
        
        data = drive_client.get_course_data()
        data['links'] = [l for l in data['links'] if l['id'] != link_id]
        
        # Reorder remaining links
        for i, link in enumerate(data['links']):
            link['order'] = i + 1
        
        drive_client.update_course_data(data)
        return jsonify({'success': True, 'message': 'Link deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

