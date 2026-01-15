import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Play, 
  FileText, 
  CheckCircle, 
  ChevronLeft, 
  X
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/Toast';
import { db } from '../services/firebase';
import { doc, getDoc, updateDoc } from 'firebase/firestore';
import { getCourseData, CourseModule } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

const ModuleDetails: React.FC = () => {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const toast = useToast();
  
  const [module, setModule] = useState<CourseModule | null>(null);
  const [loading, setLoading] = useState(true);
  const [submissions, setSubmissions] = useState<Record<string, string>>({});
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [submissionValues, setSubmissionValues] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch course data to find the module
        const courseData = await getCourseData();
        const foundModule = courseData.modules?.find(m => m.id === moduleId);
        setModule(foundModule || null);

        // Fetch user submissions
        if (currentUser && foundModule) {
          const userRef = doc(db, 'users', currentUser.uid);
          const userSnap = await getDoc(userRef);
          if (userSnap.exists()) {
            const userData = userSnap.data();
            setSubmissions(userData.submissions || {});
            
            // Pre-fill submission values
            const initialValues: Record<string, string> = {};
            const labCount = foundModule.labCount || 1;
            for (let i = 0; i < labCount; i++) {
              const key = `${foundModule.id}_lab${i}`;
              if (userData.submissions?.[key]) {
                initialValues[key] = userData.submissions[key];
              }
            }
            setSubmissionValues(initialValues);
          }
        }
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };

    if (moduleId) {
      fetchData();
    }
  }, [moduleId, currentUser]);

  const handleSubmissionChange = (key: string, value: string) => {
    setSubmissionValues(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser || !module) return;

    try {
      setIsSubmitting(true);
      const userRef = doc(db, 'users', currentUser.uid);
      
      // Construct update object
      const updates: Record<string, string> = {};
      Object.entries(submissionValues).forEach(([key, value]) => {
        if (value.trim()) {
          updates[`submissions.${key}`] = value;
        }
      });

      if (Object.keys(updates).length > 0) {
        // Get current user data to check if all labs are submitted
        const userSnap = await getDoc(userRef);
        const userData = userSnap.exists() ? userSnap.data() : {};
        const currentSubmissions = userData.submissions || {};
        
        // Merge new submissions
        const updatedSubmissions = { ...currentSubmissions };
        Object.entries(submissionValues).forEach(([key, value]) => {
          if (value.trim()) {
            updatedSubmissions[key] = value;
          }
        });
        
        // Check if all labs for this module are submitted
        const labCount = module.labCount || 1;
        let allLabsSubmitted = true;
        for (let i = 0; i < labCount; i++) {
          const key = `${module.id}_lab${i}`;
          if (!updatedSubmissions[key] || !updatedSubmissions[key].trim()) {
            allLabsSubmitted = false;
            break;
          }
        }
        
        // Update submissions and progress
        const progressUpdates: Record<string, any> = {};
        Object.entries(submissionValues).forEach(([key, value]) => {
          if (value.trim()) {
            progressUpdates[`submissions.${key}`] = value;
          }
        });
        
        // Mark module as complete if all labs are submitted
        if (allLabsSubmitted) {
          progressUpdates[`progress.${module.id}`] = true;
        }
        
        await updateDoc(userRef, progressUpdates);
        
        // Update local state
        setSubmissions(updatedSubmissions);
        
        if (allLabsSubmitted) {
          toast.success(`All labs submitted! Module "${module.title}" marked as complete.`);
        } else {
          toast.success('Labs submitted successfully!');
        }
        
        setIsSubmitModalOpen(false);
      }
    } catch (error) {
      console.error("Error submitting labs:", error);
      toast.error("Failed to submit labs. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getEmbedUrl = (url?: string) => {
    if (!url) return null;
    // Simple YouTube ID extraction
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? `https://www.youtube.com/embed/${match[2]}` : null;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center pt-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow"></div>
      </div>
    );
  }

  if (!module) {
    return (
      <div className="min-h-screen bg-navy flex flex-col items-center justify-center pt-20 text-white">
        <h2 className="text-2xl font-bold mb-4">Module Not Found</h2>
        <button onClick={() => navigate('/dashboard')} className="text-yellow hover:underline">
          Return to Dashboard
        </button>
      </div>
    );
  }

  const embedUrl = getEmbedUrl(module.videoLink);
  const labCount = module.labCount || 1;

  return (
    <div className="pt-24 pb-12 bg-navy min-h-screen">
      <div className="container mx-auto px-4 md:px-6">
        
        {/* Back Button */}
        <button 
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
          Back to Dashboard
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content: Video & Syllabus */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Video Section */}
            <div className="bg-navy-light rounded-2xl overflow-hidden border border-white/10 shadow-xl">
              <div className="aspect-video bg-black relative">
                {embedUrl ? (
                  <iframe 
                    src={embedUrl}
                    title={module.title}
                    className="w-full h-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-gray-500">
                    <Play className="w-16 h-16 mb-4 opacity-50" />
                    <p>No video available for this module</p>
                  </div>
                )}
              </div>
              <div className="p-6">
                <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">{module.title}</h1>
                <p className="text-gray-400">{module.focus}</p>
              </div>
            </div>

          </div>

          {/* Sidebar: Labs & Actions */}
          <div className="space-y-6">
            
            {/* Labs Card */}
            <div className="bg-navy-light rounded-2xl p-6 border border-white/10 sticky top-24">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-yellow" />
                  Labs
                </h2>
              </div>

              <div className="space-y-4 mb-8">
                {Array.from({ length: labCount }).map((_, idx) => {
                  const key = `${module.id}_lab${idx}`;
                  const isSubmitted = !!submissions[key];
                  return (
                    <div key={idx} className="p-4 bg-navy rounded-xl border border-white/5 flex items-center justify-between">
                      <span className="text-gray-300 font-medium">Lab {idx + 1}</span>
                      {isSubmitted ? (
                        <span className="flex items-center gap-1 text-green-400 text-sm font-medium">
                          <CheckCircle className="w-4 h-4" /> Submitted
                        </span>
                      ) : (
                        <span className="text-gray-500 text-sm">Not submitted</span>
                      )}
                    </div>
                  );
                })}
              </div>

              <button
                onClick={() => setIsSubmitModalOpen(true)}
                className="w-full py-4 bg-yellow text-navy font-bold rounded-xl hover:bg-yellow-hover transition-colors shadow-lg shadow-yellow/10"
              >
                Submit Your Work
              </button>
            </div>

          </div>
        </div>

        {/* Submission Modal */}
        <AnimatePresence>
          {isSubmitModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-navy-light w-full max-w-lg rounded-2xl border border-white/10 shadow-2xl overflow-hidden"
              >
                <div className="p-6 border-b border-white/10 flex items-center justify-between">
                  <h3 className="text-xl font-bold text-white">Submit Lab Work</h3>
                  <button 
                    onClick={() => setIsSubmitModalOpen(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
                
                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                  <div className="space-y-4">
                    {Array.from({ length: labCount }).map((_, idx) => {
                      const key = `${module.id}_lab${idx}`;
                      return (
                        <div key={idx}>
                          <label className="block text-sm font-medium text-gray-300 mb-2">
                            Lab {idx + 1} URL (GitHub/Replit)
                          </label>
                          <input 
                            type="url"
                            placeholder="https://..."
                            value={submissionValues[key] || ''}
                            onChange={(e) => handleSubmissionChange(key, e.target.value)}
                            className="w-full bg-navy border border-white/10 rounded-lg px-4 py-3 text-white focus:border-yellow outline-none transition-colors"
                          />
                        </div>
                      );
                    })}
                  </div>

                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsSubmitModalOpen(false)}
                      className="flex-1 px-4 py-3 bg-navy border border-white/10 text-white font-bold rounded-xl hover:bg-white/5 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="flex-1 px-4 py-3 bg-yellow text-navy font-bold rounded-xl hover:bg-yellow-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSubmitting ? 'Submitting...' : 'Confirm Submission'}
                    </button>
                  </div>
                </form>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
};

export default ModuleDetails;
