# Deployment Guide

This guide covers deploying the backend to Render and the frontend to Vercel.

## Backend Deployment (Render)

### Prerequisites
1. A Render account (sign up at https://render.com)
2. A Google Cloud Project with Google Drive API enabled
3. A service account JSON file for Google Drive access

### Step 1: Prepare Google Drive Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and description
   - Grant it "Editor" role (or custom role with Drive API access)
5. Create a key for the service account:
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the JSON file

### Step 2: Set up Google Drive File

1. Create a JSON file in Google Drive with the course data structure
2. Share the file with the service account email (found in the JSON file: `client_email`)
3. Copy the file ID from the Google Drive URL

### Step 3: Deploy to Render

#### Option A: Using Render Dashboard

1. Go to your Render dashboard
2. Click "New" > "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `course-website-backend` (or your preferred name)
   - **Environment**: `Python 3`
   - **Root Directory**: `backend` ⚠️ **IMPORTANT: Set this to `backend`**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

5. Add Environment Variables:
   - `GOOGLE_DRIVE_FILE_ID`: Your Google Drive file ID
   - `ADMIN_PASSWORD`: Password for admin panel access
   - `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g., `https://yourdomain.vercel.app,https://www.yourdomain.com`)
   - `PYTHON_VERSION`: `3.11.0`

6. For the service account JSON:
   - Go to "Environment" tab
   - Add a new environment variable named `SERVICE_ACCOUNT_JSON`
   - Paste the entire contents of your `service_account.json` file as the value
   - Alternatively, you can use Render's "Secret Files" feature

#### Option B: Using render.yaml (Recommended)

1. The `render.yaml` file is already configured
2. Push your code to GitHub
3. In Render dashboard, click "New" > "Blueprint"
4. Connect your repository
5. Render will automatically detect and use `render.yaml`
6. Set the environment variables in the Render dashboard

### Step 4: Update google_drive.py for Render

The code has been updated to handle service account JSON from environment variables. If you prefer to use the JSON file directly:

1. Upload `service_account.json` as a secret file in Render
2. Update the path in `google_drive.py` if needed

### Step 5: Test the Deployment

1. Once deployed, test the health endpoint: `https://your-service.onrender.com/health`
2. Test the API: `https://your-service.onrender.com/api/course/data`

## Frontend Deployment (Vercel)

### Prerequisites
1. A Vercel account (sign up at https://vercel.com)
2. Your frontend code ready

### Step 1: Prepare Environment Variables

Create a `.env.production` file or set in Vercel dashboard:
- `VITE_API_URL`: Your Render backend URL (e.g., `https://your-service.onrender.com`)

### Step 2: Deploy to Vercel

#### Option A: Using Vercel CLI

```bash
npm install -g vercel
vercel
```

#### Option B: Using Vercel Dashboard

1. Go to https://vercel.com
2. Click "New Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `.` (or leave default)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. Add Environment Variable:
   - `VITE_API_URL`: Your Render backend URL

6. Click "Deploy"

### Step 3: Update CORS in Backend

After deploying the frontend, update the `CORS_ORIGINS` environment variable in Render to include your Vercel URL:
- Example: `https://your-app.vercel.app,https://www.yourdomain.com`

## GitHub Setup

### .gitignore

The following files are already in `.gitignore`:
- `.env`
- `service_account.json`
- `__pycache__/`
- `*.pyc`

### Before Pushing to GitHub

1. Ensure `.env` is not committed
2. Ensure `service_account.json` is not committed
3. Create a `.env.example` file with placeholder values (optional but recommended)

### Recommended Repository Structure

```
course-website/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── render.yaml
│   ├── .gitignore
│   └── ...
├── src/
│   └── ...
├── .gitignore
├── package.json
└── README.md
```

## Environment Variables Reference

### Backend (Render)

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `GOOGLE_DRIVE_FILE_ID` | Google Drive file ID | Yes | `1vfePpeAynCBgUNobLc3tD3j42PsgaFgg` |
| `ADMIN_PASSWORD` | Admin panel password | Yes | `your-secure-password` |
| `CORS_ORIGINS` | Allowed CORS origins | Yes | `https://app.vercel.app` |
| `SERVICE_ACCOUNT_JSON` | Service account JSON content | Yes* | `{"type":"service_account",...}` |
| `PORT` | Server port | No | `10000` (Render default) |
| `FLASK_DEBUG` | Debug mode | No | `False` |

*Required if not using service_account.json file

### Frontend (Vercel)

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `VITE_API_URL` | Backend API URL | Yes | `https://your-service.onrender.com` |

## Troubleshooting

### Backend Issues

1. **Service Account Not Working**
   - Verify the service account email has access to the Google Drive file
   - Check that the JSON content is correctly formatted in environment variables

2. **CORS Errors**
   - Ensure `CORS_ORIGINS` includes your frontend URL
   - Check that the URL doesn't have a trailing slash

3. **Module Not Found**
   - Verify `requirements.txt` includes all dependencies
   - Check that the build command runs successfully

### Frontend Issues

1. **API Connection Failed**
   - Verify `VITE_API_URL` is set correctly
   - Check that the backend is running and accessible
   - Verify CORS is configured correctly

2. **Build Errors**
   - Check that all dependencies are in `package.json`
   - Verify Node.js version compatibility

## Security Notes

1. **Never commit sensitive files**:
   - `.env`
   - `service_account.json`
   - Any files containing passwords or API keys

2. **Use strong passwords** for admin panel

3. **Enable HTTPS** (automatic on Render and Vercel)

4. **Regularly rotate** service account keys and admin passwords

## Support

For issues or questions:
- Check the logs in Render dashboard
- Check the logs in Vercel dashboard
- Review the README.md files in backend and root directory

