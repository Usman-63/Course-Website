# Setup Guide

## Backend Setup

1. Navigate to the `backend` directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Drive:
   - Create a Google Cloud Project
   - Enable Google Drive API
   - Create a Service Account
   - Download the service account JSON key file
   - Share your Google Drive file/folder with the service account email
   - Place the JSON file in the `backend/` directory as `service_account.json`

4. Create a JSON file on Google Drive:
   - Create a new file in Google Drive
   - Name it `course_data.json`
   - Share it with the service account email
   - Copy the file ID from the URL (the long string after `/d/` and before `/edit`)

5. Create `.env` file in `backend/` directory:
```env
ADMIN_PASSWORD=your_secure_password_here
GOOGLE_DRIVE_FILE_ID=your_google_drive_file_id_here
GOOGLE_SERVICE_ACCOUNT_PATH=./service_account.json
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5000
```

6. Run the backend server:
```bash
python app.py
```

The server will start on `http://localhost:5000` by default.

## Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file in the root directory:
```env
VITE_ADMIN_PASSWORD=your_secure_password_here
VITE_API_URL=http://localhost:5000
```

**Note:** The `VITE_ADMIN_PASSWORD` must match the `ADMIN_PASSWORD` in the backend `.env` file.

3. Run the development server:
```bash
npm run dev
```

## Accessing Admin Panel

1. Navigate to the website
2. Click on the footer (bottom right corner) - there's a hidden admin link
3. Or navigate directly to `/admin`
4. Enter the admin password to access the panel

## Initial Data Setup

You can import the course format by:
1. Logging into the admin panel
2. Going to the "Metadata" tab
3. Pasting the content from `courseformat.txt` into the import textarea
4. Clicking "Import Course Format"

This will parse the text and create the initial course modules structure.

## Data Structure

The course data is stored as JSON on Google Drive with this structure:

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

