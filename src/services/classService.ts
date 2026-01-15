import { fetchWithRetry } from '../utils/fetchWithRetry';
import { API_URL, getAuthToken } from './api';

const request = async (endpoint: string, options: RequestInit = {}) => {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetchWithRetry(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || 'API request failed');
  }

  return response.json();
};

const api = {
  get: (url: string) => request(url, { method: 'GET' }),
  post: (url: string, data: any) => request(url, { method: 'POST', body: JSON.stringify(data) }),
  put: (url: string, data: any) => request(url, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (url: string) => request(url, { method: 'DELETE' }),
};

export interface ClassSession {
  id: string;
  date: string;
  topic: string;
  description?: string;
}

export const classService = {
  getAll: async () => {
    const res = await api.get('/api/admin/classes');
    return res.classes as ClassSession[];
  },
  
  add: async (data: Omit<ClassSession, 'id'>) => {
    const res = await api.post('/api/admin/classes', data);
    return res.class as ClassSession;
  },
  
  delete: async (id: string) => {
    await api.delete(`/api/admin/classes/${id}`);
  },
  
  markAttendance: async (id: string, presentEmails: string[]) => {
    await api.post(`/api/admin/classes/${id}/attendance`, { present_emails: presentEmails });
  }
};
