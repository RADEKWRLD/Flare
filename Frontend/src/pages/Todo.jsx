import { useState, useEffect, useRef, use } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useParams } from "react-router-dom";
import gsap from "gsap";
import axios from "axios";
import "./Todo.css";
import { fetchTodos } from "../store/todosSlice";
//textarea自动换行
import TextareaAutosize from "react-textarea-autosize";

//markdown语法支持
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

//高亮
import CodeMirror from "@uiw/react-codemirror";
import { markdown } from "@codemirror/lang-markdown";


export default function Todo() {
    const { id } = useParams(); // 从路由获取 todo id
    const todosFromRedux = useSelector((state) => state.todos.items ?? []);
    const [todos, setTodos] = useState(() => {
        const cached = localStorage.getItem("todos");
        return cached ? JSON.parse(cached) : [];
    });
    const dispatch = useDispatch();

    const [contents, setContents] = useState([]); // todo 内容数组
    const [imageUrls, setImageUrls] = useState({}); // 下载图片的 blob URL
    const [sessionTalk, setSessionTalk] = useState(""); // 输入框内容
    const SESSION_KEY = `todo-session-talk-${id}`;
    const SESSION_KEYS_LIST = "session-talk-keys";
    const MAX_SESSIONS = 10;

    //文件变量
    const [images, setImages] = useState([]); // 待上传图片
    const [files, setFiles] = useState([]); // 待上传文件
    const fileInputRef = useRef();
    
    //提交状态
    const [isSubmitting, setIsSubmitting] = useState(false);

    //开屏动画
    useEffect(() => {
        gsap.fromTo(
            "#todoPage-div",
            { opacity: 0 },
            { opacity: 1, duration: 0.3, ease: "power2.inOut" }
        );
    }, []);

    //同步 Redux todos
    useEffect(() => {
        if (todosFromRedux.length > 0) {
            setTodos(todosFromRedux);
            localStorage.setItem("todos", JSON.stringify(todosFromRedux));
        } else {
            dispatch(fetchTodos());
        }
    }, [todosFromRedux, dispatch]);

    const todo = todos.find((item) => item.id === id);

    //获取 todo 内容,SSE形式
    useEffect(() => {
        const savedTalk = localStorage.getItem(SESSION_KEY) || "";
        setSessionTalk(savedTalk);

        const token = localStorage.getItem("token");//添加token，sse不支持表头传递token
        const es = new EventSource(`http://localhost:5000/api/todos/content/${id}?token=${token}`);

        //缓存命中
        es.addEventListener("cache", (e) => {
            try {
                const cacheInfo = JSON.parse(e.data);
            } catch (err) {
                console.error("解析 cache 数据失败:", err);
            }
        });

        //监听data
        es.addEventListener("data", async (e) => {
            try {
                const data = JSON.parse(e.data);
                setContents(prev => {
                    // 检查是否已存在相同的内容（避免重复添加）
                    const exists = prev.some(item => item._id === data._id);
                    if (exists) {
                        return prev;
                    }
                    return [...prev, data];
                });

                // 下载图片生成 blob URL
                if (data.images?.length > 0) {
                    data.images.forEach(async (img) => {
                        const filename = img.split('/').pop()

                        // 检查是否已经有这个图片的URL
                        setImageUrls(prev => {
                            if (prev[filename]) return prev;
                            return { ...prev };
                        });

                        try {
                            const r = await axios.get(
                                `http://localhost:5000/api/todos/content/image/${decodeURIComponent(filename)}`,
                                {
                                    headers: { Authorization: `Bearer ${token}` },
                                    responseType: "blob",
                                }
                            );
                            const blobUrl = URL.createObjectURL(r.data);

                            setImageUrls(prev => ({ ...prev, [filename]: blobUrl }));
                        } catch (err) {
                            console.error("下载图片失败:", filename, err);
                        }
                    });
                }
            } catch (err) {
                console.error("解析 SSE 数据失败:", err);
            }
        });

        es.addEventListener("end", () => es.close());
        es.onerror = (err) => {
            console.error("SSE 错误:", err);
            es.close();
        };

        return () => {
            es.close();
            // 卸载或切换路由时释放 blob
            setContents([]);
            Object.values(imageUrls).forEach(url => URL.revokeObjectURL(url));
            setImageUrls({});
        };
    }, [id])

    //输入框变化
    function handleTextAreaChange(e) {
        const value = e.target.value;
        setSessionTalk(value);
        localStorage.setItem(SESSION_KEY, value);

        // 管理最近 10 条 session
        const sessionKeys = JSON.parse(localStorage.getItem(SESSION_KEYS_LIST)) || [];
        if (!sessionKeys.includes(SESSION_KEY)) {
            sessionKeys.push(SESSION_KEY);
            while (sessionKeys.length > MAX_SESSIONS) {
                const oldestKey = sessionKeys.shift();
                localStorage.removeItem(oldestKey);
            }
            localStorage.setItem(SESSION_KEYS_LIST, JSON.stringify(sessionKeys));
        }
    }

    //文件上传
    function handleUploadClick() {
        fileInputRef.current.click();
    }

    function handleFilesChange(e) {
        const selectedFiles = Array.from(e.target.files);
        const newImages = selectedFiles.filter(f => f.type.startsWith("image/"));
        const newFiles = selectedFiles.filter(f => !f.type.startsWith("image/"));
        setImages(prev => [...prev, ...newImages]);
        setFiles(prev => [...prev, ...newFiles]);
        e.target.value = null;
    }

    function removeImage(index) {
        setImages(prev => prev.filter((_, i) => i !== index));
    }

    function removeFile(index) {
        setFiles(prev => prev.filter((_, i) => i !== index));
    }

    //带 token 安全下载文件
    async function downloadFile(fileUrl) {
        const filename = fileUrl.split("/").pop();
        try {
            const res = await axios.get(fileUrl, {
                headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
                responseType: "blob",
            });
            const blob = new Blob([res.data]);
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.click();
            URL.revokeObjectURL(link.href);
        } catch (err) {
            console.error("下载文件失败:", filename, err);
        }
    }

    //提交事件
    async function handleSubmit() {
        //必须输入文字
        if (!sessionTalk.trim() || isSubmitting) return;
        
        setIsSubmitting(true); // 禁用按钮
        
        const formData = new FormData();
        formData.append("content", sessionTalk);
        images.forEach(img => formData.append("images", img));
        files.forEach(f => formData.append("files", f));

        try {
            const res = await axios.post(`http://localhost:5000/api/todos/content/${id}`, formData, {
                headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
            });

            // 立即更新本地状态，确保UI实时响应
            const newContent = res.data.data;
            setContents(prev => {
                // 检查是否已存在相同的内容（避免重复添加）
                const exists = prev.some(item => item._id === newContent._id);
                if (exists) {
                    return prev;
                }
                return [newContent, ...prev]; // 添加到前面
            });
            
            setSessionTalk("");
            setImages([]);
            setFiles([]);
            localStorage.removeItem(SESSION_KEY);

            // 下载新上传的图片生成 blob URL
            if (newContent.images?.length > 0) {
                const token = localStorage.getItem("token");
                for (const img of newContent.images) {
                    const filename = img.split("/").pop();
                    try {
                        const r = await axios.get(`http://localhost:5000/api/todos/content/image/${decodeURIComponent(filename)}`, {
                            headers: { Authorization: `Bearer ${token}` },
                            responseType: "blob",
                        });
                        const blobUrl = URL.createObjectURL(r.data);
                        setImageUrls(prev => ({ ...prev, [filename]: blobUrl }));
                    } catch (err) {
                        console.error("下载新图片失败:", filename, err);
                    }
                }
            }
        } catch (err) {
            console.error("提交失败:", err);
        } finally {
            setIsSubmitting(false); // 启用按钮
        }
    }

    //处理上传事件
    function handleKeyDown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        };
    }

    //处理编辑菜单编辑事件

    //控制开关布尔值
    const [settingsOpen, setSettingsOpen] = useState(false)
    //传入菜单位置
    const [menuPos, setMenuPos] = useState({ top: '0', left: '0' })
    //当前点击的编辑按钮
    const [activeContentId, setActiveContentId] = useState(null)
    //菜单DOM
    const menuRef = useRef(null)

    //点击动画
    useEffect(() => {
        if (settingsOpen && menuRef.current) {
            gsap.fromTo(
                menuRef.current,
                { opacity: 0, y: 10 },
                { opacity: 1, y: 0, duration: 0.2, ease: 'power2.out' }
            );
        }
    }, [settingsOpen])

    //点击外面关闭
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (settingsOpen && menuRef.current && !menuRef.current.contains(e.target)) {
                setSettingsOpen(false);
            }
        };
        window.addEventListener("click", handleClickOutside);
        return () => window.removeEventListener("click", handleClickOutside);
    }, [settingsOpen]);


    //删除内容事件
    async function handleContentDelete(contentId) {
        try {
            await axios.delete(
                `http://localhost:5000/api/todos/content/${contentId}`,
                { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } }
            )
            setContents((prev) => prev.filter((c) => c._id !== contentId));
        } catch (err) {
            console.error("删除失败:", err);
        }
    }


    //编辑内容事件,获取常量
    const [editingContentId, setEditingContentId] = useState(null)
    const [editingText, setEditingText] = useState('')

    //编辑内容事件
    async function handleContentEdit(contentId) {
        try {
            const res = await axios.put(
                `http://localhost:5000/api/todos/content/${contentId}`,
                { content: editingText },
                { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } }
            )

            setContents((prev) =>
                prev.map((c) => (c._id === contentId ? { ...c, content: editingText } : c))
            );
            setEditingContentId(null);
            setEditingText("")
        } catch (err) {
            console.error("编辑失败", err)
        }
    }

    //失焦后自动保存
    const editInputRef = useRef(null)
    useEffect(() => {
        function handleClickOutside(e) {
            if (editingContentId && editInputRef.current && !editInputRef.current.contains(e.target)) {
                // 自动保存
                handleContentEdit(editingContentId);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [editingContentId, editingText])


    return (
        <div id="todoPage-div">
            {todo ? (
                <>
                    <div id="todo-title-div">
                        <h2 id="todo-title-h2">{todo.title}</h2>
                    </div>

                    <div className="todo-content">
                        {/**todo内容渲染 */}
                        {contents.map(c => (
                            <div key={c._id} className="todo-content-item">
                                <div
                                    className="todo-content-settings-button"
                                    role="button"

                                    //模态框展示
                                    onClick={(e) => {
                                        //阻止父元素冒泡
                                        e.stopPropagation()
                                        setActiveContentId(c._id)
                                        //获取当前可视区的坐标
                                        setMenuPos({ top: e.clientY, left: e.clientX })
                                        setSettingsOpen(true)
                                    }}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
                                    </svg>

                                    {/**菜单DOM，只渲染当前点击content */}
                                    {settingsOpen && activeContentId === c._id && (
                                        <div id="content-settings-menu"
                                            ref={menuRef}
                                            onClick={(e) => { e.stopPropagation() }}
                                        >
                                            <div
                                                id="content-settings-rename-div"
                                                role="button"
                                            >
                                                <svg
                                                    id="content-settings-rename-icon"
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
                                                <span id="todo-settings-rename-span" onClick={() => {
                                                    //获取正在编辑的id
                                                    setEditingContentId(c._id)
                                                    //获取正在编辑的内容
                                                    setEditingText(c.content)
                                                    //关闭菜单
                                                    setSettingsOpen(false)
                                                }}>编辑</span>
                                            </div>
                                            <div
                                                id="content-settings-delete-div"
                                                role="button"
                                            >
                                                <svg
                                                    id="content-settings-delete-icon"
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
                                                <span id="todo-settings-delete-span" onClick={() => handleContentDelete(c._id)}>删除</span>
                                            </div>

                                        </div>
                                    )}


                                </div>

                                {/*markdown语法支持，条件渲染*/}
                                <div className="todo-content-text-div">
                                    {editingContentId === c._id ? (
                                        <div className="todo-content-wrapper">
                                            <CodeMirror
                                                className="todo-content-textarea"
                                                value={editingText}
                                                height="auto"
                                                minHeight="80px"
                                                basicSetup={{
                                                    lineNumbers: false,
                                                    highlightActiveLine: false,
                                                }}
                                                extensions={[markdown()]}
                                                autoFocus
                                                onChange={(value) => setEditingText(value)}
                                            />
                                            {/* 确认 & 取消按钮 */}
                                            <div className="edit-buttons">
                                                <button
                                                    className="edit-confirm"
                                                    onClick={() => handleContentEdit(c._id)}
                                                >
                                                    确认
                                                </button>
                                                <button
                                                    className="edit-cancel"
                                                    onClick={() => {
                                                        setEditingContentId(null);
                                                        setEditingText("");
                                                    }}
                                                >
                                                    取消
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                code({ inline, className, children, ...props }) {
                                                    const match = /language-(\w+)/.exec(className || "");
                                                    return !inline && match ? (
                                                        <SyntaxHighlighter
                                                            style={oneDark}
                                                            language={match[1]}
                                                            PreTag="div"
                                                            {...props}
                                                        >
                                                            {String(children).replace(/\n$/, "")}
                                                        </SyntaxHighlighter>
                                                    ) : (
                                                        <code className={className} {...props}>
                                                            {children}
                                                        </code>
                                                    );
                                                },
                                            }}
                                        >
                                            {c.content}
                                        </ReactMarkdown>
                                    )}


                                </div>

                                <div className="todo-content-wrapper-main-div">
                                    {/* 图片展示 */}
                                    {c.images?.map((img, idx) => {
                                        const filename = img.split("/").pop();
                                        return imageUrls[filename] ? (
                                            <div className="todo-content-img-div" key={idx}>
                                                <img
                                                    key={idx}
                                                    src={imageUrls[filename]}
                                                    alt={decodeURIComponent(filename)}
                                                    className="todo-img"
                                                />
                                            </div>
                                        ) : null;
                                    })}
                                </div>

                                <div className="todo-content-wrapper-main-div">
                                    {/* 文件展示为卡片 */}
                                    {c.files?.map((f, idx) => {
                                        const decodedName = decodeURIComponent(f.split("/").pop());//展示用
                                        const displayName = decodedName.includes("_")
                                            ? decodedName.split("_").slice(1).join("_")
                                            : decodedName;

                                        const filenameWithUUID = f.split("/").pop(); // 后端文件名
                                        // const encodedFilename = encodeURIComponent(filenameWithUUID);//下载用
                                        return (
                                            //组件复用，外层只需要再套个容器
                                            <div key={idx} className="preview-item file-card">
                                                <div className="file-icon-div">
                                                    <svg
                                                        className="file-icon"
                                                        xmlns="http://www.w3.org/2000/svg"
                                                        fill="none"
                                                        viewBox="0 0 24 24"
                                                        strokeWidth={1.5}
                                                        stroke="currentColor"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                                                        />
                                                    </svg>
                                                </div>
                                                <div className="file-info">
                                                    <div className="file-name">{displayName}</div>
                                                </div>
                                                <button className="file-button"
                                                    onClick={() => downloadFile(`http://localhost:5000/api/todos/content/file/${filenameWithUUID}`)}
                                                >
                                                    <svg className="file-icon-download" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                                                    </svg>

                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>


                    <div id="todo-input-content">
                        {/**当有内容时撑开元素 */}
                        <div className="preview-wrapper" style={{
                            paddingTop: images.length > 0 || files.length > 0 ? "1rem" : "0"
                        }}>
                            {images.map((img, idx) => (
                                <div key={idx} className="preview-item">
                                    <img src={URL.createObjectURL(img)} alt="preview" />
                                    <button onClick={() => removeImage(idx)}>X</button>
                                </div>
                            ))}
                            {files.map((file, idx) => (
                                <div key={idx} className="preview-item file-card">
                                    <div className="file-icon-div">
                                        <svg className="file-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" >
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                                        </svg>
                                    </div>
                                    <div className="file-info">
                                        <div className="file-name">{file.name}</div>
                                        <div className="file-size">
                                            {(file.size / 1024).toFixed(1)} KB
                                        </div>
                                    </div>
                                    <button onClick={() => removeFile(idx)}>X</button>
                                </div>
                            ))}
                        </div>

                        <div id="todo-input-wrapper">
                            <div id="todo-input-upload-icon-div" onClick={handleUploadClick}>
                                <svg
                                    id="todo-input-upload-icon"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth={1.5}
                                    stroke="currentColor"
                                    className="size-6"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                                </svg>
                            </div>

                            <input
                                type="file"
                                ref={fileInputRef}
                                multiple
                                style={{ display: "none" }}
                                onChange={handleFilesChange}
                            />


                            {/**丝滑的交互体验 */}
                            <TextareaAutosize
                                value={sessionTalk}
                                onChange={handleTextAreaChange}
                                onKeyDown={handleKeyDown}
                                placeholder="请输入详细文档..."
                                name="todo-input"
                                id="todo-input-textarea"
                                minRows={1}   // 最小行数
                                maxRows={8}  // 最大行数
                            />

                            <div 
                                onClick={handleSubmit} 
                                id="todo-input-submit-icon-div"
                                className={isSubmitting ? 'disabled' : ''}
                                style={{
                                    opacity: isSubmitting ? 0.5 : 1,
                                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                                    pointerEvents: isSubmitting ? 'none' : 'auto'
                                }}
                            >
                                <svg
                                    id="todo-input-submit-icon"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth={1.5}
                                    stroke="currentColor"
                                    className="size-6"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
                                </svg>
                            </div>
                        </div>
                    </div>

                </>
            ) : (
                <p>Todo not found</p>
            )}
        </div>
    );
}
