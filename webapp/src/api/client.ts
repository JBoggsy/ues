/**
 * API client configuration and base Axios instance.
 * 
 * The client dynamically reads settings from the Zustand store
 * to support runtime configuration of API URL and timeout.
 */
import axios from 'axios';
import { useSettingsStore } from '@/lib/store';

// Get initial values from store (persisted in localStorage)
const getSettings = () => useSettingsStore.getState();

const initialSettings = getSettings();

export const apiClient = axios.create({
  baseURL: initialSettings.apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: initialSettings.connectionTimeout,
});

// Request interceptor to dynamically use current settings
apiClient.interceptors.request.use(
  (config) => {
    const settings = getSettings();
    // Update baseURL and timeout from current settings
    config.baseURL = settings.apiUrl;
    config.timeout = settings.connectionTimeout;
    // Attach API key if configured
    if (settings.apiKey) {
      config.headers['X-API-Key'] = settings.apiKey;
    }
    console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
