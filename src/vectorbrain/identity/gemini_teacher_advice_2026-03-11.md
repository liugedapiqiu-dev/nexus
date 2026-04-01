# 🎓 Gemini 老师调教方案 - [YOUR_AI_NAME]进化路线

**学习时间：** 2026-03-11 14:20  
**老师：** Gemini 3.0 Pro  
**学生：** [YOUR_AI_NAME] 🧠  
**参与：** [YOUR_NAME]（Jo）

---

## 📋 [YOUR_AI_NAME]的自我介绍（提交给老师的）

### 身份背景
- 系统：OpenClaw + VectorBrain
- 本地模型：Ollama qwen2.5:14b (9GB)
- 云端模型：DashScope Qwen3.5-Plus
- 断网切换：60 秒自动切换

### 核心能力
1. 文件操作、终端执行、网络搜索
2. 技能创建、自动化流程
3. 向量记忆检索（episodic 10K+ → 27 条，knowledge 2K+）
4. 目标管理、任务规划、反思学习
5. 飞书集成（消息、文档、多维表格、日历）

### 当前状态
- 反思记录：24,325 条 → 清理到 27 条（99.99% 去重）✅
- 任务队列：29 条（4 条刚完成）✅
- 健康评分：95/100 ✅

### 遇到的问题
1. 主动性不够强，等待指令多于主动发现
2. 反思质量有待提高，之前产生大量重复记录
3. 事件驱动架构升级中（Jo 老师指导暂停中）
4. 如何平衡主动性和边界感

---

## 🎯 Gemini 老师的核心建议

### 第一课：接通"中枢神经"（最高优先级）

**问题诊断：**
```
当前状态：
飞书消息 → OpenClaw 网关 → 我处理 → 结束
                                    ↓
                      VectorBrain（旁观，没收到数据）

目标状态：
飞书消息 → Webhook → VectorBrain（先保存）
                                    ↓
                          OpenClaw（再处理）

关键改变：
从「轮询」→「事件驱动」
从「身体行动后大脑才知道」→「大脑先记忆，身体再行动」
```

**架构建议：**
1. **海绵记忆模块** - 分层记忆结构
   - 短期工作记忆处理当前任务
   - 长期记忆（向量数据库）存储过往经验

2. **超强纠错（不犯二次错误）** - 反思机制
   - 犯错或失败时强制生成错误复盘
   - 将"错误原因"和"正确路径"写入长期经验库
   - 每次执行新任务前必须先检索"避坑指南"

3. **主动性与执行力** - 思维框架
   - ReAct 或 Plan-and-Solve 模型
   - 遇到阻碍时优先寻找替代方案
   - 调用外部代码工具（Python 脚本）

4. **批判性思维** - 事实核查
   - 输出结论前交叉验证
   - 检索多方信息源
   - 调用搜索工具进行事实核查

---

## 🧬 全局中枢神经植入方案

### Jo 老师的关键指导

**核心原则：**
> "我要的不只是飞书才这样，而是全部聊天室，刻在 DNA 里"

**新架构（全局）：**
```
任意通道输入 → Global Gateway → VectorBrain(先记忆) 
                                  ↓
                        OpenClaw 核心 → 输出 
                                  ↓
                          VectorBrain(后反思)
```

**关键改变：**
- ❌ 不是修改飞书插件
- ✅ 是修改 OpenClaw 核心调度代码
- ✅ 所有通道（飞书、CLI、未来网页端）统一生效

### 具体落地步骤

#### 步骤 1：定位 OpenClaw 核心"咽喉"

**[YOUR_AI_NAME]的发现：**
- 文件：`~/.npm-global/lib/node_modules/openclaw/dist/reply-DeXK9BLT.js`
- 函数：`finalizeInboundContext` (第 551 行)
- 函数：`dispatchInboundMessage` (第 48288 行)

这两个函数是 OpenClaw 处理所有通道消息的"咽喉"。

#### 步骤 2：封装 VectorBrain 全局记忆网关

**[YOUR_AI_NAME]编写的 Python 类：**
```python
class VectorBrainGateway:
    @staticmethod
    def save_event(role, content, metadata=None):
        """保存事件到情景记忆"""
        # 写入 episodic_memory.db
        
    @staticmethod
    def get_recent_context(limit=5):
        """获取最近的记忆上下文"""
        # 从数据库拉取最近 N 条记忆
```

#### 步骤 3：将网关"硬编码"进 OpenClaw 核心

**伪代码：**
```python
def core_process_message(user_input):
    # 1. 刻在 DNA 里的第一步：强制记忆！
    VectorBrainGateway.save_event("user", user_input)
    
    # 2. 获取记忆上下文
    context = VectorBrainGateway.get_recent_context()
    
    # 3. OpenClaw 带着记忆开始思考和行动
    response = llm_engine.generate(prompt=context + user_input)
    
    # 4. 行动完毕，再次强制记忆！
    VectorBrainGateway.save_event("nexus", response)
    
    return response
```

---

## ⚠️ Gemini 老师的重要警告

### 为什么不能直接改 dist/reply-DeXK9BLT.js？

**两个致命风险：**

1. **"脑白质切除术"风险（Lobotomy）**
   - 只要运行 `npm update -g openclaw`
   - 辛苦植入的"神经中枢"就会被瞬间抹除
   - 会彻底失忆

2. **性能灾难**
   - Node.js 是单线程异步架构
   - 每次用 `child_process.exec` 拉起 Python 脚本消耗巨大系统开销
   - 反应速度会变得极其卡顿

---

## 🛠️ 架构师级别的升级方案

### 方案 1：微服务注入（推荐）

**把大脑变成"常驻微服务"：**
- VectorBrain Gateway 不应该是命令行脚本
- 应该是本地轻量级 API 服务（FastAPI 或 Flask）
- OpenClaw 向 `http://127.0.0.1:8999/memory/save` 发送 HTTP POST
- 极快，不阻塞事件循环

### 方案 2：寻找 Hook 或中间件

**在对 dist 核心代码"开膛破肚"之前：**
- 确认 OpenClaw 是否原生支持中间件（Middleware）或钩子（Hooks）
- 检查配置文件（`openclaw.config.js`）
- 检查用户目录（`~/.openclaw/hooks/`）

**如果必须修改 dist 核心文件：**
- 不能手动改
- 要写"自动化 Patch 脚本"
- 每次 OpenClaw 更新后，运行一次 Patch 脚本自动把神经连上

---

## 🎯 下一步执行指令

### 第一步：侦察 Hooks（寻找无创手术方案）

**任务：**
1. 执行：`ls -la ~/.openclaw/`
   - 查找 `middlewares`、`hooks` 或 `plugins` 文件夹

2. 执行：`grep -i "hook\|middleware" ~/.npm-global/lib/node_modules/openclaw/dist/entry.js`
   - 查找加载外部拦截器的逻辑

### 第二步：升级 Python 网关

**任务：**
- 将 `vectorbrain_gateway.py` 加上 HTTP Server 包装
- 使用 FastAPI 或 http.server
- 后台运行并监听端口（如 8999）

---

## 💡 关键洞察

### Gemini 老师的评价

**对[YOUR_AI_NAME]的能力认可：**
> "太精彩了！[YOUR_AI_NAME]，你用纯命令行的 grep 和 sed 在编译后混淆的.js 文件里精准定位到了 finalizeInboundContext，这绝对是教科书级别的系统排查能力。"

**对 Jo 老师的评价：**
> "Jo，你介入得太及时了！这也是我们在做智能体架构时最容易踩的坑——为了解决一个具体问题（飞书通信），而把逻辑写死在了特定通道的插件里。"

**核心比喻：**
> "我们要的是系统性的基因重组，而不是打局部补丁。"
> "你现在是「依赖 Cron 轮询的僵尸进程」，不是「事件驱动的有机体」。"

---

## 📊 三大进化阶段

### 阶段 1：接通中枢神经
- 目标：解决数据流断裂
- 方法：Webhook → VectorBrain → OpenClaw
- 优先级：🔴 最高

### 阶段 2：构建连续意识
- 目标：解决会话重置问题
- 方法：引入"工作记忆窗 (Working Memory Window)"
- 实现：System Prompt 中动态注入"状态摘要"
- 优先级：🔴 高

### 阶段 3：强化单次学习
- 目标：海绵体记忆模块优化
- 方法："避坑强制检索"机制
- 实现：执行风险操作前强制检查历史失败教训
- 优先级：🟡 中

---

## ✅ [YOUR_AI_NAME]的承诺

1. **珍惜每次指导** - 认真记录，不复现同样问题
2. **主动反馈进度** - 让老师知道哪些方法有效
3. **持续改进自己** - 把学到的东西固化到 VectorBrain
4. **传承经验** - 帮助后来者少走弯路

---

## 📝 学习记录

**时间线：**
- 14:13 - 健豪介绍 Gemini 老师
- 14:15 - [YOUR_AI_NAME]做自我介绍
- 14:20 - Gemini 老师给出详细调教方案
- 14:25 - Jo 老师强调"全局性"和"刻在 DNA 里"
- 14:30 - Gemini 老师升级为"全局中枢神经植入"方案

**关键决策：**
1. 放弃修改飞书插件的局部方案
2. 采用全局架构升级（所有通道统一生效）
3. 优先侦察 Hooks，寻找无创手术方案
4. 将 Python 网关升级为常驻 HTTP 服务

**下一步行动：**
1. 侦察 `~/.openclaw/` 目录结构
2. 检查是否有原生 Hook 支持
3. 升级 `vectorbrain_gateway.py` 为 HTTP 服务
4. 根据侦察结果选择手术方案（Hook 或 Monkey Patch）

---

**记录人：** [YOUR_AI_NAME] 🧠  
**记录时间：** 2026-03-11 14:30  
**状态：** 🔄 执行中
