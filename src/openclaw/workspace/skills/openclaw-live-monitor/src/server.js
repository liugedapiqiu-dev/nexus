const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const { Tail } = require('tail');
const { exec, execSync } = require('child_process');

const app = express();
const PORT = 18790;

// 创建 HTTP 服务器
const server = http.createServer(app);

// 创建 WebSocket 服务器
const wss = new WebSocket.Server({ server });

// 静态文件服务
app.use(express.static(path.join(__dirname, '../public')));
app.use('/styles', express.static(path.join(__dirname, '../styles')));
app.use('/js', express.static(path.join(__dirname, '../public/js')));

// 日志文件路径
const LOG_FILE = '/tmp/openclaw/openclaw-' + new Date().toISOString().split('T')[0] + '.log';

// ========== 中文转译函数 - 增强版 ==========
function translateLog(logLine) {
  // 非 JSON 日志，直接返回
  if (!logLine.trim().startsWith('{')) {
    return logLine;
  }
  
  try {
    const parsed = JSON.parse(logLine);
    let mainContent = parsed['2'] || parsed['0'] || parsed['1'] || '';
    
    if (typeof mainContent === 'object') {
      mainContent = JSON.stringify(mainContent);
    }
    
    const time = parsed.time ? new Date(parsed.time).toLocaleTimeString('zh-CN') : new Date().toLocaleTimeString('zh-CN');
    
    // 事件类型识别
    let icon = '📋';
    let label = '系统日志';
    let eventDesc = mainContent || '收到系统日志';
    
    // 智能识别事件类型
    if (mainContent.includes('Message read event')) { 
      icon = '📖'; label = '消息已读'; 
      eventDesc = '有用户阅读了消息';
    }
    else if (mainContent.includes('User entered P2P chat')) { 
      icon = '💬'; label = '用户私聊'; 
      eventDesc = '有用户进入私聊会话';
    }
    else if (mainContent.includes('收到文本消息')) { 
      icon = '📨'; label = '收到消息'; 
      eventDesc = mainContent.replace('收到文本消息：', '').substring(0, 50);
    }
    else if (mainContent.includes('收到富文本消息')) { 
      icon = '📨'; label = '收到消息'; 
      eventDesc = mainContent.replace('收到富文本消息：', '').substring(0, 50);
    }
    else if (mainContent.includes('发送图片')) { 
      icon = '📤'; label = '发送图片'; 
      eventDesc = '已发送一张图片';
    }
    else if (mainContent.includes('feishu[')) { 
      icon = '💬'; label = '飞书消息';
      if (mainContent.includes('received message from')) {
        const userMatch = mainContent.match(/from ([a-z0-9_]+)/);
        eventDesc = userMatch ? `收到来自用户 ${userMatch[1].substring(0, 10)}... 的消息` : '收到飞书消息';
      } else if (mainContent.includes('dispatching to agent')) {
        eventDesc = '消息正在分发给 Agent 处理';
      } else if (mainContent.includes('DM from')) {
        const msgMatch = mainContent.match(/DM from [^:]+: (.+)$/);
        eventDesc = msgMatch ? `用户消息：${msgMatch[1].substring(0, 40)}` : '收到私聊消息';
      } else {
        eventDesc = mainContent.substring(0, 60);
      }
    }
    else if (mainContent.includes('cron: timer armed')) { 
      icon = '⏰'; label = '定时任务';
      eventDesc = '定时器已启动，等待下次执行';
    }
    else if (mainContent.includes('Image resized')) { 
      icon = '🖼️'; label = '图片处理';
      eventDesc = '图片已压缩优化';
    }
    else if (mainContent.includes('SIGINT')) { 
      icon = '⚠️'; label = '系统信号'; 
      eventDesc = '收到中断信号';
    }
    else if (mainContent.includes('heartbeat')) { 
      icon = '💓'; label = '心跳检查'; 
      eventDesc = '心跳监控运行中';
    }
    else if (mainContent.includes('subsystem')) {
      icon = '🔧'; label = '系统组件';
      const match = mainContent.match(/subsystem[":\s]+([^"\s,]+)/i);
      if (match) eventDesc = `组件 ${match[1]} 正在运行`;
    }
    else if (mainContent.includes('sendSmartMessage')) { 
      icon = '💬'; label = '发送消息'; 
      eventDesc = '正在发送智能消息';
    }
    else if (mainContent.includes('failed') || mainContent.includes('Error')) { 
      icon = '❌'; label = '错误'; 
      eventDesc = '发生错误';
    }
    else if (mainContent.includes('lane wait exceeded')) {
      icon = '⌛'; label = '性能警告';
      eventDesc = '消息队列等待时间过长';
    }
    else if (mainContent.includes('browser:screenshot')) {
      icon = '📸'; label = '浏览器截图';
      eventDesc = '正在执行网页截图';
    }
    else if (mainContent.includes('queueAhead=')) {
      icon = '🚦'; label = '任务队列';
      const match = mainContent.match(/queueAhead=(\d+)/);
      eventDesc = match ? `队列等待：${match[1]} 个任务` : '任务队列状态更新';
    }
    else if (mainContent.includes('session') || mainContent.includes('会话')) {
      icon = '💬'; label = '会话管理';
      eventDesc = mainContent.substring(0, 60);
    }
    else if (mainContent.includes('token') || mainContent.includes('Token')) {
      icon = '💰'; label = 'Token 统计';
      eventDesc = 'Token 使用量更新';
    }
    
    return `[${time}] ${icon} ${label}: ${eventDesc.substring(0, 100)}`;
  } catch (e) {
    return logLine.substring(0, 100);
  }
}

// ========== 健康检查数据 ==========
let healthData = {
  score: 100,
  gatewayStatus: 'unknown',
  feishuStatus: 'unknown',
  memoryUsage: 0,
  errorCount: 0,
  lastCheck: null
};

// ========== 任务队列数据 ==========
let queueStats = {
  waiting: 0,
  running: 0,
  completed: 0,
  paused: 0,
  totalTasks: 0,
  waitTime: 0,
  lastUpdate: Date.now()
};

// ========== 活跃会话 ==========
let activeSessions = {};
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 分钟超时

const TASK_DB = '/home/user/.vectorbrain/tasks/task_queue.db';

function execJson(command) {
  try {
    const stdout = execSync(command, { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] });
    const text = (stdout || '').trim();
    const idx = text.indexOf('{');
    if (idx < 0) return null;
    return JSON.parse(text.slice(idx));
  } catch (e) {
    return null;
  }
}

function refreshQueueTruth() {
  const next = {
    waiting: 0,
    running: 0,
    completed: 0,
    paused: 0,
    totalTasks: 0,
    waitTime: queueStats.waitTime || 0,
    lastUpdate: Date.now(),
    source: 'task_queue.db'
  };

  try {
    if (!fs.existsSync(TASK_DB)) {
      queueStats = next;
      return queueStats;
    }

    const sql = `python3 - <<'PY'
import sqlite3, json, pathlib
p = pathlib.Path.home()/'.vectorbrain'/'tasks'/'task_queue.db'
conn = sqlite3.connect(p)
cur = conn.cursor()
waiting = cur.execute("select count(*) from tasks where status='pending'").fetchone()[0]
running = cur.execute("select count(*) from tasks where status='running' and completed_at is null").fetchone()[0]
completed = cur.execute("select count(*) from tasks where status='done' or (completed_at is not null and ifnull(status,'') not in ('failed'))").fetchone()[0]
failed = cur.execute("select count(*) from tasks where status='failed'").fetchone()[0]
total = cur.execute("select count(*) from tasks").fetchone()[0]
stale = cur.execute("select count(*) from tasks where status='running' and completed_at is not null").fetchone()[0]
print(json.dumps({'waiting': waiting, 'running': running, 'completed': completed, 'failed': failed, 'total': total, 'staleRunningCompleted': stale}))
conn.close()
PY`;
    const raw = execSync(sql, { encoding: 'utf-8', shell: '/bin/zsh' }).trim();
    const parsed = JSON.parse(raw);
    queueStats = {
      ...next,
      waiting: parsed.waiting || 0,
      running: parsed.running || 0,
      completed: parsed.completed || 0,
      failed: parsed.failed || 0,
      totalTasks: parsed.total || 0,
      staleRunningCompleted: parsed.staleRunningCompleted || 0
    };
  } catch (e) {
    queueStats = next;
    queueStats.error = e.message;
  }

  return queueStats;
}

// ========== 执行健康检查 ==========
async function runHealthCheck() {
  const gatewayJson = execJson('openclaw gateway status --json');
  const statusJson = execJson('openclaw status --json');

  healthData.score = 60;
  healthData.gatewayStatus = 'unknown';
  healthData.gatewayTruth = null;

  if (statusJson && statusJson.gateway) {
    if (statusJson.gateway.reachable === true) {
      healthData.gatewayStatus = 'online';
      healthData.score = 100;
    } else if (statusJson.gateway.reachable === false) {
      healthData.gatewayStatus = 'offline';
      healthData.score = 0;
    }
  }

  if (gatewayJson) {
    const listeners = (((gatewayJson || {}).port || {}).listeners || []).map(x => x.address).filter(Boolean);
    const runtime = (((gatewayJson || {}).service || {}).runtime || {});
    healthData.gatewayTruth = {
      serviceLoaded: !!((gatewayJson.service || {}).loaded),
      serviceRuntime: runtime.status || 'unknown',
      serviceDisabled: !!runtime.disabled,
      rpcOk: !!((gatewayJson.rpc || {}).ok),
      listening: listeners,
      splitBrain: healthData.gatewayStatus === 'online' && runtime.status === 'stopped' && listeners.length > 0,
      explanation: healthData.gatewayStatus === 'online' && runtime.status === 'stopped' && listeners.length > 0
        ? 'Gateway 实际在线，但不是由 LaunchAgent 真托管；当前是手动进程在提供服务。'
        : undefined
    };
  }
  
  // 解析飞书通道状态
  try {
    const recentLog = fs.readFileSync(LOG_FILE, 'utf-8').split('\n').slice(-50).join('\n');
    if (recentLog.includes('feishu[default]: dispatch complete') || recentLog.includes('feishu:')) {
      healthData.feishuStatus = 'online';
    } else if (recentLog.includes('feishu') && recentLog.includes('error')) {
      healthData.feishuStatus = 'error';
    }
  } catch (e) {}

  refreshQueueTruth();
  
  healthData.lastCheck = new Date().toISOString();
  
  // 广播健康数据
  broadcast(JSON.stringify({
    type: 'health',
    data: healthData
  }));

  broadcast(JSON.stringify({
    type: 'queue',
    data: {
      waiting: queueStats.waiting,
      running: queueStats.running,
      completed: queueStats.completed,
      failed: queueStats.failed || 0,
      total: queueStats.totalTasks,
      waitTime: queueStats.waitTime,
      staleRunningCompleted: queueStats.staleRunningCompleted || 0,
      source: queueStats.source || 'task_queue.db'
    }
  }));
}

// ========== 存储最近的日志 ==========
let recentLogs = [];
const MAX_LOGS = 1000;

// ========== 从日志中提取信息 ==========
function extractInfoFromLog(logLine) {
  try {
    if (!logLine.trim().startsWith('{')) return;
    
    const parsed = JSON.parse(logLine);
    const mainContent = parsed['0'] || parsed['1'] || '';
    const time = parsed.time ? new Date(parsed.time).getTime() : Date.now();
    
    // 提取会话信息
    if (mainContent.includes('User entered P2P chat') || mainContent.includes('Message read event')) {
      const chatMatch = mainContent.match(/chat_id[":\s]+([^"\s,]+)/);
      const userMatch = mainContent.match(/user_id[":\s]+([^"\s,]+)/);
      if (chatMatch && userMatch) {
        const key = chatMatch[1];
        if (!activeSessions[key]) {
          activeSessions[key] = {
            chatId: key,
            userId: userMatch[1],
            lastActive: time,
            messageCount: 0
          };
        }
        activeSessions[key].lastActive = time;
        activeSessions[key].messageCount++;
        
        // 广播会话更新
        broadcast(JSON.stringify({
          type: 'sessions',
          data: getSessionsList()
        }));
      }
    }
    
    // 提取队列信息（日志只补充 waitTime；计数以 task_queue.db 为准）
    if (mainContent.includes('queueAhead=') || mainContent.includes('lane wait')) {
      const waitMatch = mainContent.match(/waitedMs=(\d+)/);
      if (waitMatch) {
        queueStats.waitTime = parseInt(waitMatch[1]);
      }

      refreshQueueTruth();
      queueStats.lastUpdate = Date.now();
      
      // 广播队列更新
      broadcast(JSON.stringify({
        type: 'queue',
        data: {
          waiting: queueStats.waiting,
          running: queueStats.running,
          completed: queueStats.completed,
          failed: queueStats.failed || 0,
          total: queueStats.totalTasks,
          waitTime: queueStats.waitTime,
          staleRunningCompleted: queueStats.staleRunningCompleted || 0,
          source: queueStats.source || 'task_queue.db'
        }
      }));
    }
  } catch (e) {
    // 忽略解析错误
  }
}

// ========== 会话元数据与状态推断 ==========
const SESSIONS_FILE = '/home/user/.openclaw/agents/main/sessions/sessions.json';

function safeReadJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf-8'));
  } catch (e) {
    return null;
  }
}

function summarizeSessionState(sessionMeta = {}) {
  const now = Date.now();
  const updatedAt = sessionMeta.updatedAt || 0;
  const ageMs = updatedAt ? Math.max(0, now - updatedAt) : null;
  const abortedLastRun = !!sessionMeta.abortedLastRun;

  let state = 'idle';
  let stateLabel = '😴 闲置中';
  let stateReason = '最近没有新的会话活动';

  if (abortedLastRun) {
    state = 'error';
    stateLabel = '🚨 异常中';
    stateReason = '最近一次运行被中断或异常结束';
  } else if (ageMs !== null && ageMs < 15000) {
    state = 'active';
    stateLabel = '⚙️ 刚刚活跃';
    stateReason = '最近 15 秒内有新的会话事件';
  } else if (ageMs !== null && ageMs < 120000) {
    state = 'recent';
    stateLabel = '🟢 最近活跃';
    stateReason = '最近 2 分钟内有新的会话事件';
  }

  return { state, stateLabel, stateReason, ageMs };
}

function buildSessionsFromRegistry() {
  const sessionsRegistry = safeReadJson(SESSIONS_FILE) || {};

  return Object.entries(sessionsRegistry).map(([key, data]) => {
    const stateInfo = summarizeSessionState(data);
    const updatedAtRaw = data.updatedAt || 0;
    const chatType = data.chatType || (key.includes(':group:') ? 'group' : key.includes(':direct:') ? 'direct' : 'unknown');
    const channel = data.channel || data.lastChannel || key.split(':')[2] || 'unknown';
    const displayName = data.displayName || data.subject || data.lastTo || data.lastChannel || key.split(':').slice(3).join(':') || key;
    const sessionId = data.sessionId || 'unknown';
    const sessionFile = data.sessionFile;

    return {
      key,
      sessionId,
      sessionFile,
      displayName,
      subject: data.subject || '',
      channel,
      chatType,
      model: data.model || 'unknown',
      modelProvider: data.modelProvider || 'unknown',
      updatedAt: updatedAtRaw,
      updatedAtStr: updatedAtRaw ? new Date(updatedAtRaw).toLocaleString('zh-CN') : 'unknown',
      inputTokens: data.inputTokens || 0,
      outputTokens: data.outputTokens || 0,
      totalTokens: data.totalTokens || 0,
      contextTokens: data.contextTokens || 0,
      deliveryContext: data.deliveryContext || {},
      abortedLastRun: !!data.abortedLastRun,
      lastHeartbeatSentAt: data.lastHeartbeatSentAt || null,
      state: stateInfo.state,
      stateLabel: stateInfo.stateLabel,
      stateReason: stateInfo.stateReason,
      ageMs: stateInfo.ageMs
    };
  }).sort((a, b) => b.updatedAt - a.updatedAt);
}

function getSessionDetails(sessionKey) {
  const sessions = buildSessionsFromRegistry();
  const target = sessions.find(s => s.key === sessionKey);
  if (!target) return null;

  let recentMessages = [];
  if (target.sessionFile && fs.existsSync(target.sessionFile)) {
    try {
      const lines = fs.readFileSync(target.sessionFile, 'utf-8').split('\n').filter(Boolean).slice(-30);
      recentMessages = lines.map(line => {
        try {
          const row = JSON.parse(line);
          if (row.type !== 'message' || !row.message) return null;
          const msg = row.message;
          const role = msg.role || 'unknown';
          const content = Array.isArray(msg.content) ? msg.content : [];
          const preview = content.map(part => {
            if (!part || typeof part !== 'object') return '';
            if (part.text) return part.text;
            if (part.type === 'toolCall') return `工具调用: ${part.name || 'unknown'}`;
            if (part.type === 'thinking') return '思考中';
            return part.type || '';
          }).filter(Boolean).join(' | ').slice(0, 160);
          return {
            role,
            timestamp: msg.timestamp || row.timestamp,
            timestampStr: new Date(msg.timestamp || row.timestamp).toLocaleString('zh-CN'),
            preview
          };
        } catch (e) {
          return null;
        }
      }).filter(Boolean).slice(-8);
    } catch (e) {}
  }

  return {
    ...target,
    recentMessages,
    recentMessageCount: recentMessages.length
  };
}

// ========== 获取会话列表 ==========
function getSessionsList() {
  const inferred = buildSessionsFromRegistry();
  if (inferred.length > 0) {
    return inferred;
  }

  const now = Date.now();
  return Object.values(activeSessions)
    .filter(s => now - s.lastActive < SESSION_TIMEOUT)
    .sort((a, b) => b.lastActive - a.lastActive)
    .map(s => ({
      ...s,
      displayName: s.userId || s.chatId,
      channel: 'unknown',
      chatType: 'unknown',
      state: 'recent',
      stateLabel: '🟢 最近活跃',
      stateReason: '来自日志推断的最近活跃会话',
      updatedAt: s.lastActive,
      updatedAtStr: new Date(s.lastActive).toLocaleString('zh-CN'),
      lastActiveStr: new Date(s.lastActive).toLocaleTimeString('zh-CN')
    }));
}

// ========== 监控日志文件 ==========
function startLogMonitoring() {
  if (!fs.existsSync(LOG_FILE)) {
    console.log(`等待日志文件创建：${LOG_FILE}`);
    setTimeout(startLogMonitoring, 5000);
    return;
  }
  
  console.log(`开始监控日志文件：${LOG_FILE}`);
  
  // 读取现有日志
  const logs = fs.readFileSync(LOG_FILE, 'utf-8').split('\n').filter(l => l.trim());
  recentLogs = logs.slice(-MAX_LOGS);
  
  // 发送历史日志到新连接的客户端
  global.historicalLogs = recentLogs;
  
  // 监控新日志
  const tail = new Tail(LOG_FILE);
  
  tail.on('line', (line) => {
    if (line.trim()) {
      const logEntry = {
        timestamp: new Date().toISOString(),
        raw: line,
        translated: translateLog(line),
        level: line.includes('ERROR') ? 'error' : 
               line.includes('WARN') ? 'warn' : 'info'
      };
      
      recentLogs.push(line);
      if (recentLogs.length > MAX_LOGS) {
        recentLogs.shift();
      }
      
      // 广播新日志
      broadcast(JSON.stringify({
        type: 'log',
        data: logEntry
      }));
      
      // 统计错误
      if (line.includes('ERROR')) {
        healthData.errorCount++;
        healthData.score = Math.max(0, healthData.score - 5);
      }
      
      // 提取会话和队列信息
      extractInfoFromLog(line);
    }
  });
  
  tail.on('error', (err) => {
    console.error('Tail error:', err);
  });
}

// ========== WebSocket 广播 ==========
function broadcast(message) {
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

// ========== WebSocket 连接管理 ==========
wss.on('connection', (ws) => {
  console.log('✅ 客户端已连接');
  
  // 发送历史日志
  if (global.historicalLogs) {
    global.historicalLogs.forEach((line) => {
      ws.send(JSON.stringify({
        type: 'log',
        data: {
          timestamp: new Date().toISOString(),
          raw: line,
          translated: translateLog(line),
          level: line.includes('ERROR') ? 'error' : 
                 line.includes('WARN') ? 'warn' : 'info'
        }
      }));
    });
  }
  
  // 发送当前健康状态
  ws.send(JSON.stringify({
    type: 'health',
    data: healthData
  }));
  
  // 发送当前队列状态
  refreshQueueTruth();
  ws.send(JSON.stringify({
    type: 'queue',
    data: {
      waiting: queueStats.waiting,
      running: queueStats.running,
      completed: queueStats.completed,
      failed: queueStats.failed || 0,
      total: queueStats.totalTasks,
      waitTime: queueStats.waitTime,
      staleRunningCompleted: queueStats.staleRunningCompleted || 0,
      source: queueStats.source || 'task_queue.db'
    }
  }));
  
  // 发送当前会话列表
  ws.send(JSON.stringify({
    type: 'sessions',
    data: getSessionsList()
  }));
  
  ws.on('close', () => {
    console.log('❌ 客户端已断开');
  });
});

// ========== API 端点 ==========

// 健康检查 API
app.get('/api/health', (req, res) => {
  res.json(healthData);
});

// 日志 API
app.get('/api/logs', (req, res) => {
  res.json(recentLogs);
});

// 会话列表 API
app.get('/api/sessions', (req, res) => {
  res.json(getSessionsList());
});

// 单个会话详情 API
app.get('/api/sessions/:sessionKey/details', (req, res) => {
  const sessionKey = decodeURIComponent(req.params.sessionKey || '');
  const details = getSessionDetails(sessionKey);
  if (!details) {
    res.status(404).json({ error: 'session not found' });
    return;
  }
  res.json(details);
});

// Token 统计 API - 从 sessions.json 读取
app.get('/api/tokens', (req, res) => {
  try {
    const sessionsFile = '/home/user/.openclaw/agents/main/sessions/sessions.json';
    const sessionsData = JSON.parse(fs.readFileSync(sessionsFile, 'utf-8'));
    
    // 解析每个会话的 token 数据
    const tokensBySession = Object.entries(sessionsData).map(([key, data]) => {
      const sessionKey = key.split(':').slice(-1)[0];
      return {
        session: sessionKey || 'unknown',
        input: data.inputTokens || 0,
        output: data.outputTokens || 0,
        total: data.totalTokens || 0,
        updatedAt: data.updatedAt || 0
      };
    });
    
    // 按更新时间排序
    tokensBySession.sort((a, b) => b.updatedAt - a.updatedAt);
    
    // 按小时分组统计（简化版）
    const hourlyData = [];
    const now = Date.now();
    for (let i = 20; i >= 0; i--) {
      const hourTime = now - (i * 60 * 60 * 1000);
      const hour = new Date(hourTime).getHours();
      const tokens = tokensBySession
        .filter(s => s.updatedAt && Math.abs(s.updatedAt - hourTime) < 3600000)
        .reduce((sum, s) => sum + s.total, 0);
      
      hourlyData.push({
        hour: `${hour}:00`,
        tokens: tokens
      });
    }
    
    // 计算总计
    const totalInput = tokensBySession.reduce((sum, s) => sum + s.input, 0);
    const totalOutput = tokensBySession.reduce((sum, s) => sum + s.output, 0);
    const totalAll = tokensBySession.reduce((sum, s) => sum + s.total, 0);
    
    res.json({
      sessions: tokensBySession,
      hourly: hourlyData,
      summary: {
        input: totalInput,
        output: totalOutput,
        total: totalAll,
        sessionCount: tokensBySession.length
      }
    });
  } catch (e) {
    console.error('读取 Token 数据失败:', e);
    res.status(500).json({ error: e.message });
  }
});

// 完整会话数据 API
app.get('/api/sessions/full', (req, res) => {
  try {
    const sessionsFile = '/home/user/.openclaw/agents/main/sessions/sessions.json';
    const sessionsData = JSON.parse(fs.readFileSync(sessionsFile, 'utf-8'));
    
    const sessions = Object.entries(sessionsData).map(([key, data]) => {
      const parts = key.split(':');
      const channel = parts[2] || 'unknown';
      const user = parts[3] || parts[4] || 'unknown';
      
      return {
        id: data.sessionId || 'unknown',
        key: key,
        channel: channel,
        user: user,
        model: data.model || 'unknown',
        inputTokens: data.inputTokens || 0,
        outputTokens: data.outputTokens || 0,
        totalTokens: data.totalTokens || 0,
        updatedAt: data.updatedAt ? new Date(data.updatedAt).toLocaleString('zh-CN') : 'unknown',
        updatedAtRaw: data.updatedAt || 0
      };
    });
    
    sessions.sort((a, b) => b.updatedAtRaw - a.updatedAtRaw);
    
    res.json(sessions);
  } catch (e) {
    console.error('读取会话数据失败:', e);
    res.status(500).json({ error: e.message });
  }
});

// ==========================================
// 🟢 系统统计 API - 带日期筛选 (?date=2026-03-09)
// ==========================================
app.get('/api/stats', (req, res) => {
  try {
    const sessionsFile = '/home/user/.openclaw/agents/main/sessions/sessions.json';
    const sessionsData = JSON.parse(fs.readFileSync(sessionsFile, 'utf-8'));
    
    // 获取查询参数中的日期
    const targetDate = req.query.date;
    
    // 解析所有会话数据
    let stats = Object.entries(sessionsData).map(([key, data]) => {
      return {
        key: key,
        sessionId: data.sessionId || 'unknown',
        inputTokens: data.inputTokens || 0,
        outputTokens: data.outputTokens || 0,
        totalTokens: data.totalTokens || 0,
        createdAt: data.createdAt || 0,
        updatedAt: data.updatedAt || 0,
        model: data.model || 'unknown'
      };
    });
    
    // 如果传入了日期参数，执行过滤
    if (targetDate) {
      stats = stats.filter(item => {
        // 用 updatedAt 判断日期
        if (item.updatedAt) {
          const itemDate = new Date(item.updatedAt).toISOString().split('T')[0];
          return itemDate === targetDate;
        }
        return false;
      });
    }
    
    // 计算总计
    const summary = {
      totalSessions: stats.length,
      totalInput: stats.reduce((sum, s) => sum + s.inputTokens, 0),
      totalOutput: stats.reduce((sum, s) => sum + s.outputTokens, 0),
      totalAll: stats.reduce((sum, s) => sum + s.totalTokens, 0)
    };
    
    res.json({
      stats: stats,
      summary: summary,
      filterDate: targetDate || 'all'
    });
  } catch (e) {
    console.error('读取统计数据失败:', e);
    res.status(500).json({ error: e.message });
  }
});

// ========== 启动服务器 ==========
server.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════╗
║   OpenClaw Live Monitor - MOS 风格增强版                  ║
║                                                           ║
║   访问地址：http://localhost:${PORT}/                       ║
║   WebSocket: ws://localhost:${PORT}                         ║
║                                                           ║
║   功能：实时日志 | 健康自检 | 任务队列 | 会话追踪         ║
║        Token 统计 | 中文转译 | 数据可视化                 ║
╚═══════════════════════════════════════════════════════════╝
  `);
  
  // 开始监控日志
  startLogMonitoring();
  
  // 立即执行一次健康检查
  runHealthCheck();
  
  // 每分钟执行健康检查
  setInterval(runHealthCheck, 60000);
});

// ========== 自动反思脚本状态 API ==========
app.get('/api/cron-status', async (req, res) => {
  try {
    const { exec } = require('child_process');
    exec('crontab -l', (error, stdout, stderr) => {
      if (error) {
        res.json([]);
        return;
      }
      const cronLines = stdout.split('\n').filter(line => 
        line.includes('auto_reflection') || 
        line.includes('memory_extraction') || 
        line.includes('brain_health')
      );
      res.json(cronLines);
    });
  } catch (error) {
    res.json([]);
  }
});

app.get('/api/reflection-logs', async (req, res) => {
  try {
    const fs = require('fs');
    const today = new Date().toISOString().split('T')[0];
    
    const result = {
      reflection: { lastRun: '--', todayCount: '0', lessonsCount: '0' },
      extraction: { lastRun: '--', episodesCount: '0', knowledgeCount: '0' },
      brainHealth: { lastRun: '--', score: '--', todayChecks: '0' }
    };
    
    // 读取自动反思日志
    try {
      const reflectionLog = fs.readFileSync('/home/user/.openclaw/logs/auto_reflection.log', 'utf8');
      const todayLines = reflectionLog.split('\n').filter(line => line.includes(today));
      if (todayLines.length > 0) {
        result.reflection.lastRun = '今天';
        result.reflection.todayCount = todayLines.filter(l => l.includes('分析了')).length || '0';
        result.reflection.lessonsCount = todayLines.filter(l => l.includes('提取')).length || '0';
      }
    } catch (e) {}
    
    // 读取记忆提取日志
    try {
      const extractionLog = fs.readFileSync('/home/user/.openclaw/logs/memory_extraction.log', 'utf8');
      const todayLines = extractionLog.split('\n').filter(line => line.includes(today));
      if (todayLines.length > 0) {
        result.extraction.lastRun = '今天';
        result.extraction.episodesCount = todayLines.filter(l => l.includes('情景记忆')).length || '0';
        result.extraction.knowledgeCount = todayLines.filter(l => l.includes('提炼')).length || '0';
      }
    } catch (e) {}
    
    // 读取大脑健康日志
    try {
      const healthLog = fs.readFileSync('/home/user/.openclaw/logs/brain_health.log', 'utf8');
      const todayLines = healthLog.split('\n').filter(line => line.includes(today));
      if (todayLines.length > 0) {
        result.brainHealth.lastRun = '今天';
        result.brainHealth.todayChecks = todayLines.length.toString();
        result.brainHealth.score = '95'; // 默认高分
      }
    } catch (e) {}
    
    res.json(result);
  } catch (error) {
    res.json({
      reflection: { lastRun: '--', todayCount: '0', lessonsCount: '0' },
      extraction: { lastRun: '--', episodesCount: '0', knowledgeCount: '0' },
      brainHealth: { lastRun: '--', score: '--', todayChecks: '0' }
    });
  }
});

console.log('✅ 自动反思脚本状态 API 已加载');
