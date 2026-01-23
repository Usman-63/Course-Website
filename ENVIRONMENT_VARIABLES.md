# Environment Variables Guide

This document lists all environment variables needed for deployment on **Vercel** (frontend) and **Render** (backend).

---

## 🔵 Vercel (Frontend) Environment Variables

Set these in your Vercel project settings under **Settings → Environment Variables**:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL (your Render service URL) | `https://your-backend.onrender.com` |
| `VITE_FIREBASE_API_KEY` | Firebase Web API Key | `AIzaSy...` |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase Auth Domain | `your-project.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | Firebase Project ID | `your-project-id` |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase Storage Bucket | `your-project.appspot.com` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Firebase Messaging Sender ID | `123456789` |
| `VITE_FIREBASE_APP_ID` | Firebase App ID | `1:123456789:web:abc123` |

### How to Get Firebase Config

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** (gear icon)
4. Scroll to **Your apps** section
5. Click on your web app (or create one)
6. Copy the config values from the `firebaseConfig` object

---

## 🔴 Render (Backend) Environment Variables

Set these in your Render service settings under **Environment** tab:

### Required Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `ADMIN_PASSWORD` | Password for admin panel access | ✅ Yes | `your-secure-password-123` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | ✅ Yes | `https://your-app.vercel.app,https://www.yourdomain.com` |
| `JWT_SECRET_KEY` | Secret key for JWT token generation | ✅ Yes | `your-random-secret-key-here` |
| `GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID` | Google Sheets Survey Spreadsheet ID | ✅ Yes | `1vfePpeAynCBgUNobLc3tD3j42PsgaFgg` |
| `GOOGLE_SHEETS_REGISTER_SPREADSHEET_ID` | Google Sheets Registration Spreadsheet ID | ✅ Yes | `1vfePpeAynCBgUNobLc3tD3j42PsgaFgg` |

### Google Service Account (Choose ONE method)

**Option 1: Base64 Encoded JSON (Recommended for Render)**
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SERVICE_ACCOUNT_BASE64` | Base64-encoded service account JSON | ✅ Yes* | `eyJ0eXAiOiJKV1QiLCJhbGc...` |

**Option 2: Raw JSON String**
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SERVICE_ACCOUNT_JSON` | Raw service account JSON content | ✅ Yes* | `{"type":"service_account","project_id":"..."}` |

*Required if not using `FIREBASE_SERVICE_ACCOUNT_BASE64` or `FIREBASE_SERVICE_ACCOUNT_PATH`

### Firebase Admin SDK (Choose ONE method)

**Option 1: Base64 Encoded JSON (Recommended for Render)**
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `FIREBASE_SERVICE_ACCOUNT_BASE64` | Base64-encoded Firebase service account JSON | ✅ Yes* | `eyJ0eXAiOiJKV1QiLCJhbGc...` |

**Option 2: Raw JSON String**
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Raw Firebase service account JSON | ✅ Yes* | `{"type":"service_account","project_id":"..."}` |

**Option 3: File Path (Local Development Only)**
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to Firebase service account JSON file | ❌ No | `./serviceAccountKey.json` |

*At least one Firebase credential method is required for Firestore operations

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PORT` | Server port | `5000` | `10000` (Render sets this automatically) |
| `FLASK_ENV` | Flask environment | `production` | `development` |
| `FLASK_DEBUG` | Enable Flask debug mode | `False` | `True` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `GOOGLE_SHEETS_SURVEY_WORKSHEET` | Survey worksheet name | `Form Responses 1` | `Survey Responses` |
| `GOOGLE_SHEETS_REGISTER_WORKSHEET` | Registration worksheet name | `Form Responses 1` | `Registration Responses` |
| `GOOGLE_SHEETS_CLASSES_WORKSHEET` | Classes worksheet name | `Classes` | `Class Schedule` |

### Deprecated Variables (No Longer Used)

These are kept for backward compatibility but are **not required**:
- `GOOGLE_DRIVE_FILE_ID` - Course data is now in Firestore
- `GOOGLE_SERVICE_ACCOUNT_PATH` - Use `SERVICE_ACCOUNT_BASE64` or `SERVICE_ACCOUNT_JSON` instead

---

## 📋 Quick Setup Checklist

### Vercel Setup
- [ ] Set `VITE_API_URL` to your Render backend URL
- [ ] Set all 6 Firebase config variables (`VITE_FIREBASE_*`)
- [ ] Redeploy after setting variables

### Render Setup
- [ ] Set `ADMIN_PASSWORD` (strong password)
- [ ] Set `CORS_ORIGINS` (include your Vercel URL)
- [ ] Set `JWT_SECRET_KEY` (random secure string)
- [ ] Set `GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID`
- [ ] Set `GOOGLE_SHEETS_REGISTER_SPREADSHEET_ID`
- [ ] Set `SERVICE_ACCOUNT_BASE64` or `SERVICE_ACCOUNT_JSON` (for Google Sheets)
- [ ] Set `FIREBASE_SERVICE_ACCOUNT_BASE64` or `FIREBASE_SERVICE_ACCOUNT_JSON` (for Firestore)
- [ ] Redeploy after setting variables

---

## 🔐 How to Generate Required Values

### 1. Generate JWT_SECRET_KEY

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

### 2. Get Google Sheets Spreadsheet IDs

1. Open your Google Sheet
2. Look at the URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Copy the `SPREADSHEET_ID` part

### 3. Get Service Account JSON

**For Google Sheets/Drive:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin** → **Service Accounts**
5. Create a service account or use existing
6. Create a key (JSON format)
7. Download the JSON file

**For Firebase Admin:**
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. Download the JSON file

### 4. Encode Service Account JSON to Base64

**On Mac/Linux:**
```bash
base64 -i service_account.json
```

**On Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("service_account.json"))
```

**Or use online tool:**
- https://www.base64encode.org/

---

## ⚠️ Important Notes

1. **Never commit** environment variables to Git
2. **Use strong passwords** for `ADMIN_PASSWORD`
3. **Generate secure random strings** for `JWT_SECRET_KEY`
4. **Update CORS_ORIGINS** after deploying frontend to include your Vercel URL
5. **Share Google Sheets** with the service account email (found in the JSON file)
6. **Redeploy** both services after changing environment variables

---

## 🔄 After Deployment

1. **Test Backend Health:**
   ```
   https://your-backend.onrender.com/health
   ```

2. **Test Frontend:**
   - Visit your Vercel URL
   - Try logging into admin panel

3. **Check Logs:**
   - Render: Service → **Logs** tab
   - Vercel: Project → **Deployments** → Click deployment → **View Function Logs**

---

## 🆘 Troubleshooting

### Backend Issues

**"CORS_ORIGINS environment variable must be set"**
- Set `CORS_ORIGINS` in Render environment variables
- Include your Vercel URL (no trailing slash)

**"JWT_SECRET_KEY environment variable must be set"**
- Set `JWT_SECRET_KEY` in Render environment variables
- Generate a secure random string

**"Firebase Admin not initialized"**
- Set `FIREBASE_SERVICE_ACCOUNT_BASE64` or `FIREBASE_SERVICE_ACCOUNT_JSON`
- Verify the JSON is valid

**"GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID environment variable is required"**
- Set `GOOGLE_SHEETS_SURVEY_SPREADSHEET_ID` in Render
- Verify the spreadsheet ID is correct

### Frontend Issues

**"Firebase config missing"**
- Set all `VITE_FIREBASE_*` variables in Vercel
- Redeploy after setting variables

**"API connection failed"**
- Verify `VITE_API_URL` is set correctly
- Check that backend is running
- Verify CORS is configured correctly
