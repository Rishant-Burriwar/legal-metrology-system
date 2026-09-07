import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("lm_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor for 401 handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("lm_token");
      localStorage.removeItem("lm_user");
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("lm:logout"));
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    return res.data;
  },
  getMe: async () => {
    const res = await api.get("/auth/me");
    return res.data;
  },
};

export const inspectionApi = {
  upload: async (formData, onProgress) => {
    const res = await api.post("/inspections/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return res.data;
  },
  getById: async (id) => {
    const res = await api.get(`/inspections/${id}`);
    return res.data;
  },
  list: async (skip = 0, limit = 20, status = null, inspectorId = null) => {
    const params = { skip, limit };
    if (status) params.status = status;
    if (inspectorId !== null && inspectorId !== undefined && inspectorId !== "all") {
      params.inspector_id = inspectorId;
    }
    const res = await api.get("/inspections", { params });
    return res.data;
  },
  getInspectors: async () => {
    const res = await api.get("/inspections/inspectors");
    return res.data;
  },
  getPdfUrl: (id) => `${API_BASE_URL}/inspections/${id}/report.pdf`,
};

export const dashboardApi = {
  getStats: async (inspectorId = null) => {
    const params = {};
    if (inspectorId !== null && inspectorId !== undefined && inspectorId !== "all") {
      params.inspector_id = inspectorId;
    }
    const res = await api.get("/dashboard/stats", { params });
    return res.data;
  },
};

export default api;
