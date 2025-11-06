import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { addTodo } from '../store/todosSlice';
import { logout } from '../store/authSlice';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import './Newpage.css';
import {jwtDecode} from 'jwt-decode';

export default function Newpage() {
  const [title, setTitle] = useState('');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { token } = useSelector((state) => state.auth);

  // 实现开屏动画
  useEffect(() => {
    gsap.fromTo(
      '#addTodo-title',
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.6, ease: 'power1.out' }
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
    } else {
      navigate('/login');
    }
  }, [token, dispatch, navigate]);

  // 添加待办
  function handleAddTodo() {
    if (!title.trim()) return;
    dispatch(addTodo({ title })).then((res) => {
      if (addTodo.fulfilled.match(res)) {
        const newId = res.payload.id;
        navigate(`/todo/${newId}`);
      }
    });
    setTitle('');
  }

  // 回车键提交
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleAddTodo();
    }
  };

  return (
    <>
      <div className="addTodo">
        <h2 id="addTodo-title">欢迎回来!今天要干什么?</h2>
        <div id="addTodo-content">
          <input
            autoComplete="off"
            id="addTodo-input"
            type="text"
            value={title}
            placeholder="请输入待办标题"
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div onClick={handleAddTodo} id="addTodo-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </div>
        </div>
      </div>
    </>
  );
}