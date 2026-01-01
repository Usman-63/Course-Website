import React from 'react';
import HeroSection from './components/HeroSection';
import RegistrationForm from './components/RegistrationForm';
import CourseContentLinks from './components/CourseContentLinks';

function App() {
  return (
    <div className="min-h-screen bg-white font-sans text-gray-900">
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
