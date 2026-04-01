// 日志转译模块 - 将 OpenClaw 日志转译为人类可读的中文

// 事件类型映射
const eventTypes = {
  'Message read event': { icon: '📖', label: '消息已读' },
  'User entered P2P chat': { icon: '💬', label: '用户私聊' },
  '收到文本消息': { icon: '📨', label: '收到消息' },
  '发送图片': { icon: '📤', label: '发送图片' },
  'Browser control': { icon: '🌐', label: '浏览器控制' },
  'SIGINT': { icon: '⚠️', label: '系统信号' },
  'heartbeat': { icon: '💓', label: '心跳检查' },
  'cron': { icon: '⏰', label: '定时任务' },
  'gmail': { icon: '📧', label: 'Gmail 监控' },
  'canvas': { icon: '🎨', label: 'Canvas 服务' },
  'model': { icon: '🤖', label: 'AI 模型' },
  'listening on': { icon: '🔌', label: '服务监听' },
  'Registered hook': { icon: '🔗', label: '钩子注册' },
  'sendSmartMessage': { icon: '💬', label: '发送消息' },
  'failed': { icon: '❌', label: '错误' },
  'error': { icon: '❌', label: '错误' },
  'Error': { icon: '❌', label: '错误' }
};

/**
 * 将 JSON 日志转译为人类可读的中文
 * @param {string} logLine - 原始日志行
 * @returns {string} - 转译后的中文日志
 */
function translateLog(logLine) {
  // 非 JSON 日志，尝试关键词替换
  if (!logLine.trim().startsWith('{')) {
    let result = logLine;
    for (const [en, zh] of Object.entries(translationDict || {})) {
      result = result.replace(new RegExp(en, 'g'), zh);
    }
    return result;
  }
  
  // JSON 日志，智能解析
  try {
    const parsed = JSON.parse(logLine);
    
    // 提取主要内容（"1" 字段）
    const mainContent = parsed['1'] ? String(parsed['1']) : '';
    const time = parsed.time ? new Date(parsed.time).toLocaleTimeString('zh-CN') : new Date().toLocaleTimeString('zh-CN');
    
    // 识别事件类型
    let eventInfo = { icon: '📋', label: '系统日志' };
    for (const [keyword, info] of Object.entries(eventTypes)) {
      if (mainContent.includes(keyword)) {
        eventInfo = info;
        break;
      }
    }
    
    // 特殊处理 JSON 格式的日志
    let eventDesc = mainContent;
    
    // 处理 cron 模块日志
    if (mainContent.includes('"module":"cron"')) {
      eventDesc = '定时任务配置已加载';
    }
    // 处理 subsystem 日志
    else if (mainContent.includes('"subsystem"')) {
      const match = mainContent.match(/"subsystem"\s*:\s*"([^"]+)"/);
      if (match) {
        eventDesc = `系统组件：${match[1]}`;
      }
    }
    // 处理简单的键值对 JSON
    else if (mainContent.startsWith('{') && mainContent.includes('"module"')) {
      const match = mainContent.match(/"module"\s*:\s*"([^"]+)"/);
      if (match) {
        eventDesc = `模块：${match[1]}`;
      }
    }
    
    return `[${time}] ${eventInfo.icon} ${eventInfo.label}: ${eventDesc.substring(0, 120)}`;
  } catch (e) {
    // JSON 解析失败，返回原文
    return logLine.substring(0, 120);
  }
}

module.exports = { translateLog };
