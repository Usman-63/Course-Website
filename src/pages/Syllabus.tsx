import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Circle, Lock } from 'lucide-react';
import { getCourseData, CourseModule } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Syllabus: React.FC = () => {
  const { currentUser, userProfile } = useAuth();
  const navigate = useNavigate();
  const [modules, setModules] = useState<CourseModule[]>([]);
  const [loading, setLoading] = useState(true);
  
  const isActivated = userProfile?.isActive === true || userProfile?.role === 'admin' || currentUser?.uid === 'admin-user';

  useEffect(() => {
    if (isActivated) {
      navigate('/dashboard');
      return;
    }

    const fetchData = async () => {
      try {
        const data = await getCourseData();
        setModules((data.modules || []).filter(m => m.isVisible !== false));
      } catch (error) {
        console.error('Failed to load course data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [currentUser, isActivated, navigate]);

  if (loading || isActivated) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center pt-20">
        <Loader2 className="w-12 h-12 text-yellow animate-spin" />
      </div>
    );
  }

  return (
    <div className="pt-20 pb-24">
      <div className="container mx-auto px-4 md:px-6">
        {/* Header */}
        <div className="text-center mb-12 pt-10">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
            Course Curriculum
          </h1>
          
          {currentUser ? (
            <div className="max-w-xl mx-auto bg-navy-light p-6 rounded-2xl border border-white/10 shadow-lg">
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center gap-2 text-sm text-blue-300">
                 <Lock className="w-4 h-4 shrink-0" />
                 <span>Account pending activation. Content is currently read-only.</span>
              </div>
            </div>
          ) : (
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              As your instructor for the Gemini 3 Masterclass, Andrew bridges the gap between cutting-edge AI research and real world application.
            </p>
          )}
        </div>

        {/* Timeline / Modules */}
        <div className="max-w-4xl mx-auto space-y-12 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">
          {modules.sort((a, b) => (a.order || 0) - (b.order || 0)).map((week, index) => (
            <motion.div 
              key={week.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: index * 0.1 }}
              className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group"
            >
              {/* Icon */}
              <div className="flex items-center justify-center w-10 h-10 rounded-full border shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors bg-navy border-white/10 text-gray-400 group-hover:border-yellow group-hover:text-yellow">
                <span className="font-bold text-sm">{index + 1}</span>
              </div>
              
              {/* Content Card */}
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-navy-light p-6 md:p-8 rounded-2xl border transition-all shadow-xl border-white/5 hover:border-yellow/30">
                <div className="flex items-center justify-between mb-4">
                  <span className="inline-block px-3 py-1 bg-white/5 rounded-full text-xs font-medium text-gray-400">
                    Week {index + 1}
                  </span>
                  
                  {currentUser && (
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-600 cursor-not-allowed">
                      Mark Complete
                      <Circle className="w-4 h-4" />
                    </div>
                  )}
                </div>
                
                <h3 className="text-2xl font-bold text-white mb-3">{week.title}</h3>
                <p className="text-gray-400 mb-6 text-sm md:text-base">Focus: {week.focus}</p>
                
                <ul className="space-y-3 mb-6">
                  {week.topics.map((topic, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-gray-300">
                      <div className="mt-1 w-1.5 h-1.5 rounded-full shrink-0 bg-yellow"></div>
                      {topic}
                    </li>
                  ))}
                </ul>
                
                {currentUser && (
                  <div className="pt-4 border-t border-white/5 text-center">
                    <p className="text-xs text-gray-500 italic flex items-center justify-center gap-1">
                      <Lock className="w-3 h-3" /> Locked until activation
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Syllabus;
