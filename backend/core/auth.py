import os
import json
import base64
import time
import hashlib
from functools import wraps
from flask import request, jsonify
import firebase_admin
from firebase_admin import credentials, auth
import jwt
from datetime import datetime, timedelta
from core.logger import logger

# JWT Configuration
# Require JWT_SECRET_KEY in production (like CORS_ORIGINS)
# Only allow random generation in development mode
_jwt_secret_env = os.getenv('JWT_SECRET_KEY')
if not _jwt_secret_env:
    # Check if we're in development mode
    import sys
    is_dev = '--dev' in sys.argv or os.getenv('FLASK_ENV') == 'development'
    if is_dev:
        _jwt_secret_env = os.urandom(32).hex()
        logger.warning("JWT_SECRET_KEY not set. Using random key for development. Set JWT_SECRET_KEY in production!")
    else:
        raise ValueError("JWT_SECRET_KEY environment variable must be set in production")
JWT_SECRET_KEY = _jwt_secret_env
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24  # Token expires after 24 hours

# Rate limiting: track failed login attempts
login_attempts = {}  # {ip: {count: int, reset_time: float}}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutes

# Initialize Firebase Admin SDK
def init_firebase_admin():
    try:
        # Check if already initialized
        if firebase_admin._apps:
            return

        # 1. Try explicit path env var
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized successfully")
            return

        # 2. Try base64 content env var (or check if user mistakenly put a path here)
        service_account_b64 = os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64')
        if service_account_b64:
            # Check if it looks like a path
            if service_account_b64.endswith('.json') and os.path.exists(service_account_b64):
                cred = credentials.Certificate(service_account_b64)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized successfully")
                return
            
            # Check if it looks like raw JSON (user pasted JSON directly)
            if service_account_b64.strip().startswith('{'):
                try:
                    service_account_info = json.loads(service_account_b64)
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin initialized successfully")
                    return
                except Exception as e:
                     logger.warning(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_BASE64 as raw JSON: {type(e).__name__}")

            try:
                # Decode base64 to json string
                # Add padding if missing
                missing_padding = len(service_account_b64) % 4
                if missing_padding:
                    service_account_b64 += '=' * (4 - missing_padding)
                    
                service_account_info = json.loads(base64.b64decode(service_account_b64))
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to decode FIREBASE_SERVICE_ACCOUNT_BASE64: {type(e).__name__}")

        # 3. Fallback: Try to load from local file (for local development)
        # Look for serviceAccountKey.json in the same directory or parent
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(current_dir, 'serviceAccountKey.json')
        
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized successfully")
            return
            
        logger.warning("No Firebase Admin credentials found. Custom tokens will not work.")
        
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin: {type(e).__name__}")

# Initialize on module load
init_firebase_admin()

def create_custom_token(uid):
    """Create a custom Firebase token for the given UID"""
    try:
        if not firebase_admin._apps:
            logger.warning("Firebase Admin not initialized, cannot create token")
            return None
            
        # Create a custom token for the given user
        custom_token = auth.create_custom_token(uid)
        # Convert bytes to string if necessary (Python 3.x returns bytes)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode('utf-8')
            
        return custom_token
    except Exception as e:
        logger.error(f"Error creating custom token: {type(e).__name__}")
        return None

def get_admin_password():
    """Get admin password from environment variable"""
    # Try ADMIN_PASSWORD first, then VITE_ADMIN_PASSWORD
    return os.getenv('ADMIN_PASSWORD') or os.getenv('VITE_ADMIN_PASSWORD') or ''

def verify_password(password):
    """Verify if provided password matches admin password"""
    return password == get_admin_password()

def get_client_ip():
    """Get client IP address for rate limiting"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

def check_rate_limit():
    """Check if client has exceeded login attempt rate limit"""
    ip = get_client_ip()
    now = time.time()
    
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'reset_time': now + LOGIN_WINDOW_SECONDS}
        return True
    
    attempt_data = login_attempts[ip]
    
    # Reset if window expired
    if now > attempt_data['reset_time']:
        attempt_data['count'] = 0
        attempt_data['reset_time'] = now + LOGIN_WINDOW_SECONDS
        return True
    
    # Check if exceeded limit
    if attempt_data['count'] >= MAX_LOGIN_ATTEMPTS:
        return False
    
    return True

def record_failed_login():
    """Record a failed login attempt"""
    ip = get_client_ip()
    now = time.time()
    
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'reset_time': now + LOGIN_WINDOW_SECONDS}
    
    login_attempts[ip]['count'] += 1

def clear_login_attempts(ip):
    """Clear login attempts for an IP after successful login"""
    if ip in login_attempts:
        del login_attempts[ip]

def create_jwt_token():
    """Create a JWT token for authenticated admin"""
    payload = {
        'user_id': 'admin',
        'role': 'admin',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token):
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require admin authentication using JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401
        
        try:
            # Expecting "Bearer <token>" format
            if ' ' not in auth_header:
                return jsonify({'error': 'Invalid authorization format. Expected "Bearer <token>"'}), 401
            
            token = auth_header.split(' ')[1]
            
            # Verify JWT token
            payload = verify_jwt_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Token is valid
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid authorization format'}), 401
    
    return decorated_function
