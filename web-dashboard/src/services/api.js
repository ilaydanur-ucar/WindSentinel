const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseUrl = API_URL;
  }

  getToken() {
    return localStorage.getItem('token');
  }

  setToken(token) {
    localStorage.setItem('token', token);
  }

  clearToken() {
    localStorage.removeItem('token');
  }

  async request(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    const token = this.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: { ...headers, ...options.headers },
    });

    if (res.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Oturum suresi doldu');
    }

    const data = await res.json();
    if (!data.success && res.status >= 400) {
      throw new Error(data.message || 'Bir hata olustu');
    }
    return data;
  }

  // Auth
  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.data.token);
    return data.data;
  }

  async register(email, password, name) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    this.setToken(data.data.token);
    return data.data;
  }

  // Turbines
  getTurbines() {
    return this.request('/api/turbines');
  }

  getTurbine(turbineId) {
    return this.request(`/api/turbines/${turbineId}`);
  }

  // Alerts
  getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/alerts${query ? '?' + query : ''}`);
  }

  getAlertStats() {
    return this.request('/api/alerts/stats');
  }

  resolveAlert(id) {
    return this.request(`/api/alerts/${id}/resolve`, { method: 'PATCH' });
  }
}

export const api = new ApiService();
