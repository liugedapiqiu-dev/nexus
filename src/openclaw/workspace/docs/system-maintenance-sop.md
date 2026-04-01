# 系统维护 SOP（[YOUR_AI_NAME]版）

更新时间：2026-03-16

这份 SOP 解决三类高频问题：
- 配置改坏后脚本起不来
- cron 看起来在跑，实际上脚本没成功
- 出故障时不知道先查哪里

---

## 1. 改完 JSON 配置后的标准动作

适用文件：
- `~/.openclaw/openclaw.json`
- 任何 `.json` 配置文件

### 检查命令
```bash
python3 -m json.tool ~/.openclaw/openclaw.json >/dev/null && echo OK
```

### 判断结果
- 输出 `OK`：JSON 格式正常
- 报错：说明有语法问题，优先修复后再跑脚本

### 常见错误
- 少逗号
- 多逗号
- 引号不配对
- 花括号/方括号没闭合

---

## 2. 飞书群消息增量抓取 SOP

脚本：
```bash
~/.vectorbrain/intelligence/chat_scraper_v2.py --mode incremental
```

### 手动执行
```bash
python3 ~/.vectorbrain/intelligence/chat_scraper_v2.py --mode incremental
```

### 成功标志
日志末尾出现：
```text
📊 执行完成
群聊数：...
新增消息：...
```

### 必查文件
- 运行日志：`~/.vectorbrain/chat_scraper.log`
- 事件日志：`~/.vectorbrain/chat_scraper_log.jsonl`
- 状态文件：`~/.vectorbrain/chat_scraper_state.json`
- 数据库：`~/.vectorbrain/memory/episodic_memory.db`

### 快速检查
```bash
tail -n 20 ~/.vectorbrain/chat_scraper_log.jsonl
```

看有没有：
- `run_started`
- `run_completed`

### 如果只有 `run_started` 没有 `run_completed`
优先排查：
1. `~/.openclaw/openclaw.json` 是否是合法 JSON
2. Feishu 网络 / SSL 是否异常
3. 是否有配置缺失（appId/appSecret）
4. 是否存在锁文件残留：
```bash
ls -l ~/.vectorbrain/chat_scraper.lock
```

### 验证是否成功落库
```bash
python3 - <<'PY'
import sqlite3, pathlib
p = pathlib.Path.home()/'.vectorbrain/memory/episodic_memory.db'
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("select chat_name, sender_name, content, timestamp from conversations order by id desc limit 5")
for row in cur.fetchall():
    print(row)
conn.close()
PY
```

---

## 3. 增量向量化 SOP

脚本：
```bash
/home/user/.vectorbrain/connector/episodic_incremental_vectorizer.py
```

### 固定解释器
不要再用裸 `python3`，统一用：
```bash
/home/user/.vectorbrain/.venv-faiss/bin/python /home/user/.vectorbrain/connector/episodic_incremental_vectorizer.py
```

### 手动执行
```bash
/home/user/.vectorbrain/.venv-faiss/bin/python /home/user/.vectorbrain/connector/episodic_incremental_vectorizer.py
```

### 常见问题
#### 1) `faiss 不可用`
说明 Python 环境不对。优先检查：
```bash
/home/user/.vectorbrain/.venv-faiss/bin/python -c "import faiss; print('OK')"
```

#### 2) 数据库字段不匹配
看脚本是否还在用旧字段名；先查表结构：
```bash
python3 - <<'PY'
import sqlite3, pathlib
p = pathlib.Path.home()/'.vectorbrain/memory/episodic_memory.db'
conn = sqlite3.connect(p)
cur = conn.cursor()
for table in ['episodes', 'conversations']:
    print('\nTABLE', table)
    cur.execute(f'PRAGMA table_info({table})')
    for row in cur.fetchall():
        print(row)
conn.close()
PY
```

### 日志文件
```bash
tail -n 30 ~/.vectorbrain/episodic_incremental.log
```

---

## 4. Cron 任务体检 SOP

### 查看全部 cron
```bash
crontab -l
```

### 当前重点任务
- 飞书群抓取：
```bash
0 */3 * * * cd /home/user/.vectorbrain/intelligence && /opt/homebrew/bin/python3 chat_scraper_v2.py --mode incremental >> /home/user/.vectorbrain/chat_scraper.log 2>&1
```
- 增量向量化：
```bash
*/15 * * * * /home/user/.vectorbrain/.venv-faiss/bin/python /home/user/.vectorbrain/connector/episodic_incremental_vectorizer.py >> /home/user/.vectorbrain/episodic_incremental.log 2>&1
```

### 体检思路
1. 先看 cron 是否存在
2. 再看日志有没有新时间戳
3. 再手动执行一次，确认不是“只有 cron 坏”

---

## 5. 故障排查顺序（推荐）

以后遇到“脚本没跑/没结果”，按这个顺序来：

### 第一步：先看配置文件是不是合法
```bash
python3 -m json.tool ~/.openclaw/openclaw.json >/dev/null && echo OK
```

### 第二步：手动运行一次脚本
直接看现场报错，不猜。

### 第三步：看事件日志有没有 `run_completed`
如果没有，说明不是业务结果问题，是执行链路问题。

### 第四步：确认数据有没有落库
不要只看控制台输出，要看数据库。

### 第五步：再看 cron
cron 是最后看，不是第一步看。
因为很多时候不是 cron 没触发，而是脚本自己启动后炸了。

---

## 6. 今天确认过的结论

### 已确认正常
- `chat_scraper_v2.py` 修复后可正常执行
- 新消息可以写入 `conversations`
- `~/.openclaw/openclaw.json` 当前已修好

### 已确认需加固
- 增量向量化要固定解释器，避免 `faiss` 环境漂移
- 群抓取要保留更清晰的配置文件报错提示
- 旧日志里存在历史 SSL / Feishu 波动，不等于当前故障

---

## 7. 一句话原则

**先验证配置，再手动复现，再看日志，再看落库，最后才看 cron。**

这个顺序最省时间。
