import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io

class GoogleDriveClient:
    def __init__(self):
        self.file_id = os.getenv('GOOGLE_DRIVE_FILE_ID')
        
        if not self.file_id:
            raise ValueError("GOOGLE_DRIVE_FILE_ID environment variable is required")
        
        # Try to get service account JSON from environment variable first (for Render)
        service_account_json = os.getenv('SERVICE_ACCOUNT_JSON')
        
        if service_account_json:
            # Parse JSON from environment variable
            try:
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid SERVICE_ACCOUNT_JSON format: {e}")
        else:
            # Fall back to file path (for local development)
            self.service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH', './service_account.json')
            
            if not os.path.exists(self.service_account_path):
                raise FileNotFoundError(
                    f"Service account file not found: {self.service_account_path}. "
                    "Either set SERVICE_ACCOUNT_JSON environment variable or provide a valid file path."
                )
            
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
        
        self.service = build('drive', 'v3', credentials=credentials)
    
    def get_course_data(self):
        """Read JSON file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=self.file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            content = file_content.read().decode('utf-8')
            data = json.loads(content)
            
            # Ensure links array exists and has default links if empty
            if not data.get("links") or len(data.get("links", [])) == 0:
                data["links"] = []
            
            return data
        except Exception as e:
            print(f"Error reading from Google Drive: {e}")
            # Return default structure if file doesn't exist
            return {
                "modules": [],
                "links": [],
                "metadata": {
                    "schedule": "",
                    "pricing": {
                        "standard": 0,
                        "student": 0
                    }
                }
            }
    
    def update_course_data(self, data):
        """Write JSON file to Google Drive"""
        try:
            json_data = json.dumps(data, indent=2)
            media = MediaIoBaseUpload(
                io.BytesIO(json_data.encode('utf-8')),
                mimetype='application/json',
                resumable=True
            )
            
            self.service.files().update(
                fileId=self.file_id,
                media_body=media
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error writing to Google Drive: {e}")
            raise

