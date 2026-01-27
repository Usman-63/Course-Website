import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Search, FileText, 
  Mail, Loader2, RefreshCw, 
  ArrowUpDown, ArrowUp, ArrowDown, Settings, X, CheckSquare, Square
} from 'lucide-react';
import { 
  getRegisterStudents,
  getSurveyStudents,
  StudentOperations,
} from '../../services/api';
import { useToast } from '../Toast';

const StudentOperationsManager: React.FC = () => {
  const toast = useToast();
  const [registerStudents, setRegisterStudents] = useState<StudentOperations[]>([]);
  const [surveyStudents, setSurveyStudents] = useState<StudentOperations[]>([]);
  const [activeTab, setActiveTab] = useState<'register' | 'survey'>('register');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  
  // Sort and Filter state
  const [sortBy, setSortBy] = useState<'name' | 'email' | 'payment' | 'timestamp'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const loadingRef = useRef(false); 
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set());
  const columnSelectorRef = useRef<HTMLDivElement>(null);
  const [isForceRefreshing, setIsForceRefreshing] = useState(false);

  // Load column preferences when tab changes
  useEffect(() => {
    loadColumnPreferences();
  }, [activeTab]);

  // Extract available columns from student data
  useEffect(() => {
    const currentStudents = activeTab === 'register' ? registerStudents : surveyStudents;
    if (currentStudents.length > 0) {
      const allColumns = new Set<string>();
      currentStudents.forEach(student => {
        Object.keys(student).forEach(key => {
          // Exclude internal/private fields and complex objects
          if (!key.startsWith('_') && key !== 'Attendance') {
            allColumns.add(key);
          }
        });
      });
      
      // Add standard columns based on active tab
      if (activeTab === 'register') {
        allColumns.add('Student');
        allColumns.add('Payment');
        allColumns.add('Onboarding');
        allColumns.add('Module 1');
      } else {
        allColumns.add('Student Full Name');
        allColumns.add('Resume');
      }
      
      const sortedColumns = Array.from(allColumns).sort();
      setAvailableColumns(sortedColumns);
    }
  }, [registerStudents, surveyStudents, activeTab]);

  // Load column preferences from localStorage (tab-specific)
  const loadColumnPreferences = () => {
    try {
      const key = `student_operations_visible_columns_${activeTab}`;
      const saved = localStorage.getItem(key);
      if (saved) {
        const columns = JSON.parse(saved);
        setVisibleColumns(new Set(columns));
      } else {
        // Set default columns if no saved preferences
        if (activeTab === 'register') {
          setVisibleColumns(new Set(['Student', 'Payment', 'Onboarding', 'Module 1']));
        } else {
          setVisibleColumns(new Set(['Student Full Name', 'Resume']));
        }
      }
    } catch (error) {
      console.error('Failed to load column preferences:', error);
      // Set defaults on error
      if (activeTab === 'register') {
        setVisibleColumns(new Set(['Student', 'Payment', 'Onboarding', 'Module 1']));
      } else {
        setVisibleColumns(new Set(['Student Full Name', 'Resume']));
      }
    }
  };

  // Save column preferences to localStorage (tab-specific)
  const saveColumnPreferences = (columns: Set<string>) => {
    try {
      const key = `student_operations_visible_columns_${activeTab}`;
      localStorage.setItem(key, JSON.stringify(Array.from(columns)));
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
    setVisibleColumns(newVisible);
    saveColumnPreferences(newVisible);
  };

  // Deselect all columns
  const deselectAllColumns = () => {
    const newVisible = new Set<string>();
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

  // Load data with debouncing to prevent duplicate requests
  const loadData = useCallback(async (forceRefresh = false) => {
    // Prevent duplicate concurrent calls
    if (!forceRefresh && loadingRef.current) {
      return;
    }
    
    try {
      loadingRef.current = true;
      setLoading(true);
      
      // Load both Register and Survey data separately (no backend sorting needed, we sort on frontend)
      const [registerRes, surveyRes] = await Promise.all([
        getRegisterStudents('name', 'asc', forceRefresh),
        getSurveyStudents('name', 'asc', forceRefresh),
      ]);
      
      setRegisterStudents(registerRes.students || []);
      setSurveyStudents(surveyRes.students || []);
    } catch (error: unknown) {
      console.error('Failed to load operations data:', error);
      const message =
        error instanceof Error ? error.message : 'Failed to load student operations data';
      toast.error(message);
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [toast]);

  // Debounce loadData to prevent rapid successive calls
  useEffect(() => {
    // Set a timeout to debounce the request
    const timeoutId = setTimeout(() => {
      loadData();
    }, 300); // 300ms debounce delay

    // Cleanup function to cancel the timeout if component unmounts or dependencies change
    return () => clearTimeout(timeoutId);
  }, [loadData]); // Depend on loadData which already depends on sortBy/sortOrder

  const handleForceRefreshFromResponses = async () => {
    try {
      setIsForceRefreshing(true);
      toast.info('Refreshing data from Google Form responses. This can take 10–30 seconds on first load.');
      await loadData(true);
      toast.success('Student data refreshed from latest form responses.');
    } catch (err: unknown) {
      console.error('Failed to refresh from responses:', err);
      const message =
        err instanceof Error ? err.message : 'Failed to refresh from responses';
      toast.error(message);
    } finally {
      setIsForceRefreshing(false);
    }
  };

  const handleCopyEmails = async () => {
    try {
      const currentStudents = activeTab === 'register' ? registerStudents : surveyStudents;
      const emails = currentStudents
        .map(s => s['Email Address'])
        .filter((e): e is string => !!e && e.trim().length > 0);

      if (emails.length === 0) {
        toast.error('No emails found for this tab.');
        return;
      }

      const uniqueEmails = Array.from(new Set(emails));
      const emailsString = uniqueEmails.join(', ');

      await navigator.clipboard.writeText(emailsString);
      toast.success(`Copied ${uniqueEmails.length} ${activeTab === 'register' ? 'Register' : 'Survey'} emails to clipboard`);
    } catch (error: unknown) {
      console.error('Failed to copy emails:', error);
      const message =
        error instanceof Error ? error.message : 'Failed to copy emails';
      toast.error(message);
    }
  };

  const getStudentName = (student: StudentOperations): string => {
    // For Register tab, combine First Name + Last Name
    if (activeTab === 'register') {
      const firstName = student['First Name'] || '';
      const lastName = student['Last Name'] || '';
      if (firstName || lastName) {
        return `${firstName} ${lastName}`.trim();
      }
    }
    
    // For Survey tab or fallback, use Student Full Name or other name fields
    return student['Student Full Name'] ||
           student.Name || 
           student.name ||
           student['Student Name'] || 
           'N/A';
  };

  const filteredStudents = (() => {
    const students = activeTab === 'register' ? registerStudents : surveyStudents;
    
    // First filter by search term
    const filtered = students.filter(student => {
      const email = student['Email Address'] || '';
      const name = getStudentName(student);
      const search = searchTerm.toLowerCase();
      return email.toLowerCase().includes(search) || name.toLowerCase().includes(search);
    });
    
    // Then sort the filtered results
    const sorted = [...filtered].sort((a, b) => {
      let aValue: any = '';
      let bValue: any = '';
      
      if (sortBy === 'name') {
        aValue = getStudentName(a).toLowerCase();
        bValue = getStudentName(b).toLowerCase();
      } else if (sortBy === 'email') {
        aValue = (a['Email Address'] || '').toLowerCase();
        bValue = (b['Email Address'] || '').toLowerCase();
      } else if (sortBy === 'payment') {
        if (activeTab === 'register') {
          aValue = (a['Payment proved'] || '').toString().toLowerCase();
          bValue = (b['Payment proved'] || '').toString().toLowerCase();
        } else {
          return 0; // Payment sorting not applicable for Survey tab
        }
      } else if (sortBy === 'timestamp') {
        aValue = a['Timestamp'] || a['timestamp'] || '';
        bValue = b['Timestamp'] || b['timestamp'] || '';
      }
      
      // Compare values
      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  })();

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

  // Get ordered list of visible columns (standard columns first, then others)
  const getVisibleColumnsOrdered = (): string[] => {
    const visible = Array.from(visibleColumns);
    const ordered: string[] = [];
    
    if (activeTab === 'register') {
      // Register tab: Student, Payment, Onboarding, Module 1, then others
      const standardOrder = ['Student', 'Payment', 'Onboarding', 'Module 1'];
      standardOrder.forEach(col => {
        if (visible.includes(col)) {
          ordered.push(col);
        }
      });
      
      // Add other visible columns (excluding standard columns)
      const otherColumns = visible.filter(col => !standardOrder.includes(col));
      ordered.push(...otherColumns.sort());
    } else {
      // Survey tab: Student Full Name, Resume, then others
      const standardOrder = ['Student Full Name', 'Resume'];
      standardOrder.forEach(col => {
        if (visible.includes(col)) {
          ordered.push(col);
        }
      });
      
      // Add other visible columns (excluding standard columns)
      const otherColumns = visible.filter(col => !standardOrder.includes(col));
      ordered.push(...otherColumns.sort());
    }
    
    return ordered;
  };

  // Render cell content based on column type
  const renderCell = (column: string, student: StudentOperations): React.ReactNode => {
    // Register tab: Student column (First Name + Last Name)
    if (column === 'Student' && activeTab === 'register') {
      const email = student['Email Address'] || '';
      return (
        <div className="flex flex-col gap-1">
          <div className="font-bold text-gray-900 text-base">{getStudentName(student)}</div>
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <Mail className="w-3 h-3" />
            {email}
          </div>
        </div>
      );
    }
    
    // Survey tab: Student Full Name column
    if (column === 'Student Full Name' && activeTab === 'survey') {
      const email = student['Email Address'] || '';
      const fullName = student['Student Full Name'] || 'N/A';
      return (
        <div className="flex flex-col gap-1">
          <div className="font-bold text-gray-900 text-base">{fullName}</div>
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <Mail className="w-3 h-3" />
            {email}
          </div>
        </div>
      );
    }
    
    // Payment column: Show "Payment proved" (yes/no) for Register tab
    if (column === 'Payment' && activeTab === 'register') {
      const paymentProved = (student['Payment proved'] || '').toString().toLowerCase().trim();
      let badgeText = 'Not Set';
      let badgeColor = 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      
      if (paymentProved === 'yes') {
        badgeText = 'Yes';
        badgeColor = 'bg-green-500/20 text-green-400 border-green-500/30';
      } else if (paymentProved === 'no') {
        badgeText = 'No';
        badgeColor = 'bg-red-500/20 text-red-400 border-red-500/30';
      }
      
      return (
        <span className={`px-3 py-1.5 rounded-full text-xs font-semibold border inline-flex items-center gap-1.5 ${badgeColor}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${paymentProved === 'yes' ? 'bg-green-400' : paymentProved === 'no' ? 'bg-red-400' : 'bg-gray-400'}`} />
          {badgeText}
        </span>
      );
    }
    
    // Resume column: Show Uploaded/Not Uploaded badge for Survey tab
    if (column === 'Resume' && activeTab === 'survey') {
      // Use exact column name (check both with and without trailing spaces)
      const resumeValue = student['Upload your Resume / CV (PDF preferred)  '] || 
                         student['Upload your Resume / CV (PDF preferred)'] || '';
      
      // Check if resume exists
      const resumeStr = resumeValue ? String(resumeValue).trim() : '';
      const hasResume = resumeStr !== '' && 
                       resumeStr.toLowerCase() !== 'n/a' &&
                       resumeStr.toLowerCase() !== 'nan' &&
                       resumeStr !== 'undefined' &&
                       resumeStr !== 'null';
      
      const badgeText = hasResume ? 'Uploaded' : 'Not Uploaded';
      const badgeColor = hasResume 
        ? 'bg-green-500/20 text-green-400 border-green-500/30'
        : 'bg-red-500/20 text-red-400 border-red-500/30';
      
      return (
        <span className={`px-3 py-1.5 rounded-full text-xs font-semibold border inline-flex items-center gap-1.5 ${badgeColor}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${hasResume ? 'bg-green-400' : 'bg-red-400'}`} />
          {badgeText}
        </span>
      );
    }
    
    // Generic columns: Onboarding, Module 1, or any other form column
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
          // Determine sortable columns based on active tab
          let isSortable = false;
          let sortField: 'name' | 'email' | 'payment' | 'timestamp' | null = null;
          
          if (activeTab === 'register') {
            if (column === 'Student') {
              isSortable = true;
              sortField = 'name';
            } else if (column === 'Payment') {
              isSortable = true;
              sortField = 'payment';
            }
          } else {
            if (column === 'Student Full Name') {
              isSortable = true;
              sortField = 'name';
            }
          }
          
          return (
            <th
              key={column}
              className={`px-6 py-4 font-bold ${isSortable ? 'cursor-pointer hover:text-primary transition-colors group' : ''}`}
              onClick={isSortable && sortField ? () => handleSort(sortField) : undefined}
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

  if (loading && registerStudents.length === 0 && surveyStudents.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-yellow animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Tabs */}
      <div className="flex flex-col gap-4">
        <div className="flex bg-gray-100 p-1 rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('register')}
            className={`px-6 py-3 rounded-lg font-bold text-sm flex items-center gap-2 transition-all ${
              activeTab === 'register' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <FileText className="w-4 h-4" />
            Register Form ({registerStudents.length})
          </button>
          <button
            onClick={() => setActiveTab('survey')}
            className={`px-6 py-3 rounded-lg font-bold text-sm flex items-center gap-2 transition-all ${
              activeTab === 'survey' 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <FileText className="w-4 h-4" />
            Survey Form ({surveyStudents.length})
          </button>
        </div>

        <div className="flex gap-2">
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
                      // Determine if column is standard based on active tab
                      let isStandard = false;
                      if (activeTab === 'register') {
                        isStandard = ['Student', 'Payment', 'Onboarding', 'Module 1'].includes(column);
                      } else {
                        isStandard = ['Student Full Name', 'Resume'].includes(column);
                      }
                      
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
            onClick={handleForceRefreshFromResponses}
            disabled={isForceRefreshing}
            title="Force a full refresh from Google Sheets (Register + Survey). Use this after new form responses are submitted."
            className={`bg-white border border-gray-200 text-gray-600 px-5 py-2.5 rounded-xl font-semibold transition-all flex items-center gap-2 shadow-sm ${
              isForceRefreshing ? 'opacity-70 cursor-not-allowed' : 'hover:bg-gray-50'
            }`}
          >
            <RefreshCw className={`w-4 h-4 ${isForceRefreshing ? 'animate-spin' : ''}`} />
            <span>{isForceRefreshing ? 'Refreshing from responses…' : 'Get Data from Responses'}</span>
          </button>
          <button
            onClick={handleCopyEmails}
            title="Copy the current list of student emails to your clipboard."
            className="bg-yellow text-white px-5 py-2.5 rounded-xl font-bold hover:bg-yellow-hover transition-all flex items-center gap-2 shadow-lg shadow-yellow/20"
          >
            <Mail className="w-4 h-4" />
            Copy Emails
          </button>
        </div>
      </div>

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
          Showing <span className="text-gray-900 font-bold">{filteredStudents.length}</span> {activeTab === 'register' ? 'Register' : 'Survey'} entries
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
    </div>
  );
};

export default StudentOperationsManager;

