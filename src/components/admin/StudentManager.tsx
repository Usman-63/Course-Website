import React, { useState, useEffect } from 'react';
import { db } from '../../services/firebase';
import { auth } from '../../services/firebase';
import { doc, updateDoc } from 'firebase/firestore';
import { Users, Search, ExternalLink, Shield, ShieldAlert, Loader, Edit } from 'lucide-react';
import { getAdminData, getUsersWithAdminData, UserWithAdminData } from '../../services/api';
import { classService } from '../../services/classService';
import StudentEditSheet from './StudentEditSheet';

interface User extends UserWithAdminData {
  id: string;
  email?: string;
  name?: string;
  role?: string;
  isActive?: boolean;
  createdAt?: any;
  progress?: Record<string, boolean>; // map of module IDs to completion status
  submissions?: Record<string, string>; // map of module IDs to video URLs
}

const StudentManager: React.FC = () => {
  const [students, setStudents] = useState<User[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [totalModules, setTotalModules] = useState(0);
  const [authReady, setAuthReady] = useState(false);
  const [editingStudent, setEditingStudent] = useState<UserWithAdminData | null>(null);
  const [classes, setClasses] = useState<any[]>([]);
  const [totalLabs, setTotalLabs] = useState(0);
  const [labLabels, setLabLabels] = useState<string[]>([]);

  // Wait for auth to be ready
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      if (user) {
        setAuthReady(true);
      } else {
        setAuthReady(false);
        setLoading(false);
      }
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!authReady) return;

    // Fetch course data to get total number of modules and labs for the active course
    const fetchCourseData = async () => {
      try {
        const courseData = await getAdminData();

        const courses = courseData.courses || [];
        // Prefer the currently published course; fall back to the first one
        const activeCourse = courses.find((c) => c.isVisible) || courses[0];

        if (activeCourse) {
          const modules = activeCourse.modules || [];
          setTotalModules(modules.length);

          // Build a flat list of lab labels: ["Module 1 Lab 1", "Module 1 Lab 2", "Module 2 Lab 1", ...]
          const labels: string[] = [];
          let labCountTotal = 0;

          modules
            .slice() // avoid mutating original
            .sort((a, b) => (a.order || 0) - (b.order || 0))
            .forEach((module, index) => {
              const moduleOrder = module.order ?? index + 1;
              const moduleLabCount = module.labCount && module.labCount > 0 ? module.labCount : 0;

              for (let i = 1; i <= moduleLabCount; i += 1) {
                labels.push(`Module ${moduleOrder} Lab ${i}`);
              }

              labCountTotal += moduleLabCount;
            });

          setTotalLabs(labCountTotal);
          setLabLabels(labels);
        } else {
          setTotalModules(0);
          setTotalLabs(0);
          setLabLabels([]);
        }
      } catch (error) {
        console.error("Error fetching course data:", error);
        setTotalModules(0);
        setTotalLabs(0);
        setLabLabels([]);
      }
    };
    
    fetchCourseData();
    
    // Fetch classes for attendance
    const fetchClasses = async () => {
      try {
        const classData = await classService.getAll();
        setClasses(classData);
      } catch (error) {
        console.error("Error fetching classes:", error);
      }
    };
    fetchClasses();
    
    // Fetch users with admin data
    const fetchUsers = async () => {
      try {
        const response = await getUsersWithAdminData();
        const users = response.students.map((student) => ({
          ...student,
          id: student._id,
          email: student['Email Address'],
          name: student.Name || student.name || '',
          isActive: student.isActive,  // Map isActive from API response
          role: student.role,  // Map role from API response
        })) as User[];
        setStudents(users);
      } catch (error) {
        console.error("Error fetching users:", error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchUsers();
  }, [authReady]);

  const handleSaveStudent = async (uid: string, updates: any) => {
    try {
      // Update via API
      const { updateUserAdminData } = await import('../../services/api');
      await updateUserAdminData(uid, updates);
      
      // Refresh students list
      const response = await getUsersWithAdminData();
      const updatedUsers = response.students.map((s) => ({
        ...s,
        id: s._id,
        email: s['Email Address'],
        name: s.Name || s.name || '',
        isActive: s.isActive,  // Map isActive from API response
        role: s.role,  // Map role from API response
      })) as User[];
      setStudents(updatedUsers);
    } catch (error) {
      console.error("Error saving student:", error);
      throw error;
    }
  };

  const getAttendanceCount = (user: User) => {
    const attendance = user.attendance || {};
    return Object.values(attendance).filter(Boolean).length;
  };

  const toggleActivation = async (userId: string, currentStatus?: boolean) => {
    try {
      const userRef = doc(db, 'users', userId);
      await updateDoc(userRef, {
        isActive: !currentStatus
      });
      // Refresh students list
      const response = await getUsersWithAdminData();
      const updatedUsers = response.students.map((s) => ({
        ...s,
        id: s._id,
        email: s['Email Address'],
        name: s.Name || s.name || '',
        isActive: s.isActive,
        role: s.role,
      })) as User[];
      setStudents(updatedUsers);
    } catch (error) {
      console.error("Error toggling activation:", error);
      alert("Failed to update user status");
    }
  };

  const filteredStudents = students.filter(student => 
    student.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    student.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Total modules is fetched from course data 

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h3 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="text-yellow-600 w-8 h-8" /> 
            Student CRM
          </h3>
          <p className="text-gray-500 mt-1">Monitor progress and manage user accounts</p>
        </div>
        <div className="relative w-full md:w-96">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="bg-white border border-gray-200 rounded-xl py-3 pl-12 pr-4 text-gray-900 focus:border-primary focus:ring-1 focus:ring-primary outline-none w-full transition-all placeholder:text-gray-400 shadow-sm"
            placeholder="Search students..."
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 text-gray-600 text-xs font-bold uppercase tracking-wider border-b border-gray-200">
              <th className="px-6 py-5">Student</th>
              <th className="px-6 py-5">Status & Role</th>
              <th className="px-6 py-5">Attendance</th>
              <th className="px-6 py-5">Payment</th>
              <th className="px-6 py-5">Progress</th>
              <th className="px-6 py-5">Submissions</th>
              <th className="px-6 py-5">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && (
              <tr>
                <td colSpan={7} className="py-20 text-center">
                  <div className="flex flex-col items-center justify-center gap-3 text-gray-500">
                    <Loader className="w-8 h-8 animate-spin text-primary" />
                    <p>Loading students...</p>
                  </div>
                </td>
              </tr>
            )}
            {!loading && filteredStudents.map((student) => {
              const completedCount = student.progress ? Object.values(student.progress).filter(Boolean).length : 0;
              const progressPercent = totalModules > 0 ? Math.round((completedCount / totalModules) * 100) : 0;
              
              const submissions = student.submissions ? Object.entries(student.submissions) : [];
              const attendanceCount = getAttendanceCount(student);
              const paymentStatus = student['Payment Status'] || student.paymentStatus || '';

              return (
                <tr key={student.id} className="hover:bg-gray-50 transition-colors group">
                  <td className="px-6 py-5 align-middle">
                    <div className="flex flex-col gap-1">
                      <div className="font-bold text-gray-900 text-base">{student.name}</div>
                      <div className="text-sm text-gray-500 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
                        {student.email}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5 align-middle">
                    <div className="flex flex-col gap-3 items-start">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                        student.role === 'admin' 
                          ? 'bg-purple-100 text-purple-700 border-purple-200' 
                          : 'bg-blue-100 text-blue-700 border-blue-200'
                      }`}>
                        {student.role || 'student'}
                      </span>
                      
                      {student.role !== 'admin' && (
                        <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                          <button 
                            onClick={() => toggleActivation(student.id, student.isActive)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                              student.isActive 
                                ? 'bg-green-100 text-green-700 border-green-200 hover:bg-red-100 hover:text-red-700 hover:border-red-200' 
                                : 'bg-red-100 text-red-700 border-red-200 hover:bg-green-100 hover:text-green-700 hover:border-green-200'
                            }`}
                          >
                            {student.isActive ? (
                               <><Shield className="w-3 h-3" /> Active</>
                            ) : (
                               <><ShieldAlert className="w-3 h-3" /> Inactive</>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-5 align-middle">
                    <div className="text-sm text-gray-700">
                      <span className="font-semibold">{attendanceCount}</span>
                      <span className="text-gray-500"> classes</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 align-middle">
                    {paymentStatus && (
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        paymentStatus.toLowerCase() === 'paid'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {paymentStatus}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-5 align-middle">
                    <div className="w-full max-w-[160px]">
                      <div className="flex justify-between text-xs text-gray-500 mb-2 font-medium">
                        <span className={progressPercent === 100 ? 'text-green-600' : 'text-gray-900'}>{progressPercent}% Complete</span>
                        <span>{completedCount}/{totalModules}</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden border border-gray-200">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${
                            progressPercent === 100 ? 'bg-green-500' : 'bg-primary'
                          }`}
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5 align-middle">
                    {submissions.length > 0 ? (
                      <div className="flex gap-2 flex-wrap max-w-[200px]">
                        {submissions.map(([key, url]) => {
                           const isLab = key.includes('_lab');
                           const title = isLab 
                             ? `Lab ${parseInt(key.split('_lab')[1]) + 1}`
                             : 'Submission';
                           
                           return (
                            <a 
                              key={key}
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="w-9 h-9 bg-white border border-gray-200 rounded-lg flex items-center justify-center text-yellow-600 hover:bg-yellow hover:text-white hover:scale-105 transition-all relative group shadow-sm"
                              title={`View ${title}`}
                            >
                              <ExternalLink className="w-4 h-4" />
                              {isLab && (
                                <span className="absolute -top-2 -right-2 bg-navy text-white text-[9px] font-bold border border-white/20 rounded px-1.5 py-0.5 shadow-sm z-10">
                                  {parseInt(key.split('_lab')[1]) + 1}
                                </span>
                              )}
                            </a>
                          );
                        })}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs italic">No submissions</span>
                    )}
                  </td>
                  <td className="px-6 py-5 align-middle">
                    <button
                      onClick={() => setEditingStudent(student as UserWithAdminData)}
                      className="px-3 py-1.5 bg-yellow text-navy rounded-lg text-xs font-semibold hover:bg-yellow-hover transition-all flex items-center gap-1.5"
                    >
                      <Edit className="w-3 h-3" />
                      Edit
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!loading && filteredStudents.length === 0 && (
          <div className="text-center py-20 text-gray-500 flex flex-col items-center">
            <Search className="w-12 h-12 mb-4 opacity-20" />
            <p className="text-lg font-medium text-gray-900">No students found</p>
            <p className="text-sm opacity-60">Try adjusting your search terms</p>
          </div>
        )}
      </div>
      
      {editingStudent && (
        <StudentEditSheet
          isOpen={!!editingStudent}
          onClose={() => setEditingStudent(null)}
          student={editingStudent as any}
          onSave={handleSaveStudent}
          totalLabs={totalLabs}
          labLabels={labLabels}
          classMap={new Map(classes.map(c => [c.id, c.topic]))}
        />
      )}
    </div>
  );
};

export default StudentManager;
