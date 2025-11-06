import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { register, logout } from '../store/authSlice';
import gsap from 'gsap';
import './Register.css';
import {jwtDecode} from 'jwt-decode';

export default function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { status, error, token } = useSelector((state) => state.auth);

  // 挂载动画
  useEffect(() => {
    gsap.fromTo(
      ['#register-page'],
      { opacity: 0 },
      { opacity: 1, duration: 0.2, ease: 'power1.in' }
    );
  }, []);

  // 检查 token 过期
  useEffect(() => {
    if (token) {
      try {
        const decoded = jwtDecode(token);
        const currentTime = Date.now() / 1000;
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
      } catch (error) {
        dispatch(logout());
        navigate('/login');
      }
    }
  }, [token, dispatch, navigate]);

  const handleRegister = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      dispatch({
        type: 'auth/register/rejected',
        payload: 'Passwords do not match',
      });
      return;
    }
    const result = await dispatch(register({ username, email, password }));
    if (register.fulfilled.match(result)) {
      navigate('/login');
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

      <div id="register-page">
        <div id="register-main-div">
          <h2 id="register-h2">创建你的账户</h2>
          <h3 id="register-h3">
            已有账户? <Link to="/login">登录</Link>
          </h3>

          <label id="register-username-label" htmlFor="register-userName">
            <div id="register-username-wrapper">
              <div id="register-username-span">
                <span>用户名</span>
              </div>
              <div id="register-username-input">
                <input
                  type="text"
                  id="register-userName"
                  placeholder="请输入用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
            </div>
          </label>

          <label id="register-email-label" htmlFor="register-userEmail">
            <div id="register-email-wrapper">
              <div id="register-email-span">
                <span>邮箱</span>
              </div>
              <div id="register-email-input">
                <input
                  type="email"
                  id="register-userEmail"
                  placeholder="请输入邮箱"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>
          </label>

          <label id="register-password-label" htmlFor="register-userPassword">
            <div id="register-password-wrapper">
              <div id="register-password-span">
                <span>密码</span>
              </div>
              <div id="register-password-input">
                <input
                  type="password"
                  id="register-userPassword"
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>
          </label>

          <label id="register-confirm-password-label" htmlFor="register-confirmPassword">
            <div id="register-confirm-password-wrapper">
              <div id="register-confirm-password-span">
                <span>确认密码</span>
              </div>
              <div id="register-confirm-password-input">
                <input
                  type="password"
                  id="register-confirmPassword"
                  placeholder="请再次输入密码"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </div>
          </label>

          {error && <p style={{ color: 'red', textAlign: 'center' }}>{error}</p>}

          <button id="register-btn" onClick={handleRegister} disabled={status === 'loading'}>
            {status === 'loading' ? '注册中...' : '注册'}
          </button>
        </div>
      </div>
    </>
  );
}