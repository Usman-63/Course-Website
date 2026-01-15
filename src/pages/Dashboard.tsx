import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Bell, 
  BarChart, 
  CheckCircle, 
  Play, 
  FileText, 
  ChevronRight, 
  Clock,
  Trophy,
  BookOpen
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../components/Toast';
import { db } from '../services/firebase';
import { 
  collection, 
  query, 
  orderBy, 
  limit, 
  getDocs, 
  doc, 
  runTransaction,
  onSnapshot
} from 'firebase/firestore';
import { getCourseData, CourseModule } from '../services/api';
import { useNavigate } from 'react-router-dom';

// Types
interface Announcement {
  id: string;
  title: string;
  content: string;
  createdAt: any;
}

interface PollOption {
  id: string;
  text: string;
  votes: number;
}

interface VoteRecord {
  uid: string;
  name: string;
  optionId: string;
  timestamp: string;
}

interface Poll {
  id: string;
  question: string;
  options: PollOption[];
  votes?: VoteRecord[];
  isActive: boolean;
  totalVotes: number;
  createdAt: any;
}

const Dashboard: React.FC = () => {
  const { currentUser, userProfile } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  
  // Data State
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [votedPolls, setVotedPolls] = useState<Set<string>>(new Set());
  const [modules, setModules] = useState<CourseModule[]>([]);
  
  // Progress State
  const [progress, setProgress] = useState<Record<string, boolean>>({});
  const [, setSubmissions] = useState<Record<string, string>>({});

  // User is activated if: isActive is explicitly true, OR they're an admin, OR they're the admin-user
  const isActivated = Boolean(
    userProfile?.isActive === true || 
    userProfile?.role === 'admin' || 
    currentUser?.uid === 'admin-user'
  );

  useEffect(() => {
    if (!currentUser) {
      navigate('/login');
      return;
    }
    if (!isActivated) {
      navigate('/syllabus');
    }
  }, [currentUser, isActivated, navigate]);

  useEffect(() => {
    let unsubscribeUser: (() => void) | null = null;

    const fetchAllData = async () => {
      try {
        setLoading(true);
        
        // 1. Fetch Course Data
        const courseData = await getCourseData();
        setModules((courseData.modules || []).filter(m => m.isVisible !== false));

        // 2. Set up real-time listener for User Progress
        if (currentUser) {
          const userRef = doc(db, 'users', currentUser.uid);
          
          // Real-time listener for user data (progress, submissions, votedPolls)
          unsubscribeUser = onSnapshot(userRef, (userSnap) => {
            if (userSnap.exists()) {
              const userData = userSnap.data();
              setProgress(userData.progress || {});
              setSubmissions(userData.submissions || {});
              if (userData.votedPolls) {
                setVotedPolls(new Set(userData.votedPolls));
              }
            } else {
              // User document doesn't exist yet, initialize empty
              setProgress({});
              setSubmissions({});
              setVotedPolls(new Set());
            }
            setLoading(false);
          }, (error) => {
            console.error("Error listening to user data:", error);
            setLoading(false);
          });

          // 3. Fetch Announcements
          const annQuery = query(
            collection(db, 'announcements'),
            orderBy('createdAt', 'desc'),
            limit(3)
          );
          const annSnapshot = await getDocs(annQuery);
          setAnnouncements(annSnapshot.docs.map(d => ({ id: d.id, ...d.data() } as Announcement)));

          // 4. Fetch Polls
          const pollQuery = query(
            collection(db, 'polls'),
            orderBy('createdAt', 'desc'),
            limit(1)
          );
          const pollSnapshot = await getDocs(pollQuery);
          setPolls(pollSnapshot.docs.map(d => ({ id: d.id, ...d.data() } as Poll)));
        } else {
          setLoading(false);
        }

      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        setLoading(false);
      }
    };

    fetchAllData();

    // Cleanup listener on unmount
    return () => {
      if (unsubscribeUser) {
        unsubscribeUser();
      }
    };
  }, [currentUser]);

  const handleVote = async (pollId: string, optionId: string) => {
    if (!currentUser) {
      console.error('User not authenticated');
      return;
    }
    
    // Ensure user is authenticated with Firebase
    if (!currentUser.uid) {
      console.error('User UID not available');
      return;
    }

    // Optimistic Update
    const poll = polls.find(p => p.id === pollId);
    if (!poll) return;

    // Check local state for previous vote
    const previousVote = poll.votes?.find(v => v.uid === currentUser.uid);
    
    // Prevent clicking the same option again
    if (previousVote?.optionId === optionId) return;

    // Update local state immediately
    const updatedPolls = polls.map(p => {
      if (p.id === pollId) {
        let newOptions = [...p.options];
        let newTotalVotes = p.totalVotes || 0;
        let newVotes = [...(p.votes || [])];

        // Remove previous vote if exists
        if (previousVote) {
          newOptions = newOptions.map(opt => 
            opt.id === previousVote.optionId ? { ...opt, votes: Math.max(0, (opt.votes || 0) - 1) } : opt
          );
          newTotalVotes--;
          newVotes = newVotes.filter(v => v.uid !== currentUser.uid);
        }

        // Add new vote
        newOptions = newOptions.map(opt => 
          opt.id === optionId ? { ...opt, votes: (opt.votes || 0) + 1 } : opt
        );
        newTotalVotes++;
        newVotes.push({
          uid: currentUser.uid,
          name: userProfile?.name || 'Student',
          optionId: optionId,
          timestamp: new Date().toISOString()
        });

        return {
          ...p,
          options: newOptions,
          totalVotes: newTotalVotes,
          votes: newVotes
        };
      }
      return p;
    });

    setPolls(updatedPolls);
    setVotedPolls(prev => new Set(prev).add(pollId));

    try {
      await runTransaction(db, async (transaction) => {
        // STEP 1: ALL READS FIRST (Firestore requirement)
        const pollRef = doc(db, 'polls', pollId);
        const userRef = doc(db, 'users', currentUser.uid!);
        
        const pollSnap = await transaction.get(pollRef);
        const userSnap = await transaction.get(userRef);
        
        if (!pollSnap.exists()) {
          throw new Error("Poll does not exist!");
        }

        // STEP 2: Process the data
        const pollData = pollSnap.data() as Poll;
        let newOptions = [...pollData.options];
        let currentVotes = pollData.votes || [];
        let newTotalVotes = pollData.totalVotes || 0;

        // Check if user has voted in the DB version
        const existingVoteIndex = currentVotes.findIndex(v => v.uid === currentUser.uid);
        const existingVote = existingVoteIndex !== -1 ? currentVotes[existingVoteIndex] : null;

        // If clicking the same option they already voted for, do nothing
        if (existingVote && existingVote.optionId === optionId) {
             return;
        }

        // Remove previous vote effects
        if (existingVote) {
            const prevOptionIndex = newOptions.findIndex(o => o.id === existingVote.optionId);
            if (prevOptionIndex !== -1) {
                newOptions[prevOptionIndex] = {
                    ...newOptions[prevOptionIndex],
                    votes: Math.max(0, (newOptions[prevOptionIndex].votes || 0) - 1)
                };
            }
            newTotalVotes = Math.max(0, newTotalVotes - 1);
            currentVotes.splice(existingVoteIndex, 1);
        }

        // Add new vote
        const optionIndex = newOptions.findIndex(o => o.id === optionId);
        if (optionIndex !== -1) {
            newOptions[optionIndex] = {
                ...newOptions[optionIndex],
                votes: (newOptions[optionIndex].votes || 0) + 1
            };
            newTotalVotes++;
            
            currentVotes.push({
                uid: currentUser.uid,
                name: userProfile?.name || 'Student',
                optionId: optionId,
                timestamp: new Date().toISOString()
            });

            // STEP 3: ALL WRITES AFTER ALL READS
            transaction.update(pollRef, {
                options: newOptions,
                totalVotes: newTotalVotes,
                votes: currentVotes
            });
            
            // Update user profile to track voted polls
            if (userSnap.exists()) {
                const userData = userSnap.data();
                const currentVotedPolls = userData.votedPolls || [];
                const updatedVotedPolls = currentVotedPolls.includes(pollId) 
                    ? currentVotedPolls 
                    : [...currentVotedPolls, pollId];
                transaction.update(userRef, {
                    votedPolls: updatedVotedPolls
                });
            } else {
                // If user document doesn't exist, create it
                transaction.set(userRef, {
                    votedPolls: [pollId]
                });
            }
        }
      });
    } catch (error: any) {
      console.error("Error submitting vote:", error);
      // Revert optimistic update on error
      setPolls(polls); // Restore original polls
      setVotedPolls(prev => {
        const newSet = new Set(prev);
        newSet.delete(pollId);
        return newSet;
      });
      
      // Show user-friendly error message
      if (error.code === 'permission-denied') {
        toast.error('You do not have permission to vote. Please make sure you are logged in and your account is activated.');
      } else {
        toast.error(`Failed to record vote: ${error.message || 'Unknown error'}`);
      }
    }
  };

  // Calculations
  const sortedModules = [...modules].sort((a, b) => (a.order || 0) - (b.order || 0));
  const completedCount = Object.values(progress).filter(Boolean).length;
  const totalModules = modules.length;
  const progressPercentage = totalModules > 0 ? Math.round((completedCount / totalModules) * 100) : 0;
  
  // Find "Up Next" Module (first incomplete)
  const nextModule = sortedModules.find(m => !progress[m.id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center pt-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow"></div>
      </div>
    );
  }

  return (
    <div className="pt-24 pb-12 bg-navy min-h-screen">
      <div className="container mx-auto px-4 md:px-6">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
              Welcome back, <span className="text-yellow">{userProfile?.name?.split(' ')[0] || 'Student'}</span>
            </h1>
            <p className="text-gray-400">You're making great progress. Keep it up!</p>
          </div>
          
          <div className="bg-navy-light p-4 rounded-xl border border-white/10 w-full md:w-80">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-400 font-medium">Course Progress</span>
              <span className="text-yellow font-bold">{progressPercentage}%</span>
            </div>
            <div className="h-2 bg-navy rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${progressPercentage}%` }}
                className="h-full bg-yellow"
              />
            </div>
            <p className="text-xs text-gray-500 mt-2 text-right">{completedCount}/{totalModules} Modules Completed</p>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
          
          {/* Main Column (Announcements + Up Next) */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Announcements Section - Full Width */}
            {announcements.length > 0 && (
              <div className="mb-10">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gradient-to-r from-yellow/25 to-navy-light rounded-2xl p-6 border-2 border-yellow/50 shadow-xl shadow-yellow/20 relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 w-64 h-64 bg-yellow/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
                  
                  <div className="relative z-10 mb-6">
                    <div className="flex items-center gap-3">
                      <motion.div
                        animate={{ scale: [1, 1.05, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="p-2 bg-yellow rounded-lg text-navy shadow-lg shadow-yellow/20"
                      >
                        <Bell className="w-5 h-5" />
                      </motion.div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold text-white">Important Announcements</h2>
                          <span className="px-2 py-0.5 bg-yellow/20 text-yellow text-[10px] font-bold uppercase rounded-full border border-yellow/40">
                            Important
                          </span>
                        </div>
                        <p className="text-gray-400 text-sm mt-0.5">Stay updated with latest news</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 relative z-10">
                    {announcements.map((item, index) => (
                      <motion.div
                        key={item.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.1 }}
                        className="group bg-navy/70 backdrop-blur-sm p-5 rounded-xl border border-yellow/30 hover:border-yellow/60 shadow-lg hover:shadow-yellow/10 transition-all hover:transform hover:-translate-y-1 relative overflow-hidden"
                      >
                        <div className="absolute inset-0 bg-yellow/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                        
                        <div className="relative z-10">
                          <h3 className="text-white font-bold text-lg mb-2">{item.title}</h3>
                          <p className="text-gray-300 text-sm line-clamp-3 mb-3 leading-relaxed">{item.content}</p>
                          <div className="flex items-center justify-between pt-3 border-t border-white/10">
                            <span className="text-xs text-yellow/80 font-medium flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {item.createdAt?.toDate ? item.createdAt.toDate().toLocaleDateString() : 'Just now'}
                            </span>
                            <span className="px-2 py-0.5 bg-yellow/20 text-yellow text-[10px] font-semibold uppercase rounded border border-yellow/30">
                              New
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              </div>
            )}

            {/* Up Next / Current Focus */}
            {nextModule ? (
              <div className="bg-gradient-to-br from-navy-light to-navy p-1 rounded-2xl border border-white/10 relative overflow-hidden group">
                 <div className="absolute top-0 right-0 w-64 h-64 bg-yellow/5 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none"></div>
                 
                 <div className="bg-navy/50 backdrop-blur-sm p-6 rounded-xl h-full">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="px-3 py-1 bg-yellow text-navy text-xs font-bold rounded-full uppercase tracking-wider">
                        Up Next
                      </div>
                      <span className="text-gray-400 text-sm">Week {nextModule.order || 1}</span>
                    </div>
                    
                    <h2 className="text-2xl font-bold text-white mb-3">{nextModule.title}</h2>
                    <p className="text-gray-300 mb-6 max-w-2xl">{nextModule.focus}</p>
                    
                    <div className="flex flex-wrap gap-3">
                      {nextModule.videoLink && (
                        <a 
                          href={nextModule.videoLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-5 py-3 bg-yellow text-navy font-bold rounded-xl hover:bg-yellow-hover transition-colors shadow-lg shadow-yellow/10"
                        >
                          <Play className="w-4 h-4 fill-current" />
                          Watch Lecture
                        </a>
                      )}
                      {nextModule.labLink && (
                        <a 
                          href={nextModule.labLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-5 py-3 bg-white/5 text-white font-medium rounded-xl hover:bg-white/10 transition-colors border border-white/10"
                        >
                          <FileText className="w-4 h-4" />
                          Open Lab
                        </a>
                      )}
                    </div>
                 </div>
              </div>
            ) : (
              <div className="bg-green-500/10 border border-green-500/20 p-8 rounded-2xl text-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4 text-green-400">
                  <Trophy className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">All Caught Up!</h2>
                <p className="text-gray-400">You've completed all available modules. Amazing work!</p>
              </div>
            )}
            
          </div>

          {/* Side Column (Polls + Stats) */}
          <div className="space-y-6">
            
            {/* Polls Card */}
            {polls.length > 0 && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-yellow/25 to-navy-light rounded-2xl p-6 border-2 border-yellow/50 shadow-xl shadow-yellow/20 relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-yellow/10 rounded-full blur-2xl -mr-8 -mt-8 pointer-events-none"></div>
                
                <div className="relative z-10 mb-6">
                  <div className="flex items-center gap-3">
                    <motion.div
                      animate={{ scale: [1, 1.05, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="p-2 bg-yellow rounded-lg text-navy shadow-lg shadow-yellow/20"
                    >
                      <BarChart className="w-5 h-5" />
                    </motion.div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-white">Community Poll</h2>
                        <span className="px-2 py-0.5 bg-yellow/20 text-yellow text-[10px] font-bold uppercase rounded-full border border-yellow/40">
                          Vote
                        </span>
                      </div>
                      <p className="text-gray-400 text-xs mt-0.5">Share your opinion</p>
                    </div>
                  </div>
                </div>

                {polls.map((poll, pollIndex) => {
                  const isVoted = votedPolls.has(poll.id);

                  return (
                    <motion.div 
                      key={poll.id} 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: pollIndex * 0.1 }}
                      className="relative z-10 bg-navy/50 rounded-xl p-4 border border-yellow/20"
                    >
                      <h3 className="text-white font-semibold text-base mb-4">{poll.question}</h3>
                      <div className="space-y-2">
                        {poll.options.map((option, optIndex) => {
                          const isSelected = isVoted && poll.votes?.find(v => v.uid === currentUser?.uid)?.optionId === option.id;
                          return (
                            <motion.button
                              key={option.id}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: optIndex * 0.05 }}
                              onClick={() => handleVote(poll.id, option.id)}
                              className={`w-full rounded-lg border transition-all text-left group ${
                                isVoted 
                                  ? (isSelected
                                      ? 'border-yellow bg-yellow/15 shadow-md shadow-yellow/20' 
                                      : 'border-white/5 bg-white/5 opacity-60 hover:opacity-100 hover:bg-white/10 cursor-pointer')
                                  : 'border-white/10 hover:border-yellow/50 hover:bg-white/5'
                              }`}
                            >
                              <div className="p-3">
                                <span className={`text-sm ${isSelected ? 'text-white font-medium' : 'text-gray-300'}`}>
                                  {option.text}
                                </span>
                              </div>
                            </motion.button>
                          );
                        })}
                      </div>
                      {isVoted && (
                        <div className="flex items-center justify-end mt-4 pt-3 border-t border-white/10">
                          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-semibold uppercase rounded border border-green-500/30">
                            Voted
                          </span>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </motion.div>
            )}

            {/* Quick Stats / Info */}
            <div className="bg-navy-light rounded-2xl p-6 border border-white/10">
              <h3 className="text-white font-bold mb-4">Your Stats</h3>
              <div className="flex items-center justify-between p-3 bg-navy rounded-xl border border-white/5">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-gray-400" />
                  <span className="text-gray-300 text-sm">Completed</span>
                </div>
                <span className="text-white text-sm font-mono">{completedCount} Modules</span>
              </div>
            </div>

          </div>
        </div>

        {/* Full Curriculum List */}
        <div className="bg-navy-light rounded-2xl border border-white/10 overflow-hidden">
          <div className="p-6 border-b border-white/10">
            <h2 className="text-xl font-bold text-white flex items-center gap-3">
              <BookOpen className="w-5 h-5 text-yellow" />
              Course Curriculum
            </h2>
          </div>
          
          <div className="divide-y divide-white/5">
            {sortedModules.map((module) => {
              const isCompleted = progress[module.id];
              const isNext = nextModule?.id === module.id;
              
              return (
                <div 
                  key={module.id} 
                  className="hover:bg-white/[0.02] transition-colors duration-200"
                >
                  {/* Module Header - Clickable */}
                  <div 
                    onClick={() => navigate(`/module/${module.id}`)}
                    className="p-4 md:p-6 cursor-pointer flex items-center gap-4 group"
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                      isCompleted 
                        ? 'bg-green-500/20 text-green-400' 
                        : isNext 
                          ? 'bg-yellow text-navy'
                          : 'bg-navy border border-white/10 text-gray-500 group-hover:border-white/30'
                    }`}>
                      {isCompleted ? <CheckCircle className="w-5 h-5" /> : <span className="font-bold text-sm">{module.order}</span>}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className={`font-semibold truncate transition-colors ${
                          isCompleted || isNext ? 'text-white' : 'text-gray-400 group-hover:text-white'
                        }`}>
                          {module.title}
                        </h3>
                        {isNext && (
                          <span className="px-2 py-0.5 bg-yellow/10 text-yellow text-[10px] font-bold uppercase rounded-full border border-yellow/20">
                            Current
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 truncate group-hover:text-gray-400">{module.focus}</p>
                    </div>

                    <div className="text-gray-500 group-hover:text-yellow transition-colors">
                      <ChevronRight className="w-5 h-5" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Dashboard;
