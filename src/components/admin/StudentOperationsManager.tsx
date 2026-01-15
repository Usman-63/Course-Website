import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Users, Search, DollarSign, FileText, 
  Mail, Loader2, AlertCircle, TrendingUp, RefreshCw, 
  ArrowUpDown, ArrowUp, ArrowDown, Settings, X, CheckSquare, Square,
  MoreHorizontal, ChevronRight, Calendar, List
} from 'lucide-react';
import { 
  getStudentsOperationsCombined,
  updateStudentOperations,
  getOperationsEmails,
  getCourseData,
  StudentOperations,
  OperationsMetrics,
  OperationsStatus
} from '../../services/api';
import { useToast } from '../Toast';
import StudentEditSheet from './StudentEditSheet';
import AttendanceManager from './AttendanceManager';

const StudentOperationsManager: React.FC = () => {
  const toast = useToast();
  const [students, setStudents] = useState<StudentOperations[]>([]);
  const [metrics, setMetrics] = useState<OperationsMetrics | null>(null);
  const [status, setStatus] = useState<OperationsStatus | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'list' | 'attendance'>('list');

  // Edit Sheet State
  const [isEditSheetOpen, setIsEditSheetOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<StudentOperations | null>(null);
  
  // Sort and Filter state
  const [sortBy, setSortBy] = useState<'name' | 'email' | 'payment' | 'timestamp'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [totalLabs, setTotalLabs] = useState<number>(2);
  const loadingRef = useRef(false); 
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set(['Student', 'Payment', 'Attendance', 'Grades', 'Actions']));
  const [showDebug, setShowDebug] = useState(false);
  const columnSelectorRef = useRef<HTMLDivElement>(null);

  // Load course data only once on mount
  useEffect(() => {
    loadCourseData();
    loadColumnPreferences();
  }, []);

  // Extract available columns from student data
  useEffect(() => {
    if (students.length > 0) {
      const allColumns = new Set<string>();
      students.forEach(student => {
        Object.keys(student).forEach(key => {
          // Exclude internal/private fields and complex objects
          if (!key.startsWith('_') && key !== 'Attendance') {
            allColumns.add(key);
          }
        });
      });
      
      // Add standard columns that are always available
      const standardColumns = ['Student', 'Payment', 'Attendance', 'Grades', 'Actions'];
      standardColumns.forEach(col => allColumns.add(col));
      
      // Add assignment grade columns dynamically
      for (let i = 1; i <= totalLabs; i++) {
        allColumns.add(`Assignment ${i} Grade`);
      }
      
      const sortedColumns = Array.from(allColumns).sort();
      setAvailableColumns(sortedColumns);
    }
  }, [students, totalLabs]);

  // Load column preferences from localStorage
  const loadColumnPreferences = () => {
    try {
      const saved = localStorage.getItem('student_operations_visible_columns');
      if (saved) {
        const columns = JSON.parse(saved);
        setVisibleColumns(new Set(columns));
      }
    } catch (error) {
      console.error('Failed to load column preferences:', error);
    }
  };

  // Save column preferences to localStorage
  const saveColumnPreferences = (columns: Set<string>) => {
    try {
      localStorage.setItem('student_operations_visible_columns', JSON.stringify(Array.from(columns)));
    } catch (error) {
      console.error('Failed to save column preferences:', error);
    }
  };

  // Handle column visibility toggle
  const toggleColumn = (column: string) => {
    const newVisible = new Set(visibleColumns);
    if (newVisible.has(column)) {
      newVisible.delete(column);
    } else {
      newVisible.add(column);
    }
    setVisibleColumns(newVisible);
    saveColumnPreferences(newVisible);
  };

  // Select all columns
  const selectAllColumns = () => {
    const newVisible = new Set(availableColumns);
    // Always keep Actions column
    newVisible.add('Actions');
    setVisibleColumns(newVisible);
    saveColumnPreferences(newVisible);
  };

  // Deselect all columns (except Actions)
  const deselectAllColumns = () => {
    const newVisible = new Set(['Actions']);
    setVisibleColumns(newVisible);
    saveColumnPreferences(newVisible);
  };

  // Close column selector when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (columnSelectorRef.current && !columnSelectorRef.current.contains(event.target as Node)) {
        setShowColumnSelector(false);
      }
    };

    if (showColumnSelector) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showColumnSelector]);

  const loadCourseData = async () => {
    try {
      const courseData = await getCourseData();
      if (courseData?.modules) {
        const labs = courseData.modules.reduce((sum: number, module: any) => {
          return sum + (module.labCount || 1);
        }, 0);
        setTotalLabs(labs || 2);
      }
    } catch (error) {
      console.error('Failed to load course data:', error);
    }
  };

  // Load data with debouncing to prevent duplicate requests
  const loadData = useCallback(async (forceRefresh = false) => {
    // Prevent duplicate concurrent calls
    if (loadingRef.current) {
      console.log('Load already in progress, skipping duplicate call');
      return;
    }
    
    try {
      loadingRef.current = true;
      setLoading(true);
      
      // Single API call instead of 3 parallel calls - much more efficient!
      const res = await getStudentsOperationsCombined(sortBy, sortOrder, typeof forceRefresh === 'boolean' ? forceRefresh : false);
      
      setStudents(res.students || []);
      setMetrics(res.metrics || null);
      setStatus(res.status || null);
    } catch (error: any) {
      console.error('Failed to load operations data:', error);
      toast.error(error.message || 'Failed to load student operations data');
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [sortBy, sortOrder, toast]);

  // Debounce loadData to prevent rapid successive calls
  useEffect(() => {
    // Set a timeout to debounce the request
    const timeoutId = setTimeout(() => {
      loadData();
    }, 300); // 300ms debounce delay

    // Cleanup function to cancel the timeout if component unmounts or dependencies change
    return () => clearTimeout(timeoutId);
  }, [loadData]); // Depend on loadData which already depends on sortBy/sortOrder

  const handleUpdateStudent = async (email: string, updates: Partial<StudentOperations>) => {
    try {
      await updateStudentOperations(email, updates);
      toast.success('Student data updated successfully');
      loadData();
      // Keep sheet open or close it? Usually close it on success
      setIsEditSheetOpen(false);
      setSelectedStudent(null);
    } catch (error: any) {
      console.error('Failed to update student:', error);
      toast.error(error.message || 'Failed to update student data');
      throw error; // Re-throw so the sheet knows it failed
    }
  };

  const handleEditClick = (student: StudentOperations) => {
    setSelectedStudent(student);
    setIsEditSheetOpen(true);
  };

  const handleCopyEmails = async () => {
    try {
      const res = await getOperationsEmails();
      await navigator.clipboard.writeText(res.emails_string);
      toast.success(`Copied ${res.count} emails to clipboard`);
    } catch (error: any) {
      console.error('Failed to copy emails:', error);
      toast.error(error.message || 'Failed to copy emails');
    }
  };

  const getStudentName = (student: StudentOperations): string => {
    return student.Name || 
           student.name ||
           student['Student Name'] ||
           student['Student Full Name'] || 
           (student['First Name'] && student['Last Name'] 
             ? `${student['First Name']} ${student['Last Name']}` 
             : student['First Name'] || student['Last Name'] || 'N/A');
  };

  const filteredStudents = students.filter(student => {
    const email = student['Email Address'] || '';
    const name = getStudentName(student);
    const search = searchTerm.toLowerCase();
    return email.toLowerCase().includes(search) || name.toLowerCase().includes(search);
  });

  const handleSort = (field: 'name' | 'email' | 'payment' | 'timestamp') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const getSortIcon = (field: 'name' | 'email' | 'payment' | 'timestamp') => {
    if (sortBy !== field) {
      return <ArrowUpDown className="w-4 h-4 ml-1 opacity-50" />;
    }
    return sortOrder === 'asc' 
      ? <ArrowUp className="w-4 h-4 ml-1" />
      : <ArrowDown className="w-4 h-4 ml-1" />;
  };

  const getPaymentStatusColor = (status?: string) => {
    const s = (status || '').toLowerCase();
    if (s === 'paid') return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (s === 'pending') return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    return 'bg-red-500/20 text-red-400 border-red-500/30';
  };

  const parseAttendance = (attendance: Record<string, boolean> | string | undefined): Record<string, boolean> => {
    if (!attendance) return {};
    if (typeof attendance === 'string') {
      try {
        return JSON.parse(attendance);
      } catch {
        return {};
      }
    }
    return attendance;
  };

  // Get ordered list of visible columns (standard columns first, then others)
  const getVisibleColumnsOrdered = (): string[] => {
    const standardOrder = ['Student', 'Payment', 'Attendance', 'Grades'];
    const visible = Array.from(visibleColumns);
    const ordered: string[] = [];
    
    // Add standard columns in order if visible
    standardOrder.forEach(col => {
      if (visible.includes(col)) {
        ordered.push(col);
      }
    });
    
    // Add other visible columns (excluding standard columns and Actions)
    const otherColumns = visible.filter(col => !standardOrder.includes(col) && col !== 'Actions');
    ordered.push(...otherColumns.sort());
    
    // Always add Actions last if visible
    if (visible.includes('Actions')) {
      ordered.push('Actions');
    }
    
    return ordered;
  };

  // Render cell content based on column type
  const renderCell = (column: string, student: StudentOperations): React.ReactNode => {
    if (column === 'Student') {
      const email = student['Email Address'] || '';
      const resumeLink = student['Resume Link'] || student['Upload your Resume / CV (PDF preferred)'];
      return (
        <div className="flex flex-col gap-1">
          <div className="font-bold text-gray-900 text-base">{getStudentName(student)}</div>
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <Mail className="w-3 h-3" />
            {email}
          </div>
          {resumeLink && (
            <a 
              href={resumeLink} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-yellow-600 hover:text-yellow-700 hover:underline flex items-center gap-1 mt-1 w-fit"
            >
              <FileText className="w-3 h-3" />
              View Resume
            </a>
          )}
        </div>
      );
    }
    
    if (column === 'Payment') {
      const status = student['Payment Status'] || 'Unpaid';
      const colorClass = getPaymentStatusColor(status);
      return (
        <span className={`px-3 py-1.5 rounded-full text-xs font-semibold border inline-flex items-center gap-1.5 ${colorClass}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${status.toLowerCase() === 'paid' ? 'bg-green-400' : 'bg-current'}`} />
          {status}
        </span>
      );
    }
    
    if (column === 'Attendance') {
      const attendance = parseAttendance(student.Attendance);
      const attendanceCount = Object.values(attendance).filter(Boolean).length;
      const totalClasses = Object.keys(attendance).length;
      
      if (totalClasses === 0) return <span className="text-gray-600">-</span>;

      const percentage = Math.round((attendanceCount / totalClasses) * 100);
      const color = percentage >= 80 ? 'text-green-600' : percentage >= 50 ? 'text-yellow-600' : 'text-red-600';
      
      return (
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className={`text-lg font-bold ${color}`}>{percentage}%</span>
            <span className="text-xs text-gray-500">({attendanceCount}/{totalClasses})</span>
          </div>
          <div className="w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full ${percentage >= 80 ? 'bg-green-500' : percentage >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`} 
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
      );
    }
    
    if (column === 'Grades') {
      return (
        <div className="flex flex-wrap gap-2 max-w-[200px]">
          {Array.from({ length: totalLabs }, (_, i) => {
            const assignmentNum = i + 1;
            const gradeKey = `Assignment ${assignmentNum} Grade`;
            const grade = student[gradeKey];
            
            if (!grade) return null;

            return (
              <div key={i} className="flex flex-col bg-gray-100 rounded px-2 py-1 border border-gray-200">
                <span className="text-[10px] text-gray-500 uppercase tracking-wider">A{assignmentNum}</span>
                <span className="text-sm font-mono font-bold text-gray-900">{grade}</span>
              </div>
            );
          })}
          {!Array.from({ length: totalLabs }).some((_, i) => student[`Assignment ${i + 1} Grade`]) && (
             <span className="text-gray-600">-</span>
          )}
        </div>
      );
    }
    
    if (column === 'Actions') {
      const hasEmail = !!student['Email Address'];
      return (
        <div className="relative group">
          <button
            onClick={() => handleEditClick(student)}
            disabled={!hasEmail}
            className={`p-2 rounded-lg transition-all ${
              hasEmail 
                ? 'text-gray-400 hover:text-gray-900 hover:bg-gray-100' 
                : 'text-gray-300 cursor-not-allowed'
            }`}
            title={hasEmail ? "Edit Student" : "Email required for actions"}
          >
            <Settings className="w-5 h-5" />
          </button>
          {!hasEmail && (
            <div className="absolute right-full mr-2 top-1/2 -translate-y-1/2 w-48 p-2 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 text-center">
              Set an email first before any actions can be performed.
            </div>
          )}
        </div>
      );
    }
    
    // Generic column - display raw value
    const value = student[column];
    if (value === null || value === undefined || value === '') {
      return <span className="text-gray-400">-</span>;
    }
    
    // Handle different value types
    if (typeof value === 'object') {
      return <span className="text-gray-500 text-sm font-mono bg-gray-100 px-2 py-1 rounded border border-gray-200">{JSON.stringify(value)}</span>;
    }
    
    return <span className="text-gray-700 text-sm">{String(value)}</span>;
  };

  // Render table header
  const renderTableHeader = () => {
    const columns = getVisibleColumnsOrdered();
    return (
      <tr className="bg-sky-50 text-gray-600 text-xs font-bold uppercase tracking-wider border-b border-gray-200">
        {columns.map((column) => {
          const isSortable = column === 'Student' || column === 'Payment';
          const sortField = column === 'Student' ? 'name' : column === 'Payment' ? 'payment' : null;
          
          return (
            <th
              key={column}
              className={`px-6 py-4 font-bold ${isSortable ? 'cursor-pointer hover:text-primary transition-colors group' : ''}`}
              onClick={isSortable && sortField ? () => handleSort(sortField as 'name' | 'payment') : undefined}
            >
              <div className="flex items-center gap-2">
                {column}
                {isSortable && sortField && (
                  <span className={`transition-opacity ${sortBy === sortField ? 'opacity-100' : 'opacity-0 group-hover:opacity-50'}`}>
                    {getSortIcon(sortField)}
                  </span>
                )}
              </div>
            </th>
          );
        })}
      </tr>
    );
  };

  if (loading && students.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-yellow animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex bg-gray-100 p-1 rounded-xl">
          <button
            onClick={() => setViewMode('list')}
            className={`px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all ${
              viewMode === 'list' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <List className="w-4 h-4" />
            List View
          </button>
          <button
            onClick={() => setViewMode('attendance')}
            className={`px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all ${
              viewMode === 'attendance' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <Calendar className="w-4 h-4" />
            Attendance
          </button>
        </div>

        {viewMode === 'list' && (
        <div className="flex gap-2">
          <button
            onClick={() => setShowDebug(!showDebug)}
            className={`px-4 py-2 rounded-lg font-semibold border transition-colors ${showDebug ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
          >
            Debug
          </button>
          <div className="relative" ref={columnSelectorRef}>
            <button
              onClick={() => setShowColumnSelector(!showColumnSelector)}
              className="bg-white border border-gray-200 text-gray-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Columns
            </button>
            {showColumnSelector && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl border border-gray-200 shadow-2xl z-50 max-h-96 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                  <h4 className="text-gray-900 font-semibold">Select Columns</h4>
                  <button
                    onClick={() => setShowColumnSelector(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="p-2 border-b border-gray-100 flex gap-2">
                  <button
                    onClick={selectAllColumns}
                    className="flex-1 px-3 py-1.5 text-sm bg-yellow/10 text-yellow-600 rounded-lg hover:bg-yellow/20 transition-colors"
                  >
                    Select All
                  </button>
                  <button
                    onClick={deselectAllColumns}
                    className="flex-1 px-3 py-1.5 text-sm bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Deselect All
                  </button>
                </div>
                <div className="overflow-y-auto flex-1 p-2">
                  <div className="space-y-1">
                    {availableColumns.map((column) => {
                      const isVisible = visibleColumns.has(column);
                      const isStandard = ['Student', 'Payment', 'Attendance', 'Grades', 'Actions'].includes(column);
                      return (
                        <label
                          key={column}
                          onClick={(e) => {
                            e.preventDefault();
                            toggleColumn(column);
                          }}
                          className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                        >
                          {isVisible ? (
                            <CheckSquare className="w-4 h-4 text-primary" />
                          ) : (
                            <Square className="w-4 h-4 text-gray-400" />
                          )}
                          <span className={`text-sm ${isVisible ? 'text-gray-900' : 'text-gray-400'}`}>
                            {column}
                          </span>
                          {isStandard && (
                            <span className="text-xs text-gray-400 ml-auto">(Standard)</span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
          <button
            onClick={() => loadData(true)}
            className="bg-white border border-gray-200 text-gray-600 px-5 py-2.5 rounded-xl font-semibold hover:bg-gray-50 transition-all flex items-center gap-2 shadow-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Get Data from Responses
          </button>
          <button
            onClick={handleCopyEmails}
            className="bg-yellow text-white px-5 py-2.5 rounded-xl font-bold hover:bg-yellow-hover transition-all flex items-center gap-2 shadow-lg shadow-yellow/20"
          >
            <Mail className="w-4 h-4" />
            Copy Emails
          </button>
        </div>
        )}
      </div>

      {viewMode === 'attendance' ? (
        <AttendanceManager students={students} onUpdate={loadData} />
      ) : (
        <>



      {/* Debug View */}
      {showDebug && (
        <div className="bg-gray-900 text-green-400 p-6 rounded-xl overflow-x-auto font-mono text-xs shadow-2xl border border-gray-800">
          <h4 className="text-white font-bold text-lg mb-4 border-b border-gray-800 pb-2">Debug Data Inspection</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h5 className="text-white font-semibold mb-2">Raw Student Data (First 2 Records)</h5>
              <pre>{JSON.stringify(students.slice(0, 2), null, 2)}</pre>
            </div>
            <div>
              <h5 className="text-white font-semibold mb-2">Available Columns Detected</h5>
              <div className="flex flex-wrap gap-2 mb-4">
                {availableColumns.map(col => (
                  <span key={col} className="bg-gray-800 px-2 py-1 rounded text-gray-300">{col}</span>
                ))}
              </div>
              <h5 className="text-white font-semibold mb-2">Metrics Data</h5>
              <pre>{JSON.stringify(metrics, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Metrics View */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm font-medium">Total Students</span>
              <div className="p-2 bg-yellow/10 rounded-full">
                <Users className="w-5 h-5 text-yellow" />
              </div>
            </div>
            <div className="text-3xl font-bold text-gray-900">{metrics.total_students}</div>
          </div>
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm font-medium">Paid</span>
              <div className="p-2 bg-green-100 rounded-full">
                <DollarSign className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <div className="text-3xl font-bold text-green-600">{metrics.paid_count}</div>
            <div className="text-xs text-gray-400 mt-1">
              {metrics.total_students > 0 
                ? Math.round((metrics.paid_count / metrics.total_students) * 100) 
                : 0}% of total
            </div>
          </div>
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm font-medium">Onboarding</span>
              <div className="p-2 bg-yellow/10 rounded-full">
                <TrendingUp className="w-5 h-5 text-yellow" />
              </div>
            </div>
            <div className="text-3xl font-bold text-yellow">{metrics.onboarding_percentage}%</div>
            <div className="text-xs text-gray-400 mt-1">{metrics.has_resume_count} with resume</div>
          </div>
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-500 text-sm font-medium">Unpaid</span>
              <div className="p-2 bg-red-100 rounded-full">
                <AlertCircle className="w-5 h-5 text-red-600" />
              </div>
            </div>
            <div className="text-3xl font-bold text-red-600">{metrics.unpaid_count}</div>
          </div>
        </div>
      )}

      {/* Status Summary */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <h4 className="text-lg font-bold text-gray-900 mb-4">Missing Items</h4>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Missing Payment</span>
                <span className="text-red-600 font-bold bg-red-50 px-2 py-0.5 rounded">{status.missing_payment.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Missing Resume</span>
                <span className="text-yellow-600 font-bold bg-yellow/10 px-2 py-0.5 rounded">{status.missing_resume.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Missing Attendance</span>
                <span className="text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded">{status.missing_attendance.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Missing Grades</span>
                <span className="text-purple-600 font-bold bg-purple-50 px-2 py-0.5 rounded">{status.missing_grades.length}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Student List View */}
          {/* Search */}
          <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-white p-4 rounded-xl border border-gray-100 shadow-sm mb-6">
            <div className="relative w-full md:w-96">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="bg-gray-50 border border-gray-200 rounded-xl py-3 pl-12 pr-4 text-gray-900 focus:border-primary focus:ring-1 focus:ring-primary outline-none w-full transition-all placeholder:text-gray-400"
                placeholder="Search by name, email..."
              />
            </div>
            <div className="text-sm text-gray-500">
              Showing <span className="text-gray-900 font-bold">{filteredStudents.length}</span> students
            </div>
          </div>

          {/* Student Table */}
          <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  {renderTableHeader()}
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredStudents.map((student, idx) => {
                    const columns = getVisibleColumnsOrdered();
                    return (
                      <tr key={idx} className="hover:bg-gray-50 transition-colors group">
                        {columns.map((column) => (
                          <td key={column} className="px-6 py-4 align-middle">
                            {renderCell(column, student)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredStudents.length === 0 && (
                <div className="text-center py-20 text-gray-500 flex flex-col items-center">
                  <Search className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-lg font-medium text-gray-900">No students found</p>
                  <p className="text-sm opacity-60">Try adjusting your search terms</p>
                </div>
              )}
            </div>
          </div>
          
          <StudentEditSheet
            isOpen={isEditSheetOpen}
            onClose={() => {
              setIsEditSheetOpen(false);
              setSelectedStudent(null);
            }}
            student={selectedStudent}
            onSave={handleUpdateStudent}
            totalLabs={totalLabs}
          />
        </>
      )}
      
      {/* Legacy detail view removed in favor of Side Sheet */}
    </div>
  );
};

export default StudentOperationsManager;

