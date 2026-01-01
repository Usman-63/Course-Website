import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import HeroSection from './components/HeroSection';
import CourseContentLinks from './components/CourseContentLinks';
import { BarChart3, X } from 'lucide-react';

function App() {
  const [showComingSoon, setShowComingSoon] = useState(false);

  return (
    <div className="min-h-screen bg-white font-sans text-gray-900">
      {/* Track Progress Button - Top Right */}
      <motion.button
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5 }}
        onClick={() => setShowComingSoon(true)}
        className="fixed top-4 right-4 z-50 bg-yellow text-navy px-4 py-2 rounded-lg font-semibold shadow-lg hover:bg-yellow/90 transition-colors flex items-center gap-2"
      >
        <BarChart3 className="w-5 h-5" />
        Track your progress
      </motion.button>

      {/* Coming Soon Modal */}
      <AnimatePresence>
        {showComingSoon && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowComingSoon(false)}
              className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 relative"
              >
                <button
                  onClick={() => setShowComingSoon(false)}
                  className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
                <div className="text-center">
                  <div className="w-16 h-16 bg-yellow rounded-full flex items-center justify-center mx-auto mb-4">
                    <BarChart3 className="w-8 h-8 text-navy" />
                  </div>
                  <h2 className="text-2xl font-bold text-navy mb-2">Coming Soon</h2>
                  <p className="text-gray-600">
                    The progress tracking feature is currently under development. Check back soon!
                  </p>
                </div>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <HeroSection />
      
      <main>
        <CourseContentLinks />
      </main>
      
      <footer className="bg-navy text-white py-8 text-center">
        <div className="container mx-auto px-4">
          <p className="opacity-75">© {new Date().getFullYear()} Gemini 3 Masterclass. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
