import React, { useEffect, useState } from 'react';
import { Users, DollarSign, AlertCircle, Loader2, Calendar, BookOpen, CheckCircle, FileText } from 'lucide-react';
import { getRegisterStudents, getSurveyStudents, getCourseData, CourseModule } from '../../services/api';
import { db } from '../../services/firebase';
import { collection, query, orderBy, limit, getDocs } from 'firebase/firestore';
import { useNavigate } from 'react-router-dom';

interface Announcement {
  id: string;
  title: string;
  content: string;
  createdAt: any;
}

interface DashboardMetrics {
  total_students: number;
  paid_count: number;
  unpaid_count: number;
  has_resume_count: number;
  onboarding_percentage: number;
  survey_filled_count: number;
  survey_not_filled_count: number;
  last_synced?: string;
}

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [modules, setModules] = useState<CourseModule[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [registerRes, surveyRes, courseRes] = await Promise.all([
          getRegisterStudents('name', 'asc', false),
          getSurveyStudents('name', 'asc', false),
          getCourseData()
        ]);
        
        // Calculate metrics from separate Register and Survey data (no merging)
        const registerStudents = registerRes.students || [];
        const surveyStudents = surveyRes.students || [];
        
        // Use counts directly from each form (no email matching/merging)
        const registerCount = registerStudents.length;
        const surveyCount = surveyStudents.length;
        
        let paidCount = 0;
        let hasResumeCount = 0;
        
        // Count paid students from Register - check "Payment proved" column
        registerStudents.forEach(s => {
          const paymentProved = (s['Payment proved'] || '').toString().toLowerCase().trim();
          if (paymentProved === 'yes') {
            paidCount++;
          }
        });
        
        // Count resumes from Survey form only
        surveyStudents.forEach(s => {
          const resumeValue = s['Upload your Resume / CV (PDF preferred)  '] || 
                             s['Upload your Resume / CV (PDF preferred)'] || '';
          const resumeStr = resumeValue ? String(resumeValue).trim() : '';
          if (resumeStr !== '' && 
              resumeStr.toLowerCase() !== 'n/a' &&
              resumeStr.toLowerCase() !== 'nan' &&
              resumeStr !== 'undefined' &&
              resumeStr !== 'null') {
            hasResumeCount++;
          }
        });
        
        const calculatedMetrics: DashboardMetrics = {
          total_students: registerCount, // Total from Register form only
          paid_count: paidCount,
          unpaid_count: registerCount - paidCount,
          has_resume_count: hasResumeCount,
          onboarding_percentage: registerCount > 0 ? Math.round((hasResumeCount / registerCount) * 100) : 0,
          survey_filled_count: surveyCount, // Count from Survey form only
          survey_not_filled_count: Math.max(0, registerCount - surveyCount), // Simple subtraction
        };
        
        setMetrics(calculatedMetrics);
        setModules(courseRes.modules || []);

        // Fetch recent announcements from Firestore
        const q = query(collection(db, 'announcements'), orderBy('createdAt', 'desc'), limit(3));
        const snapshot = await getDocs(q);
        const fetchedAnnouncements = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        })) as Announcement[];
        setAnnouncements(fetchedAnnouncements);

      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-gray-50 px-4">
        <div className="bg-white rounded-3xl shadow-lg border border-gray-100 px-8 py-6 max-w-xl w-full flex items-center gap-4">
          <div className="flex-shrink-0">
            <Loader2 className="w-8 h-8 text-yellow animate-spin" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-gray-900">
              Loading dashboard data…
            </p>
            <p className="text-xs text-gray-500">
              Fetching course data, operations metrics, and recent announcements. This can take 10–30 seconds on the first load or after a full sync.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return <div>Failed to load metrics.</div>;
  }

  return (
    <div className="space-y-6">
      
      {/* Top Section: Welcome & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Welcome Card */}
        <div className="lg:col-span-2 bg-white rounded-3xl p-8 relative overflow-hidden shadow-sm flex flex-col justify-between min-h-[200px]">
          <div className="relative z-10 max-w-lg">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome to your Dashboard!</h2>
            <p className="text-gray-500 mb-4">Overview of your course operations, student progress, and content updates.</p>
          </div>
          <div className="relative z-10 flex items-center justify-between mt-4">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>Data loaded from Register and Survey forms</span>
            </div>
          </div>
          {/* Abstract background decoration */}
          <div className="absolute right-0 top-0 h-full w-1/3 bg-gray-50 rounded-l-full opacity-50 transform translate-x-1/4"></div>
          <div className="absolute right-10 bottom-10 w-24 h-24 bg-yellow/10 rounded-full blur-xl"></div>
        </div>

        {/* Quick Stats Column */}
        <div className="space-y-4">
          <button
            type="button"
            onClick={() => navigate('/admin/operations')}
            className="w-full text-left bg-yellow/10 rounded-3xl p-6 flex flex-col justify-between h-[200px] transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-yellow-400"
          >
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-gray-600 font-medium mb-1">Total Students</h3>
                <div className="text-4xl font-bold text-gray-900">{metrics.total_students.toLocaleString()}</div>
                <div className="text-xs text-gray-500 mt-2 space-y-0.5">
                  <p>
                    <span className="font-semibold text-gray-900">{metrics.survey_filled_count}</span> completed survey
                  </p>
                  <p>
                    <span className="font-semibold text-gray-900">{metrics.survey_not_filled_count}</span> not yet completed
                  </p>
                </div>
              </div>
              <div className="p-2 bg-white/50 rounded-full">
                <Users className="w-5 h-5 text-gray-400" />
              </div>
            </div>
            <div className="space-y-2">
               <div className="flex justify-between text-sm">
                 <span className="text-gray-600">Paid</span>
                 <span className="font-bold text-gray-900">{metrics.paid_count}</span>
               </div>
               <div className="w-full bg-white/30 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-yellow h-full rounded-full" style={{ width: `${(metrics.paid_count / metrics.total_students) * 100}%` }}></div>
               </div>
            </div>
          </button>
        </div>
      </div>

      {/* Middle Section: Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <button
          type="button"
          onClick={() => navigate('/admin/content')}
          className="bg-purple-50 rounded-3xl p-6 text-left transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-purple-400"
        >
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-600 font-medium">Course Modules</h3>
            <div className="p-2 bg-white/50 rounded-full">
               <BookOpen className="w-5 h-5 text-purple-600" />
            </div>
          </div>
          <div className="text-4xl font-bold text-gray-900 mb-2">{modules.length}</div>
          <div className="text-sm text-purple-600 font-medium">Active Content</div>
        </button>

        <button
          type="button"
          onClick={() => navigate('/admin/operations')}
          className="bg-green-50 rounded-3xl p-6 text-left transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-green-400"
        >
          <div className="flex justify-between items-start mb-4">
             <h3 className="text-gray-600 font-medium">Resumes</h3>
             <div className="p-2 bg-white/50 rounded-full">
               <FileText className="w-5 h-5 text-green-600" />
            </div>
          </div>
          <div className="text-4xl font-bold text-gray-900 mb-2">{metrics.has_resume_count}</div>
          <div className="text-sm text-green-600 font-medium">
             {metrics.onboarding_percentage}% Submission Rate
          </div>
        </button>
        
        {/* Notice Board / Announcements */}
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
           <div className="flex justify-between items-center mb-4">
             <h3 className="font-bold text-lg text-gray-900">Recent Announcements</h3>
           </div>
           <div className="space-y-4">
             {announcements.length > 0 ? (
               announcements.map((announcement) => (
                 <div key={announcement.id} className="flex gap-4 items-start p-3 rounded-xl hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-100">
                   <div className="w-10 h-10 rounded-full bg-yellow/20 flex items-center justify-center shrink-0">
                     <Calendar className="w-5 h-5 text-yellow-600" />
                   </div>
                   <div>
                     <h4 className="font-bold text-gray-900 text-sm">{announcement.title}</h4>
                     <p className="text-xs text-gray-500 mt-1 line-clamp-2">{announcement.content}</p>
                     <p className="text-[10px] text-gray-400 mt-1">{announcement.createdAt?.toDate().toLocaleDateString()}</p>
                   </div>
                 </div>
               ))
             ) : (
               <div className="text-center py-8 text-gray-400 text-sm">No recent announcements</div>
             )}
           </div>
        </div>
      </div>

      {/* Bottom Section: Course Content Preview & Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Course Modules List */}
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-lg text-gray-900">Course Curriculum</h3>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-lg">{modules.length} Modules</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
             {modules.slice(0, 4).map((module) => (
               <div key={module.id} className="border border-gray-100 rounded-2xl p-4 hover:shadow-md transition-shadow">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-purple-100 text-purple-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
                      Module {module.order}
                    </span>
                    <span className="text-xs text-gray-400">{module.hours} hrs</span>
                  </div>
                  <h4 className="font-bold text-gray-900 mb-1 line-clamp-1">{module.title}</h4>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {module.topics.slice(0, 2).map((topic, i) => (
                      <span key={i} className="text-[10px] text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">
                        {topic}
                      </span>
                    ))}
                    {module.topics.length > 2 && (
                      <span className="text-[10px] text-gray-400 px-1.5 py-0.5">+{module.topics.length - 2} more</span>
                    )}
                  </div>
               </div>
             ))}
          </div>
        </div>

        {/* Action Items / Status */}
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-lg text-gray-900">Action Items</h3>
            <AlertCircle className="w-5 h-5 text-red-400" />
          </div>
          <div className="space-y-4">
             <button
               type="button"
               onClick={() => navigate('/admin/operations')}
               className="w-full flex gap-3 items-center p-3 rounded-xl bg-red-50 border border-red-100 text-left transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-red-400"
             >
                <div className="p-2 bg-white rounded-full shrink-0">
                  <DollarSign className="w-4 h-4 text-red-500" />
                </div>
                <div>
                   <h4 className="font-bold text-sm text-gray-900">{metrics.unpaid_count} Pending Payments</h4>
                   <p className="text-xs text-red-600">Review unpaid students</p>
                </div>
             </button>
             
             <button
               type="button"
               onClick={() => navigate('/admin/operations')}
               className="w-full flex gap-3 items-center p-3 rounded-xl bg-yellow/10 border border-yellow/20 text-left transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-yellow-400"
             >
                <div className="p-2 bg-white rounded-full shrink-0">
                  <FileText className="w-4 h-4 text-yellow-600" />
                </div>
                <div>
                   <h4 className="font-bold text-sm text-gray-900">{metrics.total_students - metrics.has_resume_count} Missing Resumes</h4>
                   <p className="text-xs text-yellow-700">Send reminders</p>
                </div>
             </button>

             <div className="flex gap-3 items-center p-3 rounded-xl bg-green-50 border border-green-100">
                <div className="p-2 bg-white rounded-full shrink-0">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <div>
                   <h4 className="font-bold text-sm text-gray-900">System Status</h4>
                   <p className="text-xs text-green-700">All systems operational</p>
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;