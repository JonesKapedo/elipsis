import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const apiAuth = axios.create({ baseURL: '/api' });

export const apiAuthInstance = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

export const apiV1 = {
  health: () => api.get('/v1/health'),
  login: (email: string, password: string) => api.post('/v1/auth/login', { email, password }),
  me: () => api.get('/v1/auth/me'),
  assessments: () => api.get('/v1/assessments'),
  createAssessment: (data: any) => api.post('/v1/assessments', data),
  getAssessment: (id: string) => api.get(`/v1/assessments/${id}`),
  results: (id: string) => api.get(`/v1/assessments/${id}/results`),
  report: (id: string) => api.get(`/v1/assessments/${id}/report`),
  logout: () => api.post('/v1/auth/logout'),
};

export default api;
