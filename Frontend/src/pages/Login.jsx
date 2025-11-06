import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { login, logout } from '../store/authSlice';
import { fetchTodos } from '../store/todosSlice';
import gsap from 'gsap';
import api from '../utils/axiosConfig';
import {jwtDecode }from 'jwt-decode'; 

import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { status, error, token } = useSelector((state) => state.auth);

  // 页面挂载动画
  useEffect(() => {
    gsap.fromTo(
      ['#login-page'],
      { opacity: 0 },
      { opacity: 1, duration: 0.2, ease: 'power1.in' }
    );
  }, []);

  // 检查 token 过期
  useEffect(() => {
    if (token) {
      try {
        const decoded = jwtDecode(token);
        const currentTime = Date.now() / 1000; // 秒
        if (decoded.exp < currentTime) {
          dispatch(logout());
          navigate('/login');
        } else {
          const timeout = (decoded.exp - currentTime) * 1000;
          const timer = setTimeout(() => {
            dispatch(logout());
            navigate('/login');
          }, timeout);
          return () => clearTimeout(timer);
        }
      } catch (err) {
        dispatch(logout());
        navigate('/login');
      }
    }
  }, [token, dispatch, navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const result = await dispatch(login({ email, password })).unwrap();

      // 登录成功后立即设置 axios 默认 token
      api.defaults.headers.Authorization = `Bearer ${result.token}`;

      // 拉取当前账号的 todos
      dispatch(fetchTodos());

      // 跳转主页
      navigate('/');
    } catch (err) {
      console.error('登录失败', err);
    }
  };

  return (
    <>
      <div id="web-login-header">
        <svg id="web-login-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="flameGradient" x1="12" y1="2" x2="12" y2="22" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FF9B00" />
              <stop offset="1" stopColor="#FF6D00" />
            </linearGradient>
          </defs>
          <path
            fill="url(#flameGradient)"
            d="M12 2C7 7 6 12 6 16c0 3.31 2.69 6 6 6s6-2.69 6-6c0-4-3-9-6-14z"
          />
        </svg>
        <h1 id="web-login-title">Flare</h1>
      </div>

      <div id="login-page">
        <div id="login-main-div">
          <h2 id="login-h2">登录你的账户</h2>
          <h3 id="login-h3">
            还没有账户? <Link to="/register">注册</Link>
          </h3>

          {/* 邮箱输入 */}
          <label id="login-email-label" htmlFor="login-userEmail">
            <div id="login-email-wrapper">
              <div id="login-email-span">
                <span>邮箱</span>
              </div>
              <div id="login-email-input">
                <input
                  type="email"
                  id="login-userEmail"
                  placeholder="请输入邮箱"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>
          </label>

          {/* 密码输入 */}
          <label id="login-password-label" htmlFor="login-userPassword">
            <div id="login-password-wrapper">
              <div id="login-password-span">
                <span>密码</span>
              </div>
              <div id="login-password-input">
                <input
                  type="password"
                  id="login-userPassword"
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>
          </label>

          {/* 错误信息 */}
          {error && <p style={{ color: 'red', textAlign: 'center' }}>{error}</p>}

          {/* 登录按钮 */}
          <button id="login-btn" onClick={handleLogin} disabled={status === 'loading'}>
            {status === 'loading' ? '登录中...' : '登录'}
          </button>

          {/* 忘记密码 */}
          <div id="login-forgot">
            <Link to="/forgot-password">忘记密码?</Link>
          </div>
        </div>
      </div>
    </>
  );
}
