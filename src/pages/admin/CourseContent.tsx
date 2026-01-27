import React, { useState, useEffect } from 'react';
import { Loader2, Plus, RefreshCw, BookOpen, Eye, EyeOff, Edit2, Check, X, Trash2 } from 'lucide-react';
import ModuleEditor from '../../components/ModuleEditor';
import PricingTiersEditor from '../../components/PricingTiersEditor';
import { getAdminData, updateCourse, addCourse, deleteCourse, CourseData, Course } from '../../services/api';
import { useToast } from '../../components/Toast';

const CourseContent: React.FC = () => {
  const [courseData, setCourseData] = useState<CourseData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'modules' | 'metadata'>('modules');
  const [activeCourseId, setActiveCourseId] = useState<string | null>(null);
  
  // Course Management State
  const [showAddCourse, setShowAddCourse] = useState(false);
  const [newCourseTitle, setNewCourseTitle] = useState('');
  const [editingCourseId, setEditingCourseId] = useState<string | null>(null);
  const [editCourseTitle, setEditCourseTitle] = useState('');

  const toast = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const data = await getAdminData();
      setCourseData(data);
      
      // Set active course if none selected or if previously selected is gone
      if (data.courses && data.courses.length > 0) {
        if (!activeCourseId || !data.courses.find(c => c.id === activeCourseId)) {
          setActiveCourseId(data.courses[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load course data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddCourse = async () => {
    if (!newCourseTitle.trim()) return;
    try {
      setIsLoading(true);
      await addCourse(newCourseTitle);
      toast.success('Course created successfully');
      setNewCourseTitle('');
      setShowAddCourse(false);
      await loadData();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create course';
      toast.error(message);
      setIsLoading(false);
    }
  };

  const handleUpdateCourse = async (courseId: string, updates: Partial<Course>) => {
    try {
      setIsLoading(true);
      await updateCourse(courseId, updates);
      toast.success('Course updated');
      await loadData();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update course';
      toast.error(message);
      setIsLoading(false);
    }
  };

  const handleDeleteCourse = async (courseId: string) => {
    if (!window.confirm('Are you sure you want to delete this course? This action cannot be undone.')) return;
    try {
      setIsLoading(true);
      await deleteCourse(courseId);
      toast.success('Course deleted successfully');
      
      // Clear active course if it was the one deleted
      if (activeCourseId === courseId) {
        setActiveCourseId(null);
      }
      
      await loadData();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete course';
      toast.error(message);
      setIsLoading(false);
    }
  };
  
  const saveCourseTitle = async () => {
      if (!editingCourseId || !editCourseTitle.trim()) return;
      await handleUpdateCourse(editingCourseId, { title: editCourseTitle });
      setEditingCourseId(null);
  }

  const handleSaveMetadata = async () => {
    const activeCourse = courseData?.courses?.find(c => c.id === activeCourseId);
    if (!activeCourse) return;
    
    try {
      setIsLoading(true);
      await updateCourse(activeCourse.id, { metadata: activeCourse.metadata });
      toast.success('Metadata saved successfully!');
    } catch (error) {
      console.error('Failed to save metadata:', error);
      const message = error instanceof Error ? error.message : 'Failed to save metadata';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !courseData) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  const activeCourse = courseData?.courses?.find(c => c.id === activeCourseId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Course Content Management</h1>
        <button
          onClick={loadData}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
          title="Refresh Data"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Course Selection & Management */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Courses</h2>
            <button 
                onClick={() => setShowAddCourse(true)}
                className="flex items-center gap-2 text-sm bg-navy text-white px-3 py-1.5 rounded-lg hover:bg-navy/90 transition-colors"
            >
                <Plus className="w-4 h-4" /> Add Course
            </button>
        </div>
        
        {showAddCourse && (
            <div className="mb-4 flex gap-2 items-center bg-gray-50 p-3 rounded-lg">
                <input 
                    type="text" 
                    value={newCourseTitle}
                    onChange={(e) => setNewCourseTitle(e.target.value)}
                    placeholder="New Course Title"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow text-sm"
                />
                <button onClick={handleAddCourse} disabled={isLoading} className="bg-yellow text-navy px-3 py-2 rounded-md font-medium text-sm flex items-center gap-2 disabled:opacity-50">
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create'}
                </button>
                <button onClick={() => setShowAddCourse(false)} disabled={isLoading} className="text-gray-500 hover:text-gray-700 px-2 disabled:opacity-50"><X className="w-5 h-5"/></button>
            </div>
        )}

        <div className="flex gap-2 overflow-x-auto pb-2">
            {courseData?.courses?.map(course => (
                <div 
                    key={course.id}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-all ${
                        activeCourseId === course.id 
                        ? 'bg-yellow/10 border-yellow text-navy shadow-sm' 
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                    onClick={() => setActiveCourseId(course.id)}
                >
                    <BookOpen className="w-4 h-4" />
                    <span className="font-medium whitespace-nowrap">{course.title}</span>
                    {course.isVisible ? (
                        <div title="Visible to students">
                            <Eye className="w-3 h-3 text-green-600" />
                        </div>
                    ) : (
                        <div title="Hidden from students">
                            <EyeOff className="w-3 h-3 text-gray-400" />
                        </div>
                    )}
                </div>
            ))}
            {(!courseData?.courses || courseData.courses.length === 0) && (
                <p className="text-gray-400 text-sm italic">No courses found. Add one to get started.</p>
            )}
        </div>
      </div>

      {activeCourse ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
             {/* Active Course Header */}
             <div className="border-b border-gray-200 p-6 bg-gray-50/50">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                        {editingCourseId === activeCourse.id ? (
                            <div className="flex items-center gap-2">
                                <input 
                                    value={editCourseTitle}
                                    onChange={(e) => setEditCourseTitle(e.target.value)}
                                    className="text-2xl font-bold bg-white border border-gray-300 rounded px-2 py-1"
                                />
                                <button onClick={saveCourseTitle} className="text-green-600 hover:bg-green-50 p-1 rounded"><Check className="w-5 h-5"/></button>
                                <button onClick={() => setEditingCourseId(null)} className="text-red-500 hover:bg-red-50 p-1 rounded"><X className="w-5 h-5"/></button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-3">
                                <h2 className="text-2xl font-bold text-gray-900">{activeCourse.title}</h2>
                                <button 
                                    onClick={() => {
                                        setEditingCourseId(activeCourse.id);
                                        setEditCourseTitle(activeCourse.title);
                                        // Scroll to top so the edit controls are visible
                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                    }}
                                    className="text-gray-400 hover:text-gray-600"
                                >
                                    <Edit2 className="w-4 h-4" />
                                </button>
                            </div>
                        )}
                        
                        <div className={`px-3 py-1 rounded-full text-xs font-medium border ${
                            activeCourse.isVisible 
                            ? 'bg-green-100 text-green-700 border-green-200' 
                            : 'bg-gray-100 text-gray-600 border-gray-200'
                        }`}>
                            {activeCourse.isVisible ? 'Published' : 'Draft'}
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => handleUpdateCourse(activeCourse.id, { isVisible: !activeCourse.isVisible })}
                            disabled={isLoading}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-70 ${
                                activeCourse.isVisible
                                ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                                : 'bg-green-600 text-white hover:bg-green-700 shadow-sm'
                            }`}
                        >
                            {isLoading ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> {activeCourse.isVisible ? 'Hiding...' : 'Publishing...'}</>
                            ) : activeCourse.isVisible ? (
                                <><EyeOff className="w-4 h-4" /> Hide Course</>
                            ) : (
                                <><Eye className="w-4 h-4" /> Publish Course</>
                            )}
                        </button>

                        <button
                            onClick={() => handleDeleteCourse(activeCourse.id)}
                            disabled={isLoading}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 border border-transparent hover:border-red-200"
                            title="Delete Course"
                        >
                             <Trash2 className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-4 border-b border-gray-200 -mb-6">
                    <button
                    onClick={() => setActiveTab('modules')}
                    className={`pb-4 px-2 font-medium text-sm transition-colors border-b-2 ${
                        activeTab === 'modules'
                        ? 'border-yellow-600 text-yellow-600'
                        : 'border-transparent text-gray-500 hover:text-gray-900'
                    }`}
                    >
                    Modules
                    </button>
                    <button
                    onClick={() => setActiveTab('metadata')}
                    className={`pb-4 px-2 font-medium text-sm transition-colors border-b-2 ${
                        activeTab === 'metadata'
                        ? 'border-yellow-600 text-yellow-600'
                        : 'border-transparent text-gray-500 hover:text-gray-900'
                    }`}
                    >
                    Metadata
                    </button>
                </div>
             </div>

            <div className="p-6">
                {activeTab === 'modules' && (
                    <ModuleEditor 
                        modules={activeCourse.modules} 
                        courseId={activeCourse.id}
                        onUpdate={loadData} 
                    />
                )}

                {activeTab === 'metadata' && (
                    <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm max-w-2xl">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-lg font-bold text-gray-900">Course Information</h3>
                        <button
                        onClick={handleSaveMetadata}
                        disabled={isLoading}
                        className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold hover:bg-yellow-hover transition-colors disabled:opacity-50 flex items-center gap-2 text-sm"
                        >
                        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                        Save Changes
                        </button>
                    </div>
                    
                    <div className="space-y-6">
                        <div>
                            <label className="block text-gray-700 font-semibold mb-2 text-sm">Course Description</label>
                            <textarea
                                value={activeCourse.metadata.description || ''}
                                onChange={(e) => {
                                    if (!courseData || !courseData.courses) return;
                                    const newCourses = courseData.courses.map(c => {
                                        if (c.id === activeCourse.id) {
                                            return {
                                                ...c,
                                                metadata: { ...c.metadata, description: e.target.value }
                                            };
                                        }
                                        return c;
                                    });
                                    setCourseData({ ...courseData, courses: newCourses });
                                }}
                                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow text-sm min-h-[120px]"
                                placeholder="Enter course description..."
                            />
                        </div>

                        <div>
                            <label className="block text-gray-700 font-semibold mb-2 text-sm">Schedule Information</label>
                            <input
                            type="text"
                            value={activeCourse.metadata.schedule || ''}
                            onChange={(e) => {
                                if (!courseData || !courseData.courses) return;
                                const newCourses = courseData.courses.map(c => {
                                    if (c.id === activeCourse.id) {
                                        return {
                                            ...c,
                                            metadata: { ...c.metadata, schedule: e.target.value }
                                        };
                                    }
                                    return c;
                                });
                                setCourseData({ ...courseData, courses: newCourses });
                            }}
                            className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow text-sm"
                            placeholder="e.g., Fridays (6 PM – 8 PM: Theory)..."
                            />
                        </div>
                    </div>
                    
                    <div className="mt-6 border-t border-gray-100 pt-6">
                        <PricingTiersEditor 
                            pricing={activeCourse.metadata.pricing || {}} 
                            onChange={(newPricing) => {
                                if (!courseData || !courseData.courses) return;
                                const newCourses = courseData.courses.map(c => {
                                    if (c.id === activeCourse.id) {
                                        return {
                                            ...c,
                                            metadata: { 
                                                ...c.metadata, 
                                                pricing: newPricing 
                                            }
                                        };
                                    }
                                    return c;
                                });
                                setCourseData({ ...courseData, courses: newCourses });
                            }}
                        />
                    </div>
                    </div>
                )}
            </div>
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200 border-dashed">
            <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No courses selected</h3>
            <p className="text-gray-500 mb-6">Select a course to view its content</p>
        </div>
      )}
    </div>
  );
};

export default CourseContent;