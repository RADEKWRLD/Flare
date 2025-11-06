import { useDispatch, useSelector } from 'react-redux';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { fetchTodos, updateTodo, deleteTodo } from '../store/todosSlice';
import { logout } from '../store/authSlice';
import gsap from 'gsap';
import './Navbar.css';

export default function Navbar() {
    const dispatch = useDispatch();
    const navigate = useNavigate();
    //获取id参数
    const { id } = useParams();
    //创建todo对象
    const todos = useSelector((state) => state.todos.items ?? []);
    const status = useSelector((state) => state.todos.status);
    const user = useSelector((state) => state.auth.user);
    const token = useSelector((state) => state.auth.token);

    //设置事件的数据
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [activeTodoId, setActiveTodoId] = useState(null);
    const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
    const [editingTodoId, setEditingTodoId] = useState(null);
    const [editTitle, setEditTitle] = useState('');
    const [showDelete, setShowDelete] = useState(false);
    const menuRef = useRef(null);
    const modalRef = useRef(null);
    const inputRef = useRef(null);

    //挂载时获取列表
    useEffect(() => {
        if (status === 'idle' && token) {
            dispatch(fetchTodos());
        }
    }, [status, dispatch, token]);

    //启动动画
    useEffect(() => {
        if (settingsOpen && menuRef.current) {
            gsap.fromTo(
                menuRef.current,
                { opacity: 0, y: 10 },
                { opacity: 1, y: 0, duration: 0.2, ease: 'power2.out' }
            );
        }
    }, [settingsOpen]);

    //路由变换标题
    useEffect(() => {
        if (location.pathname === '/login') {
            document.title = 'Flare - 登录';
        } else if (location.pathname === '/register') {
            document.title = 'Flare - 注册';
        } else if (location.pathname === '/') {
            document.title = 'Flare待办';
        } else if (id) {
            // 找到对应 todo
            const todo = todos.find((item) => item.id === id);
            if (todo) {
                document.title = todo.title;
            } else {
                document.title = 'FlareRAG';
            }
        } else {
            document.title = 'Flare';
        }
    }, [id, todos, location.pathname]);


    //删除模态框动画
    useEffect(() => {
        if (showDelete && modalRef.current) {
            gsap.fromTo(
                modalRef.current,
                { opacity: 0, scale: 0.8 },
                { opacity: 1, scale: 1, duration: 0.2, ease: 'power2.out' }
            );
        }
    }, [showDelete]);

    //处理外部点击时间
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setSettingsOpen(false);
                setActiveTodoId(null);
            }
            if (modalRef.current && !modalRef.current.contains(e.target)) {
                setShowDelete(false);
            }
        };

        if (settingsOpen || showDelete) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [settingsOpen, showDelete]);

    //聚焦
    useEffect(() => {
        if (editingTodoId && inputRef.current) {
            inputRef.current.focus();
        }
    }, [editingTodoId]);

    //切换设置
    const toggleSettings = (e, todoId) => {
        e.preventDefault();
        e.stopPropagation();
        if (settingsOpen && activeTodoId === todoId) {
            setSettingsOpen(false);
            setActiveTodoId(null);
        } else {
            const rect = e.currentTarget.getBoundingClientRect();
            setMenuPos({
                top: rect.bottom + window.scrollY + 5,
                left: Math.max(0, rect.left + window.scrollX - 50),
            });
            setSettingsOpen(true);
            setActiveTodoId(todoId);
        }
    };

    //处理重命名
    const handleRename = (todoId) => {
        const todo = todos.find((todo) => todo.id === todoId);
        if (todo) {
            setEditingTodoId(todoId);
            setEditTitle(todo.title);
            setSettingsOpen(false);
            setActiveTodoId(null);
        }
    };

    //重命名提交
    const handleRenameSubmit = (todoId) => {
        if (editTitle.trim()) {
            dispatch(updateTodo({ id: todoId, updates: { title: editTitle } })).then(
                () => {
                    setEditingTodoId(null);
                    setEditTitle('');
                }
            );
        }
    };

    //取消重命名
    const handleRenameCancel = () => {
        setEditingTodoId(null);
        setEditTitle('');
    };

    //处理删除事件
    const handleDeleteClick = () => {
        setShowDelete(true);
        setSettingsOpen(false);
    };

    const handleDeleteConfirm = () => {
        if (activeTodoId) {
            dispatch(deleteTodo(activeTodoId));
            setShowDelete(false);
            setActiveTodoId(null);
            if (id === activeTodoId) {
                navigate('/');
            }
        }
    };

    //处理账号菜单点击事件
    const [accountMenuOpen, setAccountMenuOpen] = useState(false);
    const [accountMenuPos, setAccountMenuPos] = useState({ top: 0, left: 0 });
    const accountMenuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setSettingsOpen(false);
                setActiveTodoId(null);
            }
            if (modalRef.current && !modalRef.current.contains(e.target)) {
                setShowDelete(false);
            }
            if (accountMenuRef.current && !accountMenuRef.current.contains(e.target)) {
                setAccountMenuOpen(false);
            }
        };

        if (settingsOpen || showDelete || accountMenuOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [settingsOpen, showDelete, accountMenuOpen]);

    useEffect(() => {
        if (accountMenuOpen && accountMenuRef.current) {
            gsap.fromTo(
                accountMenuRef.current,
                { opacity: 0, y: 10 },
                { opacity: 1, y: 0, duration: 0.2, ease: 'power2.out' }
            );
        }
    }, [accountMenuOpen]);

    //点击事件
    const toggleAccountMenu = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (accountMenuOpen) {
            setAccountMenuOpen(false);
        } else {
            const rect = e.currentTarget.getBoundingClientRect();
            setAccountMenuPos({
                top: rect.bottom + window.scrollY - 100,
                left: Math.max(0, rect.left + window.scrollX),
            });
            setAccountMenuOpen(true);
        }
    };

    //登出事件
    const handleLogout = () => {
        dispatch(logout());
        navigate('/login');
    };



    return (
        <nav>
            <div id="web-content">
                <svg id="web-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
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
                <h1 id="web-title">Flare</h1>
            </div>

            <aside className="function-bar">
                <Link className="new-todo" to="/">新文档</Link>
                <Link className="search-todo" to='/search'>搜索文档</Link>
            </aside>

            <aside className="todos-list">
                {todos.map((todo, index) => (
                    <Link
                        className={`todo-item ${id === todo.id ? 'active' : ''}`}
                        key={`${todo.id}-${index}`}
                        to={`/todo/${todo.id}`}
                    >
                        {editingTodoId === todo.id ? (
                            <input
                                ref={inputRef}
                                className="todo-title-input"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onBlur={() => handleRenameSubmit(todo.id)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') handleRenameSubmit(todo.id);
                                    if (e.key === 'Escape') handleRenameCancel();
                                }}
                            />
                        ) : (
                            <span className="todo-title">{todo.title}</span>
                        )}
                        <div
                            onClick={(e) => toggleSettings(e, todo.id)}
                            className="todo-settings-button"
                            role="button"
                            aria-label={`Settings for ${todo.title}`}
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth="1.5"
                                stroke="currentColor"
                                className="size-6"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
                                />
                            </svg>
                        </div>
                    </Link>
                ))}

                {settingsOpen && activeTodoId && (
                    <div
                        id="todo-settings-menu"
                        ref={menuRef}
                        style={{ top: menuPos.top, left: menuPos.left }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div
                            id="todo-settings-rename-div"
                            onClick={() => handleRename(activeTodoId)}
                            role="button"
                            aria-label="Rename todo"
                        >
                            <svg
                                id="todo-settings-rename-icon"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={1.5}
                                stroke="currentColor"
                                className="size-6"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                                />
                            </svg>
                            <span id="todo-settings-rename-span">重命名</span>
                        </div>
                        <div
                            id="todo-settings-delete-div"
                            onClick={handleDeleteClick}
                            role="button"
                            aria-label="Delete todo"
                        >
                            <svg
                                id="todo-settings-delete-icon"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={1.5}
                                stroke="currentColor"
                                className="size-6"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                                />
                            </svg>
                            <span id="todo-settings-delete-span">删除</span>
                        </div>
                    </div>
                )}

                {showDelete && activeTodoId && (
                    <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="delete-modal-content" ref={modalRef}>
                            <h3>确认删除</h3>
                            <p>是否确定删除此待办事项？</p>
                            <div className="delete-modal-buttons">
                                <button
                                    className="delete-modal-confirm"
                                    onClick={handleDeleteConfirm}
                                >
                                    确认
                                </button>
                                <button
                                    className="delete-modal-cancel"
                                    onClick={() => setShowDelete(false)}
                                >
                                    取消
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </aside>

            <aside className='account'>
                <div id="account-div">
                    <div
                        id="account-icon"
                        onClick={toggleAccountMenu}
                        role="button"
                        aria-label="Account menu"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth={1.5}
                            stroke="currentColor"
                            className="size-6"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                            />
                        </svg>
                    </div>
                    <div id="account-information">
                        {token && user ? (
                            <>
                                <div id="account-name">
                                    <span>{user.username}</span>
                                </div>
                                <div id="account-email">
                                    <span>{user.email}</span>
                                </div>
                            </>
                        ) : (
                            <>
                                <div id="account-name">
                                    <span>游客</span>
                                </div>
                                <div id="account-email">
                                    <span>
                                        你还没<Link to="/login">登录</Link>!
                                    </span>
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {accountMenuOpen && token && user && (
                    <div
                        id="account-menu"
                        ref={accountMenuRef}
                        style={{ top: accountMenuPos.top, left: accountMenuPos.left }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div
                            id="account-menu-logout"
                            onClick={handleLogout}
                            role="button"
                            aria-label="Logout"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={1.5}
                                stroke="currentColor"
                                className="size-6"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M7.5 7.5h-.75A2.25 2.25 0 0 0 4.5 9.75v7.5a2.25 2.25 0 0 0 2.25 2.25h7.5a2.25 2.25 0 0 0 2.25-2.25v-7.5a2.25 2.25 0 0 0-2.25-2.25h-.75m0-3-3-3m0 0-3 3m3-3v11.25m6-2.25h.75a2.25 2.25 0 0 1 2.25 2.25v7.5a2.25 2.25 0 0 1-2.25 2.25h-7.5a2.25 2.25 0 0 1-2.25-2.25v-.75"
                                />
                            </svg>
                            <span>登出</span>
                        </div>
                    </div>
                )}
            </aside>
        </nav>
    );
}