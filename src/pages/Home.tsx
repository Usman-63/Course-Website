import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Zap, BookOpen, Users, BarChart, X, Megaphone } from 'lucide-react';
import frontImage from '../assets/front.png';
import andrewImage from '../assets/andrew.png';
import WeChatModal from '../components/WeChatModal';
import { useAuth } from '../contexts/AuthContext';

const Home: React.FC = () => {
  const { currentUser, userProfile } = useAuth();
  const navigate = useNavigate();
  const [showComingSoon, setShowComingSoon] = useState(false);
  const [showWeChat, setShowWeChat] = useState(false);

  const isActivated = userProfile?.isActive === true || userProfile?.role === 'admin' || currentUser?.uid === 'admin-user';

  const handleTrackProgress = () => {
    if (currentUser) {
      if (isActivated) {
        navigate('/dashboard');
      } else {
        navigate('/syllabus');
      }
    } else {
      setShowComingSoon(true);
    }
  };

  return (
    <>
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center pt-20 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-yellow/10 rounded-full blur-[120px] -mr-20 -mt-20"></div>
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-500/10 rounded-full blur-[100px] -ml-20 -mb-20"></div>
          <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-[0.03]"></div>
        </div>

        <div className="container mx-auto px-4 md:px-6 relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="order-2 lg:order-1">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <h1 className="text-5xl md:text-7xl font-bold text-white leading-[1.1] mb-6 tracking-tight">
                Master AI with <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow to-yellow-hover">Gemini 3 Pro</span>
              </h1>
              <p className="text-xl text-gray-300 mb-8 max-w-lg leading-relaxed">
                From Idea to Build in 3 Weeks. Learn to build logical reasoning paths, summarize instantly, and use AI agents to create for you.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <button 
                  onClick={handleTrackProgress}
                  className="inline-flex items-center justify-center px-8 py-4 bg-yellow text-navy font-bold rounded-xl hover:bg-yellow-hover transition-all transform hover:scale-105 shadow-lg shadow-yellow/20"
                >
                  Track Progress
                  <BarChart className="ml-2 w-5 h-5" />
                </button>
                {!currentUser && (
                  <Link 
                    to="/syllabus" 
                    className="inline-flex items-center justify-center px-8 py-4 bg-white/5 text-white font-medium rounded-xl hover:bg-white/10 transition-all border border-white/10 backdrop-blur-sm"
                  >
                    View Syllabus
                  </Link>
                )}
              </div>
            </motion.div>
          </div>

          <div className="order-1 lg:order-2 relative">
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="relative z-10"
            >
              <div className="relative rounded-2xl overflow-hidden shadow-2xl border border-white/10 aspect-[4/3] group">
                 <div className="absolute inset-0 bg-gradient-to-t from-navy/80 to-transparent z-10"></div>
                 <img 
                   src={frontImage} 
                   alt="Gemini Masterclass Interface" 
                   className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700"
                 />
              </div>
            </motion.div>
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] border border-white/5 rounded-full -z-10 animate-[spin_60s_linear_infinite]"></div>
          </div>
        </div>
      </section>

      {/* Coming Soon Modal */}
      <AnimatePresence>
        {showComingSoon && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowComingSoon(false)}
            className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-navy rounded-2xl shadow-2xl max-w-md w-full p-8 relative border-2 border-yellow"
            >
              <button
                onClick={() => setShowComingSoon(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-yellow transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
              
              <div className="text-center">
                <div className="w-16 h-16 bg-yellow/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-yellow/20">
                  <BarChart className="w-8 h-8 text-yellow" />
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-2">Track Your Progress</h2>
                
                <p className="text-gray-300 mb-8 leading-relaxed">
                  Log in or create an account to track your progress, submit homework, and join the community discussion.
                </p>
                
                <div className="flex flex-col gap-3">
                  <Link 
                    to="/signup" 
                    onClick={() => setShowComingSoon(false)}
                    className="w-full py-3 bg-yellow text-navy font-bold rounded-xl hover:bg-yellow-hover transition-colors"
                  >
                    Create Account
                  </Link>
                  <Link 
                    to="/login" 
                    onClick={() => setShowComingSoon(false)}
                    className="w-full py-3 bg-white/5 text-white font-bold rounded-xl hover:bg-white/10 transition-colors"
                  >
                    Log In
                  </Link>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bento Grid Features */}
      <section className="py-24 bg-navy-light/30">
        <div className="container mx-auto px-4 md:px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">Why This Masterclass?</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              We don't just teach prompts. We teach you how to build intelligent systems using the most advanced Google AI stack.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 bg-navy p-8 rounded-3xl border border-white/5 hover:border-yellow/30 transition-colors group">
              <div className="w-12 h-12 bg-blue-500/20 rounded-2xl flex items-center justify-center mb-6 text-blue-400 group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">The Reasoning Engine</h3>
              <p className="text-gray-400 leading-relaxed">
                Move beyond simple chatbots. Learn to construct complex logical reasoning chains that allow AI to solve multi-step problems with high accuracy.
              </p>
            </div>

            <div className="bg-navy p-8 rounded-3xl border border-white/5 hover:border-yellow/30 transition-colors group">
              <div className="w-12 h-12 bg-purple-500/20 rounded-2xl flex items-center justify-center mb-6 text-purple-400 group-hover:scale-110 transition-transform">
                <BookOpen className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">NotebookLM</h3>
              <p className="text-gray-400 leading-relaxed">
                Turn your documents into an intelligent knowledge base. Summarize hundreds of sources instantly.
              </p>
            </div>

            <div className="bg-navy p-8 rounded-3xl border border-white/5 hover:border-yellow/30 transition-colors group">
              <div className="w-12 h-12 bg-green-500/20 rounded-2xl flex items-center justify-center mb-6 text-green-400 group-hover:scale-110 transition-transform">
                <Users className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">Agentic Builder</h3>
              <p className="text-gray-400 leading-relaxed">
                Master Google Antigravity. Build autonomous agents that can execute tasks, write code, and deploy web apps for you.
              </p>
            </div>

            <div className="md:col-span-2 bg-gradient-to-r from-yellow/10 to-navy p-8 rounded-3xl border border-white/5 hover:border-yellow/30 transition-colors relative overflow-hidden">
               <div className="relative z-10">
                 <h3 className="text-2xl font-bold text-white mb-3">3 Weeks to Mastery</h3>
                 <p className="text-gray-300 max-w-md">
                   An intensive, project-based curriculum designed for professionals who want to lead in the AI era, not just follow.
                 </p>
                 {currentUser && isActivated ? (
                   <Link to="/dashboard" className="inline-flex items-center text-yellow font-bold mt-6 hover:underline">
                     View Full Curriculum <ArrowRight className="w-4 h-4 ml-2" />
                   </Link>
                 ) : (
                   <Link to="/syllabus" className="inline-flex items-center text-yellow font-bold mt-6 hover:underline">
                     View Full Curriculum <ArrowRight className="w-4 h-4 ml-2" />
                   </Link>
                 )}
               </div>
               <div className="absolute right-0 bottom-0 opacity-20 transform translate-x-1/4 translate-y-1/4">
                 <div className="w-64 h-64 bg-yellow rounded-full blur-[80px]"></div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* Instructor Section */}
      <section className="py-24 relative overflow-hidden">
        <div className="container mx-auto px-4 md:px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            {/* Left: Circular Photo with Instructor Button */}
            <div className="order-1 md:order-1 flex flex-col items-center md:items-start">
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                className="relative"
              >
                <div className="relative w-64 h-64 md:w-80 md:h-80">
                  <img 
                    src={andrewImage} 
                    alt="Andrew - Instructor" 
                    className="w-full h-full rounded-full object-cover border-4 border-yellow/30 shadow-2xl" 
                  />
                </div>
                <div className="mt-6 flex justify-center md:justify-start">
                  <div className="px-4 py-2 bg-yellow text-navy font-bold rounded-lg shadow-lg">
                    Instructor
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Right: Content */}
            <div className="order-2 md:order-2">
              <motion.div 
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Meet Your Instructor</h2>
                <p className="text-yellow text-xl font-semibold mb-6">Andrew, CEO of Azure Partners</p>
                <p className="text-white text-lg mb-6 leading-relaxed">
                  AI strategist and author with experience at Amazon, IBM, and multiple startups. Currently leads the AI Mastery program at Columbia University and advises global startups on AI innovation.
                </p>
                <p className="text-gray-400 text-base mb-8 italic leading-relaxed">
                  "My goal is to demystify the complex world of Large Language Models and give you practical, build-ready skills that you can apply immediately."
                </p>
                
                {/* Affiliation Buttons */}
                <div className="flex flex-wrap gap-3 mb-8">
                  <div className="px-4 py-2 bg-navy-light border border-white/10 rounded-lg text-white text-sm font-medium">
                    Amazon
                  </div>
                  <div className="px-4 py-2 bg-navy-light border border-white/10 rounded-lg text-white text-sm font-medium">
                    IBM
                  </div>
                  <div className="px-4 py-2 bg-navy-light border border-white/10 rounded-lg text-white text-sm font-medium">
                    Columbia University
                  </div>
                </div>

                {/* WeChat Button */}
                <button 
                  onClick={() => setShowWeChat(true)}
                  className="inline-flex items-center gap-2 text-yellow font-semibold hover:text-yellow-hover transition-colors"
                >
                  <Megaphone className="w-5 h-5" />
                  Connect on WeChat
                </button>
              </motion.div>
            </div>
          </div>
        </div>
      </section>
      
      <WeChatModal isOpen={showWeChat} onClose={() => setShowWeChat(false)} />
    </>
  );
};

export default Home;
