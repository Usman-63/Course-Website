# Gemini 3 Masterclass Course Website

A modern course website with admin panel for managing course content, modules, links, and pricing.

## Features

- 🎓 Dynamic course content management
- 📝 Admin panel for content editing
- 💰 Flexible pricing tiers with features
- 📅 Schedule information display
- 🔗 Resource links management
- 📱 Responsive design
- ⚡ Fast and modern UI

## Tech Stack

### Frontend
- React + TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- React Router
- Lucide React Icons

### Backend
- Python Flask
- Google Drive API (for data storage)
- Flask-CORS
- Gunicorn (production server)

## Project Structure

```
course-website/
├── backend/          # Flask backend API
│   ├── app.py       # Main Flask application
│   ├── routes.py    # API routes
│   ├── google_drive.py  # Google Drive integration
│   ├── auth.py      # Admin authentication
│   ├── requirements.txt
│   ├── Procfile     # For Render deployment
│   └── render.yaml  # Render configuration
├── src/             # React frontend
│   ├── components/  # React components
│   ├── pages/       # Page components
│   ├── services/    # API services
│   └── layouts/     # Layout components
└── public/          # Static assets
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Google Cloud Project with Drive API enabled
- Service Account with Drive API access

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```env
VITE_API_URL=http://localhost:5000
```

3. Start development server:
```bash
npm run dev
```

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file (see `backend/.env.example`):
```env
GOOGLE_DRIVE_FILE_ID=your_file_id
ADMIN_PASSWORD=your_password
CORS_ORIGINS=http://localhost:5173
```

5. Add `service_account.json` file (from Google Cloud Console)

6. Run the server:
```bash
python app.py
```

## Deployment

See [backend/DEPLOYMENT.md](./backend/DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy

**Backend (Render):**
1. Push code to GitHub
2. Connect repository to Render
3. Set environment variables
4. Deploy

**Frontend (Vercel):**
1. Push code to GitHub
2. Connect repository to Vercel
3. Set `VITE_API_URL` environment variable
4. Deploy

## Environment Variables

### Frontend
- `VITE_API_URL`: Backend API URL

### Backend
- `GOOGLE_DRIVE_FILE_ID`: Google Drive file ID
- `ADMIN_PASSWORD`: Admin panel password
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)
- `SERVICE_ACCOUNT_JSON`: Service account JSON (alternative to file)
- `PORT`: Server port (default: 5000)

## Admin Panel

Access the admin panel at `/admin` to:
- Manage course modules
- Add/edit/delete links
- Configure pricing tiers
- Update schedule information

## License

Private project - All rights reserved
