# Gemini 3 Masterclass - Course Website

A modern, responsive course landing page built with React, TypeScript, and Vite. Features a hero section, course content links, and integration with Google Forms for registration.

## 🚀 Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Lucide React** - Icons

## 📦 Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🎨 Features

- **Hero Section** - Eye-catching branding with yellow/navy theme
- **Course Content Links** - Dynamic grid of course materials
- **Registration Link** - Direct link to Google Forms registration
- **Responsive Design** - Works on all devices
- **Smooth Animations** - Framer Motion powered transitions

## 🌐 Deployment to Vercel

This project is configured for easy deployment to Vercel.

### Option 1: Deploy via Vercel CLI

```bash
# Install Vercel CLI globally
npm i -g vercel

# Deploy
vercel

# Deploy to production
vercel --prod
```

### Option 2: Deploy via GitHub

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Import your GitHub repository
5. Vercel will auto-detect Vite and configure everything
6. Click "Deploy"

### Configuration

The `vercel.json` file is already configured with:
- ✅ Build command: `npm run build`
- ✅ Output directory: `dist`
- ✅ SPA routing (all routes redirect to index.html)
- ✅ Asset caching headers

## 📁 Project Structure

```
├── src/
│   ├── components/      # React components
│   │   ├── HeroSection.tsx
│   │   ├── CourseContentLinks.tsx
│   │   └── RegistrationForm.tsx
│   ├── data/           # Data files
│   │   └── links.ts    # Course content links
│   ├── assets/         # Images and static assets
│   ├── App.tsx         # Main app component
│   └── main.tsx        # Entry point
├── public/             # Public assets
├── dist/               # Build output (generated)
├── vercel.json         # Vercel configuration
└── package.json        # Dependencies
```

## 🔧 Configuration

### Adding Course Links

Edit `src/data/links.ts` to add or modify course content links:

```typescript
export const courseLinks: CourseLink[] = [
  {
    id: '1',
    title: 'Course Syllabus',
    url: 'https://...',
    description: 'Detailed breakdown...'
  },
  // Add more links here
];
```

### Updating Registration Form

The registration link is in `src/data/links.ts` with the title "Register Now". Update the URL if the Google Form changes.

## 🎯 Environment Variables

No environment variables are required for this project. All configuration is in the codebase.

## 📝 License

Private project - All rights reserved.

---

Built with ❤️ for Gemini 3 Masterclass
