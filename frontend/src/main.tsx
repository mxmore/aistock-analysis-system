
// 更早期的错误过滤 - 在任何其他代码执行之前
(function() {
  // 立即设置错误过滤器
  const originalAddEventListener = window.addEventListener;
  window.addEventListener = function(type, listener, options) {
    if (type === 'unhandledrejection') {
      const wrappedListener = function(event) {
        const reason = event.reason;
        if (reason && 
            (reason.name === 'i' || 
             reason.code === 403 || 
             reason.message === 'permission error' ||
             (reason.data && reason.data.code === 403))) {
          event.preventDefault();
          event.stopImmediatePropagation();
          return false;
        }
        return listener.call(this, event);
      };
      return originalAddEventListener.call(this, type, wrappedListener, options);
    }
    return originalAddEventListener.call(this, type, listener, options);
  };

  // 立即设置 Promise rejection 处理器
  window.addEventListener('unhandledrejection', function(event) {
    const reason = event.reason;
    if (reason && 
        (reason.name === 'i' || 
         reason.code === 403 || 
         reason.message === 'permission error' ||
         (reason.data && reason.data.code === 403))) {
      event.preventDefault();
      event.stopImmediatePropagation();
      console.debug('🔇 Extension error filtered early:', reason.name || reason.code);
      return false;
    }
  }, true); // 使用捕获阶段
})();

import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './ui/App'

// 开发环境提示和额外保护
const isDevelopment = window.location.hostname === 'localhost';
if (isDevelopment) {
  console.info('%c🚀 AI Stock Analysis App', 'color: #00ff00; font-weight: bold; font-size: 16px;');
  console.info('%c📢 Extension errors are filtered - your app is working normally', 'color: #ffa500; font-size: 12px;');
}

createRoot(document.getElementById('root')!).render(<App />)
