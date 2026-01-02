import os
from functools import wraps
from flask import request, jsonify

def get_admin_password():
    """Get admin password from environment variable"""
    return os.getenv('ADMIN_PASSWORD', '')

def verify_password(password):
    """Verify if provided password matches admin password"""
    return password == get_admin_password()

def require_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401
        
        try:
            # Expecting "Bearer <password>" format
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            if not verify_password(token):
                return jsonify({'error': 'Invalid password'}), 401
        except Exception as e:
            return jsonify({'error': 'Invalid authorization format'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

