from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables BEFORE importing routes
# Get the directory where this file is located
backend_dir = Path(__file__).parent
env_path = backend_dir / '.env'
# Only load .env file if it exists (for local development)
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment from {env_path}")

# Also try to load from root directory if not found in backend
root_env_path = backend_dir.parent / '.env'
if root_env_path.exists():
    load_dotenv(dotenv_path=root_env_path)
    print(f"Loaded environment from {root_env_path}")
    
if not env_path.exists() and not root_env_path.exists():
    # In production (Render), environment variables are set directly
    load_dotenv()

from api.routes import api

app = Flask(__name__)

# CORS configuration - require explicit origins (no wildcard default)
cors_origins = os.getenv('CORS_ORIGINS', '')
if not cors_origins:
    # In development, allow localhost if CORS_ORIGINS not set
    import sys
    if '--dev' in sys.argv or os.getenv('FLASK_ENV') == 'development':
        cors_origins = 'http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173'
        print("WARNING: Using default CORS origins for development. Set CORS_ORIGINS in production!")
    else:
        raise ValueError("CORS_ORIGINS environment variable must be set in production")

CORS(app, origins=cors_origins.split(','))

# Register blueprints
app.register_blueprint(api, url_prefix='/api')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'message': 'Backend is running'}, 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return {'status': 'ok', 'message': 'Course Website API'}, 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

