import axios from 'axios';
import { logout } from '../store/authSlice';
import { clearTodos } from '../store/todosSlice';

// 根据环境变量设置 baseURL
// 生产环境使用 /api，开发环境使用 http://localhost:5000/api
const api = axios.create({
  baseURL: 'http://localhost:5000/api'
});

let store;

export const setStore = (reduxStore) => {
  store = reduxStore;
  // 初始化时如果有 token，直接设置到 axios
  const token = reduxStore.getState().auth.token || localStorage.getItem('token');
  if (token) {
    api.defaults.headers.Authorization = `Bearer ${token}`;
  }
};

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    let token = null;

    if (store) {
      token = store.getState().auth.token;
    }

    if (!token) {
      token = localStorage.getItem('token');
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (store) {
        store.dispatch(logout());
        store.dispatch(clearTodos());
      }
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
