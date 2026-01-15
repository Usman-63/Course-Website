import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, MessageSquare, LogOut } from 'lucide-react';
import WeChatModal from '../components/WeChatModal';
import { useAuth } from '../contexts/AuthContext';
import { auth } from '../services/firebase';
import { signOut } from 'firebase/auth';
import { clearAuthToken } from '../services/api';

const MainLayout: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showWeChat, setShowWeChat] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { currentUser, userProfile } = useAuth();

  const isActivated = userProfile?.isActive === true || userProfile?.role === 'admin' || currentUser?.uid === 'admin-user';

  const handleLogout = async () => {
    try {
      clearAuthToken(); // Clear admin token if present
      await signOut(auth);
      navigate('/');
    } catch (error) {
      console.error("Failed to log out", error);
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    setMobileMenuOpen(false);
    window.scrollTo(0, 0);
  }, [location]);

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: isActivated ? 'Dashboard' : 'Syllabus', path: isActivated ? '/dashboard' : '/syllabus' },
    { name: 'Pricing', path: '/register' }, // Linking to register page for pricing
  ];

  return (
    <div className="min-h-screen bg-navy text-white font-sans selection:bg-primary selection:text-navy">
      {/* Navigation */}
      <nav 
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled ? 'bg-navy/80 backdrop-blur-md py-4 shadow-lg border-b border-white/5' : 'bg-transparent py-6'
        }`}
      >
        <div className="container mx-auto px-4 md:px-6 flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold tracking-tighter flex items-center gap-2 group">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center transform group-hover:rotate-12 transition-transform">
              <span className="text-navy font-bold text-lg">G3</span>
            </div>
            <span className="text-white font-display">Gemini<span className="text-primary">Masterclass</span></span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link 
                key={link.name} 
                to={link.path}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  location.pathname === link.path ? 'text-primary' : 'text-gray-300'
                }`}
              >
                {link.name}
              </Link>
            ))}
            {currentUser ? (
              <button 
                onClick={handleLogout}
                className="flex items-center gap-2 bg-white/10 text-white px-5 py-2.5 rounded-full font-bold text-sm hover:bg-white/20 transition-all"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            ) : (
              <Link 
                to="/register" 
                className="bg-primary text-navy px-5 py-2.5 rounded-full font-bold text-sm hover:bg-primary-hover transition-transform hover:scale-105 active:scale-95"
              >
                Enroll Now
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden text-white p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed inset-0 z-40 bg-navy pt-24 px-6 md:hidden"
          >
            <div className="flex flex-col gap-6 text-center">
              {navLinks.map((link) => (
                <Link 
                  key={link.name} 
                  to={link.path}
                  className="text-2xl font-medium text-white hover:text-primary"
                >
                  {link.name}
                </Link>
              ))}
              {currentUser ? (
                <button 
                  onClick={() => {
                    handleLogout();
                    setMobileMenuOpen(false);
                  }}
                  className="bg-white/10 text-white px-6 py-4 rounded-xl font-bold text-xl mt-4 flex items-center justify-center gap-2"
                >
                  <LogOut className="w-5 h-5" />
                  Logout
                </button>
              ) : (
                <Link 
                  to="/register" 
                  className="bg-primary text-navy px-6 py-4 rounded-xl font-bold text-xl mt-4"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Enroll Now
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Page Content */}
      <main className="pt-0">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-navy-light py-12 border-t border-white/5 mt-20">
        <div className="container mx-auto px-4 md:px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
            <div className="col-span-1 md:col-span-2">
              <Link to="/" className="text-2xl font-bold tracking-tighter flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-navy font-bold text-lg">G3</span>
                </div>
                <span className="text-white font-display">Gemini<span className="text-primary">Masterclass</span></span>
              </Link>
              <p className="text-gray-400 max-w-sm">
                Master the full capabilities of Gemini 3 Pro, NotebookLM, and Antigravity. From idea to build in 3 weeks.
              </p>
            </div>
            
            <div>
              <h4 className="font-bold text-white mb-4">Links</h4>
              <ul className="space-y-2">
                {navLinks.map((link) => (
                  <li key={link.name}>
                    <Link to={link.path} className="text-gray-400 hover:text-primary text-sm transition-colors">
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-white mb-4">Contact</h4>
              <p className="text-gray-400 text-sm mb-2">Have questions?</p>
              <div className="flex flex-col gap-2">
                <button 
                  onClick={() => setShowWeChat(true)}
                  className="text-gray-400 hover:text-primary text-sm flex items-center gap-2 transition-colors text-left"
                >
                  <MessageSquare className="w-4 h-4" />
                  Connect on WeChat
                </button>
              </div>
            </div>
          </div>
          
          <div className="border-t border-white/5 mt-12 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-500 text-sm">
              © {new Date().getFullYear()} Gemini 3 Masterclass. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
      <WeChatModal isOpen={showWeChat} onClose={() => setShowWeChat(false)} />
    </div>
  );
};

export default MainLayout;