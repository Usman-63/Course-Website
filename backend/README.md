# Backend Setup Guide

This backend provides API endpoints for managing course data stored on Google Drive.

## Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Drive API enabled
- Service Account credentials

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google Drive:
   - Create a Google Cloud Project
   - Enable Google Drive API
   - Create a Service Account
   - Download the service account JSON key file
   - Share your Google Drive file/folder with the service account email
   - Place the JSON file in the `backend/` directory as `service_account.json`

3. Create a JSON file on Google Drive for course data:
   - Create a new file in Google Drive
   - Name it `course_data.json`
   - Share it with the service account email
   - Copy the file ID from the URL (the long string after `/d/` and before `/edit`)

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in the required values:
     ```
     ADMIN_PASSWORD=your_secure_password_here
     GOOGLE_DRIVE_FILE_ID=your_google_drive_file_id_here
     GOOGLE_SERVICE_ACCOUNT_PATH=./service_account.json
     FLASK_ENV=development
     FLASK_DEBUG=True
     PORT=5000
     ```

## Running the Server

```bash
python app.py
```

The server will start on `http://localhost:5000` by default.

## API Endpoints

### Public Endpoints

- `GET /api/course/data` - Get all course data (modules, links, metadata)

### Admin Endpoints (Password Protected)

- `POST /api/admin/login` - Login with password
- `GET /api/admin/data` - Get course data (admin view)
- `PUT /api/admin/data` - Update entire course data
- `POST /api/admin/modules` - Add new module
- `PUT /api/admin/modules/:id` - Update module
- `DELETE /api/admin/modules/:id` - Delete module
- `POST /api/admin/links` - Add new link
- `PUT /api/admin/links/:id` - Update link
- `DELETE /api/admin/links/:id` - Delete link
- `POST /api/admin/import` - Import from courseformat.txt

## Data Structure

The course data JSON file should follow this structure:

```json
{
  "modules": [
    {
      "id": "1",
      "title": "Module 1: Title",
      "hours": 5,
      "focus": "Module focus description",
      "topics": ["Topic 1", "Topic 2"],
      "order": 1
    }
  ],
  "links": [
    {
      "id": "1",
      "title": "Course Syllabus",
      "url": "https://...",
      "description": "Link description",
      "iconType": "file",
      "order": 1
    }
  ],
  "metadata": {
    "description": "Course description",
    "schedule": "Schedule information",
    "pricing": {
      "standard": 495.00,
      "student": 249.00
    }
  }
}
```

## Security Notes

- Never commit `.env` or `service_account.json` to version control
- Use strong passwords in production
- Enable HTTPS in production
- Configure CORS appropriately for your frontend domain

