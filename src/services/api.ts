import { fetchWithRetry } from '../utils/fetchWithRetry';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export interface CourseModule {
  id: string;
  title: string;
  hours: number;
  focus: string;
  topics: string[];
  order: number;
  labCount?: number;
  videoLink?: string;
  labLink?: string;
  isVisible?: boolean; // Added visibility flag
}

export interface PricingTier {
  name: string;
  price: number;
  features?: string[];
}

export interface CourseMetadata {
  description?: string;
  schedule: string;
  capstone?: string;
  certification?: string;
  pricing: {
    [key: string]: number | PricingTier;
  };
  earlyAccessOffer?: string;
}

export interface Course {
  id: string;
  title: string;
  isVisible: boolean;
  modules: CourseModule[];
  metadata: CourseMetadata;
  links?: any[];
}

export interface CourseData {
  version: number;
  courses: Course[];
  // Legacy fields for backward compatibility
  modules?: CourseModule[];
  metadata?: CourseMetadata;
}

const COURSE_DATA_CACHE_KEY = 'course_data_cache';
const COURSE_VERSION_CACHE_KEY = 'course_version_cache';

// Get auth token from localStorage
export const getAuthToken = (): string | null => {
  return localStorage.getItem('admin_token');
};

// Set auth token
export const setAuthToken = (token: string): void => {
  localStorage.setItem('admin_token', token);
};

// Clear auth token
export const clearAuthToken = (): void => {
  localStorage.removeItem('admin_token');
};

// Check if admin is logged in
export const isAdminLoggedIn = (): boolean => {
  return !!getAuthToken();
};

export const getCourseVersion = async (): Promise<number> => {
  try {
    const response = await fetchWithRetry(`${API_URL}/api/course/version`, {
      timeout: 5000,
      retries: 2,
    });
    if (!response.ok) return 0;
    const data = await response.json();
    return data.version || 0;
  } catch (error) {
    console.error('Failed to fetch course version:', error);
    return 0;
  }
};

// Public API calls
export const getCourseData = async (): Promise<CourseData> => {
  // 1. Get remote version
  const remoteVersion = await getCourseVersion();

  // 2. Get local version and data
  const localVersion = parseInt(localStorage.getItem(COURSE_VERSION_CACHE_KEY) || '0', 10);
  const cachedData = localStorage.getItem(COURSE_DATA_CACHE_KEY);

  // 3. Compare and return cache if valid
  // If remoteVersion is 0 (error or not set), we default to fetching fresh data unless we really want to rely on cache
  // But typically if we can't verify version, we should probably fetch fresh or use cache if fetch fails.
  // Here we assume if remoteVersion matches localVersion, it's safe.
  if (remoteVersion > 0 && remoteVersion === localVersion && cachedData) {
    try {
      const parsedData = JSON.parse(cachedData);
      console.log('Using cached course data', remoteVersion);
      return parsedData;
    } catch (e) {
      console.warn('Failed to parse cached course data, fetching fresh data');
    }
  }

  console.log('Fetching fresh course data', { remoteVersion, localVersion });
  const response = await fetchWithRetry(`${API_URL}/api/course/data`, {
    timeout: 10000,
    retries: 2,
  });
  if (!response.ok) {
    throw new Error('Failed to fetch course data');
  }
  const data = await response.json();

  // 4. Update cache
  try {
    localStorage.setItem(COURSE_DATA_CACHE_KEY, JSON.stringify(data));
    // Use the version from the fetched data if available, otherwise use the one we just fetched
    const versionToStore = (data as any).version || remoteVersion;
    localStorage.setItem(COURSE_VERSION_CACHE_KEY, versionToStore.toString());
  } catch (e) {
    console.warn('Failed to cache course data:', e);
  }

  return data;
};

// Admin API calls
export const adminLogin = async (password: string): Promise<{ success: boolean; message?: string; error?: string; token?: string; firebase_token?: string }> => {
  const response = await fetchWithRetry(`${API_URL}/api/admin/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ password }),
    timeout: 10000,
    retries: 1, // Don't retry login attempts too many times
  });
  
  if (response.status === 429) {
    return { success: false, error: 'Too many login attempts. Please try again later.' };
  }
  
  return response.json();
};

export const getFirebaseToken = async (): Promise<string | null> => {
  const token = getAuthToken();
  if (!token) return null;

  const response = await fetchWithRetry(`${API_URL}/api/admin/firebase-token`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 5000,
    retries: 1,
  });

  if (!response.ok) return null;
  const data = await response.json();
  return data.firebase_token;
};

export const getAdminData = async (): Promise<CourseData> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/data`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to fetch admin data');
  }
  
  return response.json();
};

export const updateCourseData = async (data: CourseData): Promise<{ success: boolean; message?: string }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/data`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
    timeout: 15000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to update course data');
  }
  
  return response.json();
};

export const addCourse = async (title: string, isVisible: boolean = false): Promise<{ success: boolean; course: Course }> => {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/courses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ title, isVisible }),
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) throw new Error('Failed to add course');
  return response.json();
};

export const updateCourse = async (courseId: string, updates: Partial<Course>): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/courses/${courseId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) throw new Error('Failed to update course');
  return response.json();
};

export const deleteCourse = async (courseId: string): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/courses/${courseId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to delete course');
  }
  
  return response.json();
};

export const addModule = async (module: Omit<CourseModule, 'id'>, courseId?: string): Promise<{ success: boolean; module: CourseModule }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const url = new URL(`${API_URL}/api/admin/modules`);
  if (courseId) url.searchParams.set('courseId', courseId);

  const response = await fetchWithRetry(url.toString(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(module),
    timeout: 15000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to add module');
  }
  
  return response.json();
};

export const updateModule = async (moduleId: string, module: Partial<CourseModule>, courseId?: string): Promise<{ success: boolean; module: CourseModule }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const url = new URL(`${API_URL}/api/admin/modules/${moduleId}`);
  if (courseId) url.searchParams.set('courseId', courseId);

  const response = await fetchWithRetry(url.toString(), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(module),
    timeout: 15000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to update module');
  }
  
  return response.json();
};

export const deleteModule = async (moduleId: string, courseId?: string): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const url = new URL(`${API_URL}/api/admin/modules/${moduleId}`);
  if (courseId) url.searchParams.set('courseId', courseId);

  const response = await fetchWithRetry(url.toString(), {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to delete module');
  }
  
  return response.json();
};

// Student Operations API (Google Sheets)
export interface StudentOperations {
  'Email Address': string;
  Name?: string;
  name?: string;
  'Student Name'?: string;
  'Student Full Name'?: string;
  'Full Name'?: string;
  'First Name'?: string;
  'Last Name'?: string;
  'Resume Link'?: string;
  'Parent Name'?: string;
  Referrer?: string;
  'Payment Status'?: string;
  Attendance?: Record<string, boolean> | string;
  'Assignment 1 Grade'?: string;
  'Assignment 2 Grade'?: string;
  'Teacher Evaluation'?: string;
  [key: string]: any;
}

export interface OperationsMetrics {
  total_students: number;
  paid_count: number;
  unpaid_count: number;
  has_resume_count: number;
  onboarding_percentage: number;
}

export interface OperationsStatus {
  missing_payment: Array<{ email: string; name: string; status: string }>;
  missing_resume: Array<{ email: string; name: string }>;
  missing_attendance: Array<{ email: string; name: string }>;
  missing_grades: Array<{ email: string; name: string; missing: string[] }>;
}

export const getStudentsOperations = async (
  sortBy: 'name' | 'email' | 'payment' | 'timestamp' = 'name',
  sortOrder: 'asc' | 'desc' = 'asc',
  forceRefresh: boolean = false
): Promise<{ success: boolean; students: StudentOperations[] }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const url = new URL(`${API_URL}/api/admin/students/operations`);
  url.searchParams.set('sort_by', sortBy);
  url.searchParams.set('sort_order', sortOrder);
  if (forceRefresh) {
    url.searchParams.set('force_refresh', 'true');
  }
  
  const response = await fetchWithRetry(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 15000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to fetch students operations');
  }
  
  return response.json();
};

export const getStudentsOperationsCombined = async (
  sortBy: 'name' | 'email' | 'payment' | 'timestamp' = 'name',
  sortOrder: 'asc' | 'desc' = 'asc',
  forceRefresh: boolean = false
): Promise<{ 
  success: boolean; 
  students: StudentOperations[]; 
  metrics: OperationsMetrics; 
  status: OperationsStatus 
}> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const url = new URL(`${API_URL}/api/admin/students/operations/all`);
  url.searchParams.set('sort_by', sortBy);
  url.searchParams.set('sort_order', sortOrder);
  if (forceRefresh) {
    url.searchParams.set('force_refresh', 'true');
  }
  
  const response = await fetchWithRetry(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 15000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to fetch students operations');
  }
  
  return response.json();
};

export const getStudentOperations = async (email: string): Promise<{ success: boolean; student: StudentOperations }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/students/operations/${encodeURIComponent(email)}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    if (response.status === 404) {
      throw new Error('Student not found');
    }
    throw new Error('Failed to fetch student operations');
  }
  
  return response.json();
};

export const updateStudentOperations = async (
  email: string,
  updates: Partial<StudentOperations>
): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/students/operations/${encodeURIComponent(email)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
    timeout: 15000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to update student operations');
  }
  
  return response.json();
};

export const bulkUpdateStudentsOperations = async (
  updates: Array<{ email: string } & Partial<StudentOperations>>
): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/students/operations/bulk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ updates }),
    timeout: 20000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to bulk update students operations');
  }
  
  return response.json();
};

export const getOperationsMetrics = async (): Promise<{ success: boolean; metrics: OperationsMetrics }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/students/operations/metrics`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to fetch operations metrics');
  }
  
  return response.json();
};

export const getOperationsStatus = async (): Promise<{ success: boolean; status: OperationsStatus }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/students/operations/status`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to fetch operations status');
  }
  
  return response.json();
};

export const getOperationsEmails = async (): Promise<{ success: boolean; emails: string[]; emails_string: string; count: number }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetchWithRetry(`${API_URL}/api/admin/students/operations/emails`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: 10000,
    retries: 2,
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to fetch operations emails');
  }
  
  return response.json();
};

