from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables BEFORE importing routes
# This ensures env vars are available when GoogleDriveClient is initialized
# Get the directory where this file is located
backend_dir = Path(__file__).parent
env_path = backend_dir / '.env'
# Only load .env file if it exists (for local development)
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # In production (Render), environment variables are set directly
    load_dotenv()

from routes import api

app = Flask(__name__)

# CORS configuration - allow all origins in production, or specific ones from env
cors_origins = os.getenv('CORS_ORIGINS', '*')
if cors_origins == '*':
    CORS(app)
else:
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

