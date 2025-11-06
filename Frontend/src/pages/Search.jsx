import React, { useState, useRef, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import './Search.css';

export default function Search() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionId] = useState(() => {
    // 生成唯一的会话ID或使用已有的
    const existingId = sessionStorage.getItem('currentSearchSessionId');
    if (existingId) return existingId;
    const newId = `search_${Date.now()}`;
    sessionStorage.setItem('currentSearchSessionId', newId);
    return newId;
  });
  const [sessionStage, setSessionStage] = useState(() => {
    return parseInt(sessionStorage.getItem(`sessionStage_${sessionId}`) || '0');
  });
  const [lastActive, setLastActive] = useState(Date.now());
  const [isReturningUser, setIsReturningUser] = useState(false);
  const [isPageRefresh, setIsPageRefresh] = useState(() => {
    // 检查是否是页面刷新
    const lastRefreshTime = sessionStorage.getItem(`lastRefreshTime_${sessionId}`);
    if (!lastRefreshTime) {
      // 首次加载，设置刷新时间
      sessionStorage.setItem(`lastRefreshTime_${sessionId}`, Date.now().toString());
      return false;
    }
    // 如果存在lastRefreshTime，说明页面之前被加载过，现在是刷新
    sessionStorage.setItem(`lastRefreshTime_${sessionId}`, Date.now().toString());
    return true;
  });
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);
  
  // 从sessionStorage加载对话历史
  useEffect(() => {
    const savedMessages = sessionStorage.getItem(`messages_${sessionId}`);
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages);
        // 为旧消息添加默认的完成状态
        const messagesWithCompletion = parsedMessages.map(msg => ({
          ...msg,
          isCompleted: msg.isCompleted !== undefined ? msg.isCompleted : (msg.type === 'ai' ? true : undefined)
        }));
        setMessages(messagesWithCompletion);
      } catch (e) {
        console.error('Error parsing saved messages:', e);
      }
    }
    
    // 检查是否是重新进入对话
    const lastActiveTime = parseInt(sessionStorage.getItem(`lastActive_${sessionId}`) || '0');
    const currentTime = Date.now();
    // 如果上次活动时间存在且间隔超过30秒，认为是重新进入
    if (lastActiveTime && (currentTime - lastActiveTime) > 30000) {
      setIsReturningUser(true);
      // 增加会话阶段计数
      const newStage = sessionStage + 1;
      setSessionStage(newStage);
      sessionStorage.setItem(`sessionStage_${sessionId}`, newStage.toString());
      
      // 如果会话阶段超过10个，清理会话
      if (newStage > 10) {
        sessionStorage.removeItem(`messages_${sessionId}`);
        sessionStorage.removeItem(`sessionStage_${sessionId}`);
        sessionStorage.removeItem(`lastActive_${sessionId}`);
        setMessages([]);
        setSessionStage(0);
        setIsReturningUser(false);
      }
    }
    
    // 更新最后活动时间
    setLastActive(currentTime);
    sessionStorage.setItem(`lastActive_${sessionId}`, currentTime.toString());
  }, [sessionId, sessionStage]);

  // 获取用户信息
  const getAuthData = React.useCallback(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    let userId = null;
    if (token) {
      try {
        const decoded = jwtDecode(token);
        userId = decoded.user_id;
        if (!userId && userData) {
          const parsed = JSON.parse(userData);
          userId = parsed.id || parsed.user_id;
        }
      } catch (e) {
        console.error('Error parsing token:', e);
      }
    }
    return { token, userId };
  }, []);

  // 滚动到消息列表底部
  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  useEffect(() => {
    scrollToBottom();
    // 保存对话到sessionStorage
    if (messages.length > 0) {
      sessionStorage.setItem(`messages_${sessionId}`, JSON.stringify(messages));
    }
  }, [messages, sessionId]);

  // 监听页面可见性变化
  useEffect(() => {
    const handleVisibilityChange = () => {
      const currentTime = Date.now();
      
      if (document.visibilityState === 'hidden') {
        // 用户离开页面，记录时间
        sessionStorage.setItem(`lastActive_${sessionId}`, currentTime.toString());
      } else if (document.visibilityState === 'visible') {
        // 用户回到页面，检查是否需要标记为重新进入
        const lastActiveTime = parseInt(sessionStorage.getItem(`lastActive_${sessionId}`) || '0');
        if (lastActiveTime && (currentTime - lastActiveTime) > 30000) {
          setIsReturningUser(true);
          // 增加会话阶段计数
          const newStage = sessionStage + 1;
          setSessionStage(newStage);
          sessionStorage.setItem(`sessionStage_${sessionId}`, newStage.toString());
          
          // 如果会话阶段超过10个，清理会话
          if (newStage > 10) {
            sessionStorage.removeItem(`messages_${sessionId}`);
            sessionStorage.removeItem(`sessionStage_${sessionId}`);
            sessionStorage.removeItem(`lastActive_${sessionId}`);
            setMessages([]);
            setSessionStage(0);
            setIsReturningUser(false);
          }
        }
        
        // 更新最后活动时间
        setLastActive(currentTime);
        sessionStorage.setItem(`lastActive_${sessionId}`, currentTime.toString());
      }
    };
    
    // 添加可见性变化监听器
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [sessionId, sessionStage]);

  // 处理用户重新进入对话或页面刷新时的持续输出
  useEffect(() => {
    const continueChatFromLastMessage = () => {
      // 获取最后一条AI消息
      const lastAiMessage = [...messages].reverse().find(msg => msg.type === 'ai');
      
      // 如果存在最后一条AI消息，且未标记为完成，尝试继续获取
      if (lastAiMessage && !lastAiMessage.isCompleted) {
        const { token, userId } = getAuthData();
        if (!token || !userId) return;
        
        // 获取最后一条用户消息
        const lastUserMessage = [...messages].reverse().find(msg => msg.type === 'user');
        if (!lastUserMessage) return;
        setIsLoading(true);
        
        try {
          const eventSource = new EventSource(
            `http://localhost:5000/search?question=${encodeURIComponent(lastUserMessage.content)}&user_id=${userId}&token=${token}&continue=true`
          );
          eventSourceRef.current = eventSource;
          
          eventSource.onmessage = (event) => {
            if (event.data === '[DONE]') {
              // 标记消息为已完成
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === lastAiMessage.id ? { ...msg, isCompleted: true } : msg
                )
              );
              eventSource.close();
              setIsLoading(false);
              return;
            }
            if (event.data === '[ERROR]') {
              setError('服务器错误，请重试');
              setIsLoading(false);
              eventSource.close();
              return;
            }
            
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === lastAiMessage.id ? { ...msg, content: msg.content + event.data } : msg
              )
            );
          };
          
          eventSource.onerror = () => {
            if (eventSource.readyState !== 2) {
              setError('连接错误，请重试');
              setIsLoading(false);
              eventSource.close();
            }
          };
        } catch (err) {
          console.error('Error:', err);
          setIsLoading(false);
        }
      }
    };

    // 处理用户重新进入对话的情况
    if (isReturningUser && messages.length > 0) {
      continueChatFromLastMessage();
      
      // 重置重新进入状态
      setIsReturningUser(false);
    }
    
    // 处理页面刷新的情况
    if (isPageRefresh && messages.length > 0) {
      continueChatFromLastMessage();
      
      // 重置页面刷新状态
      setIsPageRefresh(false);
    }
  }, [isReturningUser, isPageRefresh, messages, getAuthData]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const { token, userId } = getAuthData();
    if (!token) return setError('请先登录');
    if (!userId) return setError('用户信息缺失，请重新登录');

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: question.trim(),
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion('');
    setIsLoading(true);
    setError('');

    const aiMessage = {
      id: Date.now() + 1,
      type: 'ai',
      content: '',
      timestamp: new Date().toLocaleTimeString(),
      isCompleted: false, // 添加完成标志
    };
    setMessages((prev) => [...prev, aiMessage]);

    try {
      const eventSource = new EventSource(
        `http://localhost:5000/search?question=${encodeURIComponent(question)}&user_id=${userId}&token=${token}`
      );
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          // 标记消息为已完成
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMessage.id ? { ...msg, isCompleted: true } : msg
            )
          );
          eventSource.close();
          setIsLoading(false);
          return;
        }
        if (event.data === '[ERROR]') {
          setError('服务器错误，请重试');
          setIsLoading(false);
          eventSource.close();
          return;
        }

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessage.id ? { ...msg, content: msg.content + event.data } : msg
          )
        );
      };

      eventSource.onerror = () => {
        if (eventSource.readyState !== 2) {
          setError('连接错误，请重试');
          setIsLoading(false);
          eventSource.close();
        }
      };
    } catch (err) {
      console.error('Error:', err);
      setError('发送失败，请重试');
      setIsLoading(false);
    }
  };

  return (
    <div className="search-container">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>请输入您的问题开始搜索</p>
          </div>
        ) : (
          <>
            {isReturningUser && (
              <div className="session-notification">
                <p>您已重新进入对话 (阶段 {sessionStage}/10)</p>
              </div>
            )}
            {isPageRefresh && (
              <div className="refresh-notification">
                <p>页面已刷新，正在恢复对话...</p>
              </div>
            )}
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.type}`}>
                <div className="message-content">
                  {message.type === 'user' ? (
                    message.content
                  ) : (
                    <div
                      className="markdown-content"
                      dangerouslySetInnerHTML={{
                        __html: message.content,
                      }}
                    />
                  )}
                  {message.type === 'ai' &&
                    isLoading &&
                    message.id === messages[messages.length - 1]?.id && (
                      <span className="typing-indicator">...</span>
                    )}
                </div>
                <div className="message-time">{message.timestamp}</div>
              </div>
            ))}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="search-form" onSubmit={handleSubmit}>
        <div className="input-group">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="请输入您的问题..."
            disabled={isLoading}
            className="search-input"
          />
          <button
            type="submit"
            disabled={!question.trim() || isLoading}
            className="search-btn"
          >
            {isLoading ? '搜索中...' : '发送'}
          </button>
        </div>
      </form>
    </div>
  );
}
