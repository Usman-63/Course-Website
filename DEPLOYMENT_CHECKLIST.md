# Deployment Checklist

Use this checklist before deploying to ensure everything is ready.

## Pre-Deployment

### Backend (Render)

- [ ] Google Cloud Project created
- [ ] Google Drive API enabled
- [ ] Service Account created with Drive API access
- [ ] Service Account JSON downloaded
- [ ] Google Drive file created and shared with service account email
- [ ] Google Drive file ID copied
- [ ] Admin password chosen (strong password)
- [ ] Frontend URL(s) known for CORS configuration

### Frontend (Vercel)

- [ ] Backend URL known (will be provided by Render)
- [ ] All environment variables documented

### GitHub

- [ ] `.env` files are in `.gitignore`
- [ ] `service_account.json` is in `.gitignore`
- [ ] All sensitive data excluded from repository
- [ ] Code is committed and pushed to GitHub

## Deployment Steps

### 1. Deploy Backend to Render

1. [ ] Go to https://render.com and sign in
2. [ ] Click "New" > "Web Service"
3. [ ] Connect your GitHub repository
4. [ ] Configure:
   - Name: `course-website-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Root Directory: `backend`
5. [ ] Add Environment Variables:
   - `GOOGLE_DRIVE_FILE_ID`: [Your file ID]
   - `ADMIN_PASSWORD`: [Your password]
   - `CORS_ORIGINS`: [Your frontend URL, e.g., `https://your-app.vercel.app`]
   - `SERVICE_ACCOUNT_JSON`: [Paste entire JSON content]
   - `PYTHON_VERSION`: `3.11.0`
6. [ ] Click "Create Web Service"
7. [ ] Wait for deployment to complete
8. [ ] Test health endpoint: `https://your-service.onrender.com/health`
9. [ ] Copy the service URL (e.g., `https://your-service.onrender.com`)

### 2. Deploy Frontend to Vercel

1. [ ] Go to https://vercel.com and sign in
2. [ ] Click "New Project"
3. [ ] Import your GitHub repository
4. [ ] Configure:
   - Framework Preset: `Vite`
   - Root Directory: `.` (or leave default)
   - Build Command: `npm run build` (auto-detected)
   - Output Directory: `dist` (auto-detected)
5. [ ] Add Environment Variable:
   - `VITE_API_URL`: [Your Render backend URL from step 1]
6. [ ] Click "Deploy"
7. [ ] Wait for deployment to complete
8. [ ] Copy the frontend URL (e.g., `https://your-app.vercel.app`)

### 3. Update Backend CORS

1. [ ] Go back to Render dashboard
2. [ ] Edit your web service
3. [ ] Update `CORS_ORIGINS` environment variable:
   - Add your Vercel URL: `https://your-app.vercel.app`
   - If you have a custom domain, add that too
   - Format: `https://app1.vercel.app,https://app2.vercel.app`
4. [ ] Save changes (this will trigger a redeploy)

### 4. Final Testing

- [ ] Visit frontend URL
- [ ] Test course content loads
- [ ] Test admin panel login at `/admin`
- [ ] Test creating/editing modules
- [ ] Test creating/editing links
- [ ] Test updating pricing
- [ ] Test schedule display
- [ ] Check browser console for errors
- [ ] Test on mobile device

## Post-Deployment

- [ ] Document your URLs
- [ ] Set up custom domain (if needed)
- [ ] Configure SSL (automatic on Render/Vercel)
- [ ] Set up monitoring/alerts
- [ ] Test admin panel functionality
- [ ] Verify Google Drive integration works

## Troubleshooting

### Backend Issues

**Service Account Error:**
- Verify SERVICE_ACCOUNT_JSON is correctly formatted
- Check that service account email has access to Google Drive file
- Ensure JSON is pasted as a single line or properly escaped

**CORS Errors:**
- Verify CORS_ORIGINS includes exact frontend URL (no trailing slash)
- Check that frontend URL matches exactly (http vs https)

**Module Not Found:**
- Check requirements.txt is complete
- Verify build command runs successfully
- Check Render build logs

### Frontend Issues

**API Connection Failed:**
- Verify VITE_API_URL is set correctly
- Check backend is running and accessible
- Verify CORS is configured
- Check browser console for specific error

**Build Errors:**
- Check all dependencies in package.json
- Verify Node.js version compatibility
- Check Vercel build logs

## Security Reminders

- [ ] Never commit `.env` files
- [ ] Never commit `service_account.json`
- [ ] Use strong admin password
- [ ] Regularly rotate service account keys
- [ ] Monitor access logs
- [ ] Keep dependencies updated

## Support Resources

- Render Documentation: https://render.com/docs
- Vercel Documentation: https://vercel.com/docs
- Google Drive API: https://developers.google.com/drive/api
- Project README: See README.md
- Deployment Guide: See backend/DEPLOYMENT.md

