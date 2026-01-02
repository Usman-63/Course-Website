const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export interface CourseModule {
  id: string;
  title: string;
  hours: number;
  focus: string;
  topics: string[];
  order: number;
}

export interface CourseLink {
  id: string;
  title: string;
  url: string;
  description?: string;
  iconType?: string;
  order: number;
}

export interface CourseMetadata {
  schedule: string;
  capstone?: string;
  certification?: string;
  pricing: {
    [key: string]: number | { name: string; price: number; features?: string[] };
  };
  earlyAccessOffer?: string;
}

export interface CourseData {
  modules: CourseModule[];
  links: CourseLink[];
  metadata: CourseMetadata;
}

// Get auth token from localStorage
const getAuthToken = (): string | null => {
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

// Public API calls
export const getCourseData = async (): Promise<CourseData> => {
  const response = await fetch(`${API_URL}/api/course/data`);
  if (!response.ok) {
    throw new Error('Failed to fetch course data');
  }
  return response.json();
};

// Admin API calls
export const adminLogin = async (password: string): Promise<{ success: boolean; message?: string; error?: string }> => {
  const response = await fetch(`${API_URL}/api/admin/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ password }),
  });
  return response.json();
};

export const getAdminData = async (): Promise<CourseData> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/data`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
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
  
  const response = await fetch(`${API_URL}/api/admin/data`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
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

export const addModule = async (module: Omit<CourseModule, 'id'>): Promise<{ success: boolean; module: CourseModule }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/modules`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(module),
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

export const updateModule = async (moduleId: string, module: Partial<CourseModule>): Promise<{ success: boolean; module: CourseModule }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/modules/${moduleId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(module),
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

export const deleteModule = async (moduleId: string): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/modules/${moduleId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
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

export const addLink = async (link: Omit<CourseLink, 'id'>): Promise<{ success: boolean; link: CourseLink }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/links`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(link),
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to add link');
  }
  
  return response.json();
};

export const updateLink = async (linkId: string, link: Partial<CourseLink>): Promise<{ success: boolean; link: CourseLink }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/links/${linkId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(link),
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to update link');
  }
  
  return response.json();
};

export const deleteLink = async (linkId: string): Promise<{ success: boolean; message: string }> => {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(`${API_URL}/api/admin/links/${linkId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      throw new Error('Authentication failed');
    }
    throw new Error('Failed to delete link');
  }
  
  return response.json();
};


