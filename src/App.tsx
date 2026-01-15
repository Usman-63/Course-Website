import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import MainLayout from './layouts/MainLayout';
import { Loader2 } from 'lucide-react';

import AdminLayout from './layouts/AdminLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import CourseContent from './pages/admin/CourseContent';
import Engagement from './pages/admin/Engagement';
import StudentManager from './components/admin/StudentManager';
import StudentOperationsManager from './components/admin/StudentOperationsManager';
import AdminLogin from './components/AdminLogin';

// Lazy load pages for code splitting
const Home = lazy(() => import('./pages/Home'));
const Syllabus = lazy(() => import('./pages/Syllabus'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ModuleDetails = lazy(() => import('./pages/ModuleDetails'));
const Register = lazy(() => import('./pages/Register'));
const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));

const LoadingFallback = () => (
  <div className="min-h-screen bg-navy flex items-center justify-center">
    <Loader2 className="w-12 h-12 text-primary animate-spin" />
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <Router>
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                {/* Public / Student Routes */}
                <Route path="/" element={<MainLayout />}>
                  <Route index element={<Home />} />
                  <Route path="syllabus" element={<Syllabus />} />
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="module/:moduleId" element={<ModuleDetails />} />
                  <Route path="register" element={<Register />} />
                  <Route path="login" element={<Login />} />
                  <Route path="signup" element={<Signup />} />
                </Route>
                
                {/* Admin Routes */}
                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin" element={<AdminLayout />}>
                  <Route index element={<AdminDashboard />} />
                  <Route path="content" element={<CourseContent />} />
                  <Route path="students" element={<StudentManager />} />
                  <Route path="operations" element={<StudentOperationsManager />} />
                  <Route path="engagement" element={<Engagement />} />
                </Route>
              </Routes>
            </Suspense>
          </Router>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
