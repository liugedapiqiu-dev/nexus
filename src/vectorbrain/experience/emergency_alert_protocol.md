# 🚨 紧急消息检测与通知机制

## 经验来源
**创建时间**: 2026-03-13 12:46  
**触发事件**: 群聊情报网系统部署完成后，用户要求添加紧急消息通知功能

## 核心需求

### 1. 紧急消息检测
当群聊中出现以下情况时，**主动通知**用户（发送到飞书私聊）：

#### 🚨 紧急情况（立即通知）
- **关键词触发**: "紧急"、"急"、"马上"、"立即"、"今天必须"、"出问题"、"事故"、"投诉"
- **质量问题**: 产品缺陷、客户投诉、验货失败
- **交期延误**: 工厂延期、物流异常、无法按时交货
- **财务风险**: 付款异常、价格错误、订单取消
- **供应链中断**: 供应商失联、原材料短缺

#### ⚠️ 情绪异常（需要关注）
- **负面情绪词**: "烦"、"累"、"难"、"无语"、"糟糕"、"失望"、"加班"、"痛苦"
- **语气词异常**: 连续感叹号！！！、多个问号？？？、"到底"、"怎么又"
- **冲突信号**: "不对"、"错了"、"不是这样"、"重新做"

#### 🔥 场面热闹（可能重要）
- **高频发言**: 单个群 1 小时内超过 50 条消息
- **多人参与**: 10 分钟内超过 5 人发言
- **密集@**: 短时间内多次@特定人员

### 2. 通知方式
- **渠道**: 飞书私聊（发送到用户 ID: ou_cd2f520717fd4035c6ef3db89a53b748）
- **格式**: 简洁明了，包含关键信息
- **频率**: 同一事件不重复通知，除非有新进展

### 3. 正常运行模式
- **不问不说**: 用户不询问时，不主动汇报常规消息
- **例外**: 仅紧急消息触发主动通知
- **每小时扫描**: 结合消息抓取脚本执行检测

## 技术实现

### 关键词库

```python
# 紧急关键词
URGENCY_KEYWORDS = [
    "紧急", "急", "马上", "立即", "立刻", "今天必须", "刻不容缓",
    "出问题", "事故", "投诉", "异常", "故障", "严重", "危险"
]

# 质量问题关键词
QUALITY_ISSUES = [
    "质量", "缺陷", "不良", "次品", "退货", "投诉", "不合格",
    "验货失败", "色差", "破损", "错误", "做错了"
]

# 交期问题关键词
DELIVERY_ISSUES = [
    "延期", "延误", "延迟", "来不及", "赶不上", "超时",
    "物流异常", "没发货", "未到港", "清关问题"
]

# 财务风险关键词
FINANCIAL_RISKS = [
    "付款失败", "价格错误", "订单取消", "退款", "赔款",
    "亏本", "损失", "赔钱"
]

# 负面情绪词
NEGATIVE_EMOTIONS = [
    "烦", "累", "难", "无语", "糟糕", "失望", "加班", "痛苦",
    "崩溃", "受不了", "太过分了", "气死"
]

# 冲突信号
CONFLICT_SIGNALS = [
    "不对", "错了", "不是这样", "重新做", "返工", "搞什么",
    "怎么回事", "为什么又", "到底"
]
```

### 检测算法

```python
def detect_urgency(messages):
    """检测紧急消息"""
    alerts = []
    
    for msg in messages:
        content = msg.get("content", "")
        sender = msg.get("sender_name", "")
        chat_name = msg.get("chat_name", "")
        timestamp = msg.get("timestamp", "")
        
        # 1. 关键词匹配
        for keyword in URGENCY_KEYWORDS:
            if keyword in content:
                alerts.append({
                    "type": "🚨 紧急情况",
                    "chat": chat_name,
                    "sender": sender,
                    "content": content,
                    "time": timestamp,
                    "trigger": f"包含关键词：{keyword}"
                })
                break
        
        # 2. 情绪分析
        neg_count = sum(1 for word in NEGATIVE_EMOTIONS if word in content)
        if neg_count >= 2:  # 2 个以上负面词
            alerts.append({
                "type": "⚠️ 情绪异常",
                "chat": chat_name,
                "sender": sender,
                "content": content,
                "time": timestamp,
                "trigger": f"负面情绪词：{neg_count}个"
            })
        
        # 3. 语气分析（标点符号）
        if content.count("！") >= 3 or content.count("!") >= 3:
            alerts.append({
                "type": "⚠️ 语气异常",
                "chat": chat_name,
                "sender": sender,
                "content": content,
                "time": timestamp,
                "trigger": "连续感叹号"
            })
    
    return alerts

def detect_hot_discussion(messages):
    """检测热闹场面（高频讨论）"""
    if len(messages) > 50:  # 1 小时内超过 50 条
        return {
            "type": "🔥 高频讨论",
            "count": len(messages),
            "trigger": "消息数超过阈值"
        }
    return None
```

### 通知发送

```python
def send_alert(alerts):
    """发送飞书私聊通知"""
    if not alerts:
        return
    
    # 构建通知内容
    content = ["🚨 **群聊情报网 - 紧急通知**\n"]
    
    for alert in alerts[:5]:  # 最多显示 5 条
        content.append(f"**{alert['type']}**")
        content.append(f"📍 群组：{alert['chat']}")
        content.append(f"👤 发言人：{alert['sender']}")
        content.append(f"⏰ 时间：{alert['time']}")
        content.append(f"💬 内容：{alert['content'][:100]}...")
        content.append(f"🎯 触发：{alert['trigger']}")
        content.append("")
    
    # 发送飞书消息
    send_feishu_message(USER_ID, "\n".join(content))
```

## 部署检查清单

- [x] 创建紧急关键词库
- [x] 集成到 chat_scraper_v2.py
- [x] 修复 chat_analyzer.py
- [ ] 配置飞书通知通道
- [ ] 测试通知功能
- [ ] 添加去重逻辑（避免重复通知）
- [ ] 添加通知历史记录

## 相关文件

- **脚本位置**: `/home/user/.vectorbrain/intelligence/`
  - `chat_scraper_v2.py` - 消息抓取（含紧急检测）
  - `chat_analyzer.py` - 情报分析（待修复）
  - `emergency_detector.py` - 紧急检测模块（新建）

- **数据库**: `~/.vectorbrain/memory/episodic_memory.db`
- **状态文件**: `~/.vectorbrain/intelligence/chat_scraper_state.json`
- **通知日志**: `~/.vectorbrain/intelligence/alerts.log`（待创建）

## 使用示例

### 场景 1: 质量问题
```
群：采购信息同步
消息：「这批货质量有问题，表面有划痕，客户投诉了！」
触发：关键词「质量」、「问题」、「投诉」
动作：立即发送飞书私聊通知
```

### 场景 2: 交期延误
```
群：蜘蛛侠 Switch 设计沟通
消息：「工厂说来不及了，要延期 3 天！！！」
触发：关键词「来不及」、「延期」+ 连续感叹号
动作：立即发送飞书私聊通知
```

### 场景 3: 情绪异常
```
群：醇龙箱包对接
消息：「真是烦死了，怎么又错了，我已经加班三天了！」
触发：负面词「烦」、「累」、「又」
动作：发送关注度通知
```

## 经验教训

1. **关键词匹配要精准** - 避免误报（如"没问题"不应触发）
2. **上下文理解** - 同样的词在不同语境下严重程度不同
3. **通知频率控制** - 同一事件 1 小时内不重复通知
4. **优先级排序** - 紧急 > 情绪 > 热闹
5. **用户可配置** - 允许用户自定义关键词和通知阈值

## 持续优化

- 根据用户反馈调整关键词库
- 学习用户哪些通知被重视、哪些被忽略
- 定期更新情绪词库和语气分析算法
- 考虑添加机器学习模型进行更精准的情感分析

---

*最后更新：2026-03-13 12:46*
*版本：1.0*
