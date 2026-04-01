// OpenClaw Live Monitor - 主脚本

// ========== 全局状态 ==========
let showChinese = true;
let currentFilter = 'all';
let sessionsData = [];
let selectedSessionKey = null;
let sessionSearchQuery = '';
let tokenData = [];
let queueData = {
  waiting: 0,
  running: 0,
  completed: 0,
  paused: 0,
  totalTasks: 0,
  waitTime: 0
};

// ========== WebSocket 连接 ==========
const ws = new WebSocket(`ws://${window.location.host}`);

ws.onopen = () => {
  console.log('✅ WebSocket 已连接');
  updateConnectionStatus(true);
};

ws.onclose = () => {
  console.log('❌ WebSocket 已断开');
  updateConnectionStatus(false);
  // 5 秒后尝试重连
  setTimeout(() => {
    window.location.reload();
  }, 5000);
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'log') {
    addLogEntry(message.data);
    updateTimeline(message.data);
  } else if (message.type === 'health') {
    updateHealth(message.data);
  } else if (message.type === 'sessions') {
    updateSessions(message.data);
  } else if (message.type === 'queue') {
    updateQueue(message.data);
  }
};

// ========== 连接状态更新 ==========
function updateConnectionStatus(connected) {
  const statusDot = document.querySelector('.status-dot');
  const statusText = document.querySelector('.status-text');
  
  if (connected) {
    statusDot.className = 'status-dot online';
    statusText.textContent = '系统运行正常';
    statusDot.style.background = 'var(--accent-green)';
  } else {
    statusDot.className = 'status-dot';
    statusText.textContent = '连接断开';
    statusDot.style.background = 'var(--accent-red)';
  }
}

// ========== 健康状态更新 ==========
function updateHealth(data) {
  const healthScore = document.getElementById('healthScore');
  const healthStatus = document.getElementById('healthStatus');
  const gatewayStatus = document.getElementById('gatewayStatus');
  const feishuStatus = document.getElementById('feishuStatus');
  const errorCount = document.getElementById('errorCount');
  
  if (data.score !== undefined) {
    healthScore.textContent = data.score;
    healthScore.className = `metric-value score-${data.score >= 80 ? 'good' : data.score >= 60 ? 'warn' : 'bad'}`;
    
    if (data.score >= 80) {
      healthStatus.textContent = '✅ 运行正常';
      healthStatus.style.color = 'var(--accent-green)';
    } else if (data.score >= 60) {
      healthStatus.textContent = '⚠️ 需要注意';
      healthStatus.style.color = 'var(--accent-yellow)';
    } else {
      healthStatus.textContent = '❌ 存在异常';
      healthStatus.style.color = 'var(--accent-red)';
    }
  }
  
  if (data.gatewayStatus) {
    gatewayStatus.textContent = data.gatewayStatus === 'online' ? '🟢 在线' : '🔴 离线';
    gatewayStatus.style.color = data.gatewayStatus === 'online' ? 'var(--accent-green)' : 'var(--accent-red)';
  }
  
  if (data.feishuStatus) {
    feishuStatus.textContent = data.feishuStatus === 'online' ? '🟢 在线' : '⚠️ 未知';
    feishuStatus.style.color = data.feishuStatus === 'online' ? 'var(--accent-green)' : 'var(--accent-yellow)';
  }
  
  if (data.errorCount !== undefined) {
    errorCount.textContent = data.errorCount;
    if (data.errorCount > 0) {
      errorCount.parentElement.parentElement.style.borderColor = 'var(--accent-red)';
    }
  }
}

// ========== 日志条目添加 ==========
function addLogEntry(logData) {
  const logStream = document.getElementById('logStream');
  const entry = document.createElement('div');
  entry.className = `log-entry ${logData.level}`;
  
  const time = new Date(logData.timestamp).toLocaleTimeString('zh-CN');
  const text = showChinese ? logData.translated : logData.raw;
  
  entry.innerHTML = `
    <span class="log-time">${time}</span>
    <span class="log-level ${logData.level}">${logData.level}</span>
    <span class="log-text">${escapeHtml(text)}</span>
  `;
  
  // 应用过滤器
  if (currentFilter !== 'all' && logData.level !== currentFilter) {
    entry.style.display = 'none';
  }
  
  // 应用搜索
  const searchQuery = document.getElementById('searchInput').value.toLowerCase();
  if (searchQuery && !text.toLowerCase().includes(searchQuery)) {
    entry.style.display = 'none';
  }
  
  logStream.appendChild(entry);
  
  // 自动滚动到底部
  logStream.scrollTop = logStream.scrollHeight;
  
  // 限制显示数量
  while (logStream.children.length > 200) {
    logStream.removeChild(logStream.firstChild);
  }
}

// ========== 时间线更新 ==========
function updateTimeline(logData) {
  // 检测任务相关日志
  const text = logData.translated || logData.raw;
  
  if (text.includes('任务') || text.includes('开始') || text.includes('完成') || text.includes('错误')) {
    const timelineContainer = document.getElementById('timelineContainer');
    const timelineItem = document.createElement('div');
    
    let status = 'completed';
    let emoji = '✅';
    
    if (text.includes('开始') || text.includes('启动')) {
      status = 'running';
      emoji = '🔄';
    } else if (text.includes('错误') || text.includes('失败')) {
      status = 'error';
      emoji = '❌';
    }
    
    timelineItem.className = `timeline-item ${status}`;
    timelineItem.innerHTML = `
      <span class="timeline-time">${new Date(logData.timestamp).toLocaleTimeString('zh-CN')}</span>
      <div class="timeline-content">
        <div class="timeline-title">${emoji} ${text.substring(0, 60)}</div>
        <div class="timeline-desc">任务执行记录</div>
      </div>
    `;
    
    timelineContainer.insertBefore(timelineItem, timelineContainer.firstChild);
    
    // 限制显示数量
    while (timelineContainer.children.length > 20) {
      timelineContainer.removeChild(timelineContainer.lastChild);
    }
  }
}

// ========== 会话列表更新 ==========
function updateSessions(sessions) {
  if (!sessions || !Array.isArray(sessions)) return;

  sessionsData = sessions;

  const sessionsList = document.getElementById('sessionsList');
  const sessionCountBadge = document.getElementById('sessionCountBadge');

  const filteredSessions = sessions.filter(s => {
    const haystack = [s.displayName, s.subject, s.channel, s.chatType, s.key]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return !sessionSearchQuery || haystack.includes(sessionSearchQuery);
  });

  sessionCountBadge.textContent = `${filteredSessions.length} 个会话`;

  sessionsList.innerHTML = filteredSessions.map(s => {
    const initials = (s.displayName || s.channel || '未知').substring(0, 2).toUpperCase();
    const isActive = s.key === selectedSessionKey;
    return `
      <button class="session-card ${isActive ? 'selected' : ''}" data-session-key="${escapeHtml(s.key)}">
        <div class="session-user">
          <div class="session-avatar">${escapeHtml(initials)}</div>
          <div>
            <div class="session-name">${escapeHtml(s.displayName || '未命名会话')}</div>
            <div class="session-subject">${escapeHtml(s.channel || 'unknown')} · ${escapeHtml(s.chatType || 'unknown')}</div>
          </div>
        </div>
        <div class="session-meta session-meta-stack">
          <span class="session-state state-${escapeHtml(s.state || 'idle')}">${escapeHtml(s.stateLabel || '😴 闲置中')}</span>
          <span class="session-time">${escapeHtml(s.updatedAtStr || '未知')}</span>
        </div>
      </button>
    `;
  }).join('');

  bindSessionCardEvents();

  if (!selectedSessionKey && filteredSessions.length > 0) {
    selectedSessionKey = filteredSessions[0].key;
  }

  if (selectedSessionKey) {
    loadSelectedSession(selectedSessionKey);
  } else {
    renderSelectedSessionEmpty();
  }

  // 更新关系图
  renderSessionMap(filteredSessions);

  // 更新表格
  updateSessionsTable(filteredSessions);
}

// ========== 渲染会话关系图 ==========
function renderSessionMap(sessions) {
  const sessionMap = document.getElementById('sessionMap');
  const centerNode = sessionMap.querySelector('.map-center-node');

  // 清除旧的节点（保留中心节点）
  Array.from(sessionMap.children).forEach(child => {
    if (!child.classList.contains('map-center-node')) {
      sessionMap.removeChild(child);
    }
  });

  if (sessions.length === 0) return;

  const renderSessions = sessions.slice(0, 8);
  const angleStep = (2 * Math.PI) / renderSessions.length;
  const radius = 100;

  renderSessions.forEach((s, i) => {
    const angle = i * angleStep;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    const node = document.createElement('div');
    node.className = `map-node ${s.key === selectedSessionKey ? 'selected' : ''}`;
    node.style.transform = `translate(${x}px, ${y}px)`;

    const initials = (s.displayName || s.channel || '未知').substring(0, 2).toUpperCase();

    node.innerHTML = `
      <div class="map-node-avatar">${escapeHtml(initials)}</div>
      <div class="map-node-label">${escapeHtml((s.displayName || '会话').substring(0, 8))}</div>
      <div class="map-node-stat">${escapeHtml(s.stateLabel || '闲置中')}</div>
    `;

    node.addEventListener('click', () => {
      selectedSessionKey = s.key;
      updateSessions(sessionsData);
    });

    sessionMap.appendChild(node);

    // 添加连接线
    const connection = document.createElement('div');
    connection.className = 'map-connection';
    const distance = Math.sqrt(x * x + y * y);
    const angleDeg = angle * (180 / Math.PI);
    connection.style.width = `${distance}px`;
    connection.style.transform = `rotate(${angleDeg}deg)`;
    sessionMap.insertBefore(connection, centerNode);
  });
}

// ========== 更新会话详情表格 ==========
function updateSessionsTable(sessions) {
  // 从 API 获取详细数据
  fetch('/api/sessions/full')
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById('sessionsTableBody');
      
      if (data && Array.isArray(data)) {
        tbody.innerHTML = data.map(s => `
          <tr>
            <td>${getChannelIcon(s.channel)}</td>
            <td>${escapeHtml(s.user || '未知')}</td>
            <td>${escapeHtml(s.model || '默认')}</td>
            <td>${formatNumber(s.inputTokens || 0)}</td>
            <td>${formatNumber(s.outputTokens || 0)}</td>
            <td><strong>${formatNumber(s.totalTokens || 0)}</strong></td>
            <td>${s.updatedAt || '未知'}</td>
          </tr>
        `).join('');
      }
    })
    .catch(err => console.error('获取会话数据失败:', err));
}

function getChannelIcon(channel) {
  const icons = {
    'feishu': '💬 飞书',
    'telegram': '✈️ Telegram',
    'discord': '🎮 Discord',
    'webchat': '🌐 网页',
    'wechat': '💚 微信'
  };
  return icons[(channel || '').toLowerCase()] || channel;
}

function bindSessionCardEvents() {
  document.querySelectorAll('.session-card[data-session-key]').forEach(card => {
    card.addEventListener('click', () => {
      selectedSessionKey = card.dataset.sessionKey;
      updateSessions(sessionsData);
    });
  });
}

function renderSelectedSessionEmpty() {
  const panel = document.getElementById('selectedSessionPanel');
  panel.innerHTML = '<div class="selected-session-empty">没有匹配到会话，试试换个关键词。</div>';
}

async function loadSelectedSession(sessionKey) {
  const panel = document.getElementById('selectedSessionPanel');
  const fallback = sessionsData.find(s => s.key === sessionKey);
  panel.innerHTML = '<div class="selected-session-loading">正在读取会话详情...</div>';

  try {
    const response = await fetch(`/api/sessions/${encodeURIComponent(sessionKey)}/details`);
    if (!response.ok) throw new Error('load failed');
    const details = await response.json();
    renderSelectedSession(details);
  } catch (error) {
    if (fallback) {
      renderSelectedSession(fallback);
    } else {
      panel.innerHTML = '<div class="selected-session-empty">这个会话详情暂时读不到。</div>';
    }
  }
}

function renderSelectedSession(details) {
  const panel = document.getElementById('selectedSessionPanel');
  const recentMessages = Array.isArray(details.recentMessages) ? details.recentMessages : [];

  panel.innerHTML = `
    <div class="selected-session-header">
      <div>
        <div class="selected-session-title">${escapeHtml(details.displayName || details.key || '未命名会话')}</div>
        <div class="selected-session-subtitle">${escapeHtml(details.channel || 'unknown')} · ${escapeHtml(details.chatType || 'unknown')}</div>
      </div>
      <div class="selected-session-badge state-${escapeHtml(details.state || 'idle')}">${escapeHtml(details.stateLabel || '😴 闲置中')}</div>
    </div>

    <div class="selected-session-grid">
      <div class="selected-stat">
        <span class="label">会话键</span>
        <span class="value mono">${escapeHtml(details.key || '--')}</span>
      </div>
      <div class="selected-stat">
        <span class="label">最后活动</span>
        <span class="value">${escapeHtml(details.updatedAtStr || '--')}</span>
      </div>
      <div class="selected-stat">
        <span class="label">模型</span>
        <span class="value">${escapeHtml(details.model || '--')}</span>
      </div>
      <div class="selected-stat">
        <span class="label">总 Token</span>
        <span class="value">${formatNumber(details.totalTokens || 0)}</span>
      </div>
      <div class="selected-stat wide">
        <span class="label">状态说明</span>
        <span class="value">${escapeHtml(details.stateReason || '暂无说明')}</span>
      </div>
    </div>

    <div class="selected-session-messages">
      <div class="selected-session-section-title">最近消息片段</div>
      ${recentMessages.length ? recentMessages.map(msg => `
        <div class="selected-message-row role-${escapeHtml(msg.role || 'unknown')}">
          <div class="selected-message-meta">${escapeHtml(msg.role || 'unknown')} · ${escapeHtml(msg.timestampStr || '--')}</div>
          <div class="selected-message-preview">${escapeHtml(msg.preview || '(无可显示内容)')}</div>
        </div>
      `).join('') : '<div class="selected-session-empty small">这个会话暂时没有可展示的最近消息。</div>'}
    </div>
  `;
}

// ========== 队列状态更新 ==========
function updateQueue(data) {
  if (!data) return;
  
  queueData = { ...queueData, ...data };
  
  document.getElementById('queueWaiting').textContent = data.waiting || 0;
  document.getElementById('queueRunning').textContent = data.running || 0;
  document.getElementById('queueCompleted').textContent = data.completed || queueData.completed;
  document.getElementById('queuePaused').textContent = data.paused || 0;
  document.getElementById('queueTotal').textContent = data.total || queueData.totalTasks;
  
  const waitTime = data.waitTime || 0;
  document.getElementById('queueWaitTime').textContent = 
    waitTime >= 1000 ? `${(waitTime / 1000).toFixed(1)}s` : `${waitTime}ms`;
  
  // 更新状态徽章
  const statusBadge = document.getElementById('queueStatusBadge');
  const queueAheadEl = document.getElementById('queueAhead');
  
  if (queueAheadEl) {
    queueAheadEl.textContent = data.waiting || 0;
  }
  
  if ((data.waiting || 0) > 5 || waitTime > 10000) {
    statusBadge.textContent = '拥堵';
    statusBadge.className = 'queue-status-badge congested';
  } else if ((data.waiting || 0) > 2 || waitTime > 5000) {
    statusBadge.textContent = '繁忙';
    statusBadge.className = 'queue-status-badge busy';
  } else {
    statusBadge.textContent = '正常';
    statusBadge.className = 'queue-status-badge normal';
  }
}

// ========== Token 图表初始化 ==========
let tokenChart;

function initTokenChart() {
  const ctx = document.getElementById('tokenChart').getContext('2d');
  
  tokenChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Token 使用量',
        data: [],
        borderColor: '#4a9eff',
        backgroundColor: 'rgba(74, 158, 255, 0.1)',
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: '#4a9eff',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(23, 28, 40, 0.9)',
          titleColor: '#e8ecf1',
          bodyColor: '#9aa5b5',
          borderColor: 'rgba(74, 158, 255, 0.3)',
          borderWidth: 1,
          padding: 12,
          displayColors: false,
          callbacks: {
            label: function(context) {
              return `Token: ${context.parsed.y.toLocaleString()}`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(80, 90, 120, 0.2)'
          },
          ticks: {
            color: '#6b758a',
            callback: function(value) {
              return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value;
            }
          }
        },
        x: {
          grid: {
            color: 'rgba(80, 90, 120, 0.2)'
          },
          ticks: {
            color: '#6b758a',
            maxRotation: 45,
            minRotation: 45
          }
        }
      },
      animation: {
        duration: 750,
        easing: 'easeInOutQuart'
      }
    }
  });
}

// ========== 更新 Token 数据 ==========
async function updateTokenData() {
  try {
    const response = await fetch('/api/tokens');
    const data = await response.json();
    
    if (data && data.summary) {
      // 更新今日 Token 显示
      const todayTokensEl = document.getElementById('todayTokens');
      if (todayTokensEl) {
        todayTokensEl.textContent = formatNumber(data.summary.total || 0);
      }
    }
    
    if (tokenChart && data && data.hourly && Array.isArray(data.hourly)) {
      // 更新图表数据
      const recentData = data.hourly.slice(-20);
      tokenChart.data.labels = recentData.map(item => item.hour);
      tokenChart.data.datasets[0].data = recentData.map(item => item.tokens);
      tokenChart.update('none'); // 无动画更新
    }
  } catch (error) {
    console.error('获取 Token 数据失败:', error);
  }
}

// ========== 工具函数 ==========
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatNumber(num) {
  return num.toLocaleString('zh-CN');
}

// ========== 事件监听器 ==========
document.addEventListener('DOMContentLoaded', () => {
  // 初始化图表
  initTokenChart();
  
  // 立即加载 Token 数据
  updateTokenData();
  
  // 每 30 秒更新 Token 数据
  setInterval(updateTokenData, 30000);
  
  // 过滤器按钮
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.level;
      
      // 重新过滤日志
      Array.from(document.getElementById('logStream').children).forEach(entry => {
        const level = entry.classList.contains('error') ? 'error' : 
                     entry.classList.contains('warn') ? 'warn' : 'info';
        entry.style.display = (currentFilter === 'all' || level === currentFilter) ? 'block' : 'none';
      });
    });
  });
  
  // 搜索功能
  document.getElementById('searchInput').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    Array.from(document.getElementById('logStream').children).forEach(entry => {
      const text = entry.querySelector('.log-text').textContent.toLowerCase();
      entry.style.display = text.includes(query) ? 'block' : 'none';
    });
  });

  // 会话搜索
  const sessionSearchInput = document.getElementById('sessionSearchInput');
  if (sessionSearchInput) {
    sessionSearchInput.addEventListener('input', (e) => {
      sessionSearchQuery = e.target.value.trim().toLowerCase();
      updateSessions(sessionsData);
    });
  }
  
  // 语言切换
  document.getElementById('toggleLang').addEventListener('click', () => {
    showChinese = !showChinese;
    document.getElementById('toggleLang').textContent = showChinese ? '🇨🇳 中文' : '🇬🇧 English';
    // 实际应用中应该重新渲染日志
  });
});

// ========== 从日志中提取队列信息 ==========
// 这个函数会被 server.js 调用
window.extractQueueInfo = function(logLine) {
  try {
    if (!logLine.trim().startsWith('{')) return false;
    
    const parsed = JSON.parse(logLine);
    const mainContent = parsed['1'] || parsed['0'] || '';
    
    if (mainContent.includes('lane wait exceeded')) {
      const laneMatch = mainContent.match(/queueAhead=(\d+)/);
      const waitedMatch = mainContent.match(/waitedMs=(\d+)/);
      
      if (laneMatch && waitedMatch) {
        const queueAhead = parseInt(laneMatch[1]);
        const waitedMs = parseInt(waitedMatch[1]);
        
        // 更新队列显示
        updateQueue({
          waiting: queueAhead,
          waitTime: waitedMs
        });
        
        return true;
      }
    }
  } catch (e) {}
  return false;
};
