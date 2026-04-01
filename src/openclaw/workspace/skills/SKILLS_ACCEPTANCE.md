# Skills Acceptance Baseline

> 治理层 v2 · B 线产物  
> 范围：第一批主干技能验收基线（可反复执行）  
> 当前首批覆盖：`vectorbrain-memory-search`、`vectorbrain-connector`、`self-improvement`、`startup-healthcheck`

## 1. 文档目的

这份文档不是一次性审计说明，而是后续可以重复执行的 **acceptance baseline（最小验收基线）**。

它用于回答三件事：

1. 这个技能现在 **应该负责什么**。
2. 这个技能至少要达到什么程度，才能被视为 **可接受 / 可继续迁移 / 可继续保留为主干技能**。
3. 如果失败，如何 **观测、降级、回滚**，而不是让问题静默扩散。

## 2. 设计依据

本基线基于以下真实来源建立，而不是凭概念想象：

- `skills/SKILLS_INVENTORY.md`
- `skills/SKILLS_INVENTORY.json`
- `skills/skills.registry.json`
- 当前机器上真实存在的技能目录与文件：
  - `~/.openclaw/skills/vectorbrain-memory-search`
  - `~/.openclaw/skills/vectorbrain-connector`
  - `~/.openclaw/skills/self-improvement`
  - `~/.openclaw/skills/startup-healthcheck`
- 技能内实际文件：`SKILL.md`、`skill.json`、脚本、模板、说明文件
- 关联真实实现：
  - `~/.vectorbrain/connector/vector_search.py`
  - `~/.vectorbrain/src/memory_manager.py`
  - `~/.openclaw/skills/startup-healthcheck/src/healthcheck.py`

## 3. 使用原则

### 3.1 验收层级

每个技能按三层验收：

- **L1 结构验收**：目录、元数据、入口是否存在且一致。
- **L2 运行验收**：最小命令或最小步骤是否可执行并返回预期类型结果。
- **L3 合同验收**：技能宣称的职责、边界、失败可观测性是否成立。

### 3.2 结果判定

- **PASS**：最小成功标准全部成立。
- **PASS-WITH-GAPS**：核心能力可用，但存在文档/入口/边界不一致，需要登记缺口。
- **FAIL**：核心能力不可用，或技能契约与真实实现严重背离。
- **MANUAL**：必须人工参与，当前无法仅靠静态检查自动确认。

### 3.3 验收原则

- 不批量改源码，不改运行系统。
- 优先做 **只读 / 低风险** 验证。
- 如需写入，必须明确是 **测试写入**，且提供回滚或清理建议。
- 基线优先验证“主干技能是否仍可信”，不是追求覆盖所有高级能力。

## 4. 首批主干技能选择依据

首批 4 个技能之所以先纳入正式 acceptance：

| skill | 原因 |
|---|---|
| `vectorbrain-memory-search` | 已在 AGENTS / TOOLS / IDENTITY 中被提升为默认记忆检索协议，影响最大 |
| `vectorbrain-connector` | 是 OpenClaw ↔ VectorBrain 的桥接面，任何路径/契约漂移都会放大 |
| `self-improvement` | 承担错误沉淀、经验沉淀、行为改进的治理闭环 |
| `startup-healthcheck` | 属于启动时健康可观测面，直接影响“系统是否可感知地就绪” |

## 5. 可扩展规则（下一批怎么接）

后续新增技能进入 acceptance 时，沿用本模板，至少补齐：

1. `registry` 中存在稳定 `id`
2. 明确 `source_path` / `rollback_target`
3. 补齐以下 7 个字段：
   - 职责
   - 前置依赖
   - 最小成功标准
   - 验证命令/步骤
   - 失败信号
   - 回滚/降级建议
   - 后续增强项
4. 至少 1 个 L1 检查 + 1 个 L2 检查 + 1 个 L3 检查
5. 明确哪些检查是自动、哪些必须人工

---

# 6. 首批技能正式验收表

## 6.1 `vectorbrain-memory-search`

**Registry id**: `vectorbrain-memory-search`  
**Inventory 定位**: P0-highest / brain / owner=`vectorbrain`  
**Source path**: `~/.openclaw/skills/vectorbrain-memory-search`  
**Rollback target**: `~/.openclaw/skills/vectorbrain-memory-search`

### 职责

- 为会话提供第一优先级的记忆检索入口。
- 在涉及过去经验、历史决策、身份背景、项目上下文时，提供可复用的检索能力。
- 作为治理契约，声明记忆检索协议应遵循：**knowledge → daily file → episodic**。

### 前置依赖

- `python3`
- `~/.vectorbrain/connector/vector_search.py`
- `~/.vectorbrain/memory/knowledge_memory.db`
- 若启用向量检索增强：
  - `faiss` 可用或可降级
  - `ollama` + `bge-m3` 模型
- 当前运行环境能读取 VectorBrain 目录

### 最小成功标准

1. 技能目录内 `SKILL.md` 与 `skill.json` 存在且可解析。
2. `skill.json.action.command` 仍指向 `python3 ~/.vectorbrain/connector/vector_search.py "{query}"`。
3. 直接执行最小查询时，脚本能返回 **结果集或明确的“未找到”提示**，而不是直接崩溃。
4. 当 `faiss` 不可用时，能降级到 SQLite 文本检索，而不是整体失效。
5. 技能对外契约中，仍明确“记忆检索优先级协议”。

### 验证命令 / 验证步骤

#### L1 结构验收

- 检查文件存在：
  - `~/.openclaw/skills/vectorbrain-memory-search/SKILL.md`
  - `~/.openclaw/skills/vectorbrain-memory-search/skill.json`
- 检查 `skill.json` 可解析，且包含：
  - `name`
  - `memory_protocol.priority_order`
  - `action.command`

#### L2 运行验收

建议命令：

```bash
python3 ~/.vectorbrain/connector/vector_search.py "测试 记忆"
```

通过条件：

- 进程退出码为 0；且
- 输出中满足以下之一：
  - 包含 `找到` / `检索完成` / `Top-` 等结果提示
  - 包含明确的“未找到相关记忆”
  - 包含 fallback 提示并继续返回结果/空结果

#### L3 合同验收

人工核对以下契约是否仍成立：

- `SKILL.md` 与 `skill.json` 都把该技能定位为“核心记忆检索技能”
- 仍声明协议：`knowledge -> daily file -> episodic`
- 若真实实现只覆盖 knowledge 检索，则必须标记为 **PASS-WITH-GAPS**，不能假装完全符合协议

### 当前已发现的失败/缺口信号

- **契约缺口**：`skill.json` 与 `SKILL.md` 都声明检索协议为 `knowledge -> daily file -> episodic`，但当前真实脚本 `~/.vectorbrain/connector/vector_search.py` 主要实现的是 `knowledge_memory.db` 检索，并未在同一入口内显式完成“今日记忆文件 → episodic”全链路。
- **实现偏差**：技能契约比脚本实现更强，属于治理层必须持续追踪的 gap。

### 失败信号

出现任一项即判定 FAIL 或 PASS-WITH-GAPS：

- `skill.json` 无法解析
- 入口命令不存在或路径失效
- 脚本执行直接报错退出
- `faiss` 缺失时没有 fallback
- 协议说明从技能元数据中消失
- 真实实现与协议长期背离且未登记

### 回滚 / 降级建议

- **降级**：允许以当前 `vector_search.py` 作为“knowledge-first 检索入口”继续使用，但必须在治理记录中标注：`protocol partially enforced manually`。
- **回滚**：若后续迁移/改造导致不可用，回滚到当前 registry 指定源目录与当前命令模板，不做路径切换。

### 后续增强项

- 把 `knowledge -> daily file -> episodic` 变成同一入口下可验证的真实执行链
- 为输出增加统一 machine-readable result shape
- 增加 `--backend` / `--dry-run` / `--protocol-check` 验证参数
- 增加针对 fallback 路径的独立 smoke test

### 验收结论建议

- **当前建议状态**：`PASS-WITH-GAPS`
- **人工参与**：需要人工判断“协议是否真实执行”，当前不能仅靠脚本输出自动证明

---

## 6.2 `vectorbrain-connector`

**Registry id**: `vectorbrain-connector`  
**Inventory 定位**: brain / owner=`vectorbrain` / registry=`candidate-migrate`  
**Source path**: `~/.openclaw/skills/vectorbrain-connector`  
**Rollback target**: `~/.openclaw/skills/vectorbrain-connector`

### 职责

- 作为 OpenClaw 与 VectorBrain 的桥接技能。
- 提供记忆读取、记忆写入、反思写入、任务规划等“连接器层”能力说明。
- 为 Brain/Body 边界提供统一入口语义。

### 前置依赖

- `python3`
- `~/.vectorbrain/connector/` 路径存在
- `~/.vectorbrain/src/memory_manager.py`
- VectorBrain 数据库目录存在：
  - `~/.vectorbrain/memory/`
  - `~/.vectorbrain/reflection/`
  - `~/.vectorbrain/tasks/`
  - `~/.vectorbrain/goals/`

### 最小成功标准

1. `SKILL.md` 和 `skill.json` 都存在。
2. 技能至少能证明“**有一个真实可调用的连接面**”，而不是纯说明文档。
3. 技能引用的关键路径存在。
4. 若某些 `skill.json.entry.scripts` 所指文件并不存在，必须判定为 **PASS-WITH-GAPS** 或 **FAIL**，不能直接视为通过。
5. 至少一条“读取类”能力可被低风险验证。

### 验证命令 / 验证步骤

#### L1 结构验收

- 检查存在：
  - `~/.openclaw/skills/vectorbrain-connector/SKILL.md`
  - `~/.openclaw/skills/vectorbrain-connector/skill.json`
- 检查 `skill.json.entry.path == ~/.vectorbrain/connector/`
- 检查以下脚本文件是否存在：
  - `vector_search.py`
  - `memory_reader.py`
  - `reflection_writer.py`
  - `task_planner.py`

#### L2 运行验收

低风险最小验证建议分两步：

**读取面 smoke test：**

```bash
python3 ~/.vectorbrain/connector/vector_search.py "测试"
```

**底层管理器存在性 / 可导入性：**

```bash
python3 - <<'PY'
from pathlib import Path
p = Path.home()/'.vectorbrain'/'src'/'memory_manager.py'
print(p.exists())
PY
```

通过下限：

- 至少存在 1 个真实可调用脚本入口；且
- 连接器依赖路径存在；且
- 不要求在 acceptance 基线中强制做写入测试

#### L3 合同验收

人工核对：

- `SKILL.md` 里写的是“读取记忆 / 写入记忆 / 执行规划 / 机会扫描”
- `skill.json` 里写的是 `vector_search / memory_read / reflection_write / task_plan`
- 若 `memory_reader.py`、`reflection_writer.py`、`task_planner.py` 缺失，则合同并未完全落地

### 当前已发现的失败/缺口信号

- `skill.json` 声明的脚本中，当前只确认 `vector_search.py` 存在。
- `memory_reader.py`、`reflection_writer.py`、`task_planner.py` 当前未在 `~/.vectorbrain/connector/` 下发现。
- `SKILL.md` 中示例命令使用 `~/.vectorbrain/src/memory_manager.py load ...` / `save ...`，但当前 `memory_manager.py` 不具备对应 CLI 参数解析入口，更像 Python 模块而非完备 CLI。

### 失败信号

- `skill.json` 和 `SKILL.md` 任一缺失
- registry 中记录的关键路径消失
- 所有声明入口都不可调用
- 连接器能力全部退化成“文档承诺”而无任何真实运行面
- 路径迁移后未保留 rollback target

### 回滚 / 降级建议

- **降级**：将 `vectorbrain-connector` 视为“桥接契约 + 部分可调用实现”，只把已证实存在的 `vector_search.py` 计入可用面，其余能力标记待补齐。
- **回滚**：保持 registry 的 `source_path` 不变，不进行 mirror cutover；如后续改造失败，以当前 `.openclaw/skills/vectorbrain-connector` 描述面作为稳定锚点。

### 后续增强项

- 补齐 `skill.json` 所声明但缺失的脚本
- 或者把 `skill.json` 收敛为真实存在的入口，不再超卖能力
- 为 `memory_manager.py` 增加正式 CLI，统一 `load/save/search/stats`
- 增加只读 `connector doctor` / `connector check` 命令

### 验收结论建议

- **当前建议状态**：`PASS-WITH-GAPS`（偏弱）
- 若要求“entry scripts 必须全部真实存在”则应判定 **FAIL**
- **人工参与**：需要人工决定是修 contract 还是补实现

---

## 6.3 `self-improvement`

**Registry id**: `self-improvement`  
**Inventory 定位**: brain / owner=`shared`  
**Source path**: `~/.openclaw/skills/self-improvement`  
**Rollback target**: `~/.openclaw/skills/self-improvement`

### 职责

- 记录错误、教训、知识缺口、最佳实践、功能请求。
- 形成从一次性问题到长期规则的治理闭环。
- 提供从 `.learnings/*` 向 `AGENTS.md` / `TOOLS.md` / `SOUL.md` 等长期记忆的 promotion 规则。

### 前置依赖

- 技能目录内以下文件存在：
  - `SKILL.md`
  - `skill.json`
  - `.learnings/LEARNINGS.md`
  - `.learnings/ERRORS.md`
  - `.learnings/FEATURE_REQUESTS.md`
- 脚本存在：
  - `scripts/activator.sh`
  - `scripts/error-detector.sh`
  - `scripts/extract-skill.sh`
- 若在 OpenClaw workspace 中实际使用，还需要：
  - `~/.openclaw/workspace/.learnings/`

### 最小成功标准

1. 技能定义了三类核心日志目标：`ERRORS` / `LEARNINGS` / `FEATURE_REQUESTS`。
2. `skill.json` 中的 entry 路径与 `SKILL.md` 中的说明一致，不出现语义冲突。
3. 至少一条 hook 或 helper 脚本存在且内容可读。
4. promotion 规则清晰，能说明何时写回 `AGENTS.md` / `TOOLS.md` / `SOUL.md`。
5. 不要求 acceptance 阶段真实追加写入日志，但必须能证明写入目标明确且格式稳定。

### 验证命令 / 验证步骤

#### L1 结构验收

检查存在：

- `~/.openclaw/skills/self-improvement/SKILL.md`
- `~/.openclaw/skills/self-improvement/skill.json`
- `~/.openclaw/skills/self-improvement/.learnings/LEARNINGS.md`
- `~/.openclaw/skills/self-improvement/.learnings/ERRORS.md`
- `~/.openclaw/skills/self-improvement/.learnings/FEATURE_REQUESTS.md`
- `~/.openclaw/skills/self-improvement/scripts/activator.sh`
- `~/.openclaw/skills/self-improvement/scripts/error-detector.sh`
- `~/.openclaw/skills/self-improvement/scripts/extract-skill.sh`

#### L2 运行验收

低风险验证建议：

```bash
bash ~/.openclaw/skills/self-improvement/scripts/activator.sh
bash ~/.openclaw/skills/self-improvement/scripts/error-detector.sh
bash ~/.openclaw/skills/self-improvement/scripts/extract-skill.sh demo-skill --dry-run
```

通过条件：

- 脚本能输出提醒 / dry-run 结果
- 不要求真的写文件
- `extract-skill.sh` 必须拒绝危险路径（当前脚本已包含相对路径限制）

#### L3 合同验收

人工核对：

- `skill.json.entry.paths.*` 是否仍与三类日志文件一致
- promotion 规则是否仍明确指向 `AGENTS.md` / `TOOLS.md` / `SOUL.md`
- OpenClaw 使用场景中，技能目录自带 `.learnings/` 与 workspace 级 `.learnings/` 是否边界清晰

### 当前已发现的失败/缺口信号

- 技能目录下自带 `.learnings/*` 模板文件，但 `SKILL.md` 又推荐在 `~/.openclaw/workspace/.learnings/` 中实际使用，存在“模板位置”和“运行位置”双层语义。
- 这是可接受的，但治理上需要明确：**技能目录内 `.learnings` 是模板/示例，workspace `.learnings` 才是实际运行数据面**。若不声明，后续容易混淆。

### 失败信号

- 三类日志路径任一缺失
- 记录格式被破坏到不可继续追加
- hook/helper 脚本全部失效
- promotion 规则从技能文档中消失
- 误把技能内模板日志当成 workspace 实际日志面

### 回滚 / 降级建议

- **降级**：即使 hook 未启用，也允许保留为“手动记录模式”，前提是日志模板和写入格式仍稳定。
- **回滚**：如未来重构导致脚本失效，至少保留 `.learnings` 三件套与 markdown logging format，不破坏历史积累。

### 后续增强项

- 明确“模板日志”与“运行日志”边界
- 增加一个只读 doctor/check 命令，验证 `.learnings` 完整性
- 为 `extract-skill.sh` 增加 acceptance 自检输出
- 将 promotion 流程抽成 machine-readable policy

### 验收结论建议

- **当前建议状态**：`PASS-WITH-GAPS`
- **人工参与**：需要人工确认实际日志面使用的是 workspace 还是技能目录模板

---

## 6.4 `startup-healthcheck`

**Registry id**: `startup-healthcheck`  
**Inventory 定位**: platform / owner=`shared` / registry=`candidate-migrate`  
**Source path**: `~/.openclaw/skills/startup-healthcheck`  
**Rollback target**: `~/.openclaw/skills/startup-healthcheck`

### 职责

- 在 OpenClaw 启动后汇报系统最基本健康信息。
- 关注 VectorBrain、记忆库计数、Gateway 端口、Feishu 配置、技能数量等信号。
- 作为“启动后是否就绪”的最低可观测面，而非自动修复器。

### 前置依赖

- `python3`
- `sqlite3`（Python 模块）
- `pgrep`
- `lsof`
- `openclaw` CLI（用于发送报告）
- `~/.openclaw/skills/startup-healthcheck/src/healthcheck.py`
- 如需启动自动触发，还需要 hook 或启动流程集成

### 最小成功标准

1. 技能目录中 `SKILL.md`、`skill.json`、`src/healthcheck.py` 存在。
2. 运行脚本时，至少能生成一份文本报告；即使发送失败，也会 fallback 到 stdout。
3. 检查是 **read-mostly**，默认不修改系统状态。
4. 报告至少覆盖：
   - OpenClaw 进程
   - VectorBrain 进程
   - episodic / knowledge 计数
   - 网关端口
5. 若技能元数据入口与真实脚本不一致，必须记为缺口。

### 验证命令 / 验证步骤

#### L1 结构验收

检查存在：

- `~/.openclaw/skills/startup-healthcheck/SKILL.md`
- `~/.openclaw/skills/startup-healthcheck/skill.json`
- `~/.openclaw/skills/startup-healthcheck/src/healthcheck.py`
- `~/.openclaw/skills/startup-healthcheck/README.md`

并核对：

- `skill.json.entry.main`
- `SKILL.md` 中的调用方式
- 真实脚本文件名

#### L2 运行验收

建议命令：

```bash
python3 ~/.openclaw/skills/startup-healthcheck/src/healthcheck.py
```

通过条件：

- 能打印 `OpenClaw 启动自检中` / 报告内容 / `自检完成`
- 若 `openclaw send` 失败，仍能在 stdout 看到报告
- 不因缺少单一检查项就直接崩溃

#### L3 合同验收

人工核对：

- 自检脚本默认只做检查，不进行系统修复
- 报告目的地是否清晰（当前主要是 `openclaw send`，失败则 stdout）
- 启动挂钩方式是否只是建议集成，而不是强耦合修改系统

### 当前已发现的失败/缺口信号

- `skill.json.entry.main` 当前写的是 `healthcheck.sh`，但真实存在的主执行文件是 `src/healthcheck.py`。
- 这属于 **入口元数据与真实实现不一致** 的显式缺口。
- `README.md` 中还建议修改平台启动入口或 service 配置，这部分不应作为 acceptance 必选项，只能视为集成方案参考。

### 失败信号

- 入口元数据与真实脚本不一致且长期未登记
- 脚本无法生成报告
- 报告完全依赖消息发送，发送失败时没有 fallback
- 检查逻辑开始隐式修改系统状态
- 关键检查项（进程/DB/端口）被删掉而没有替代说明

### 回滚 / 降级建议

- **降级**：即使自动触发未接入，也允许保留为“手动健康检查脚本”，只要 `src/healthcheck.py` 仍可独立执行。
- **回滚**：如未来入口重构失败，回滚到直接执行 `python3 .../src/healthcheck.py` 的最小模式，不依赖 `skill.json.entry.main`。

### 后续增强项

- 统一 `skill.json` 入口到真实脚本
- 增加 `--stdout-only` / `--no-send` / `--json` 模式
- 明确 gateway / channel 检查的超时与失败等级
- 让报告格式既适合人读，也适合机器消费

### 验收结论建议

- **当前建议状态**：`PASS-WITH-GAPS`
- **人工参与**：需要人工确认是否真的接入启动流程；该项不应靠静态文档推断

---

# 7. 首批技能共性缺口

本轮验收基线发现的共性问题：

1. **技能契约强于真实实现**
   - 典型：`vectorbrain-memory-search`
2. **skill.json 入口与真实文件不完全一致**
   - 典型：`startup-healthcheck`
3. **skill.json 声明的脚本并未全部存在**
   - 典型：`vectorbrain-connector`
4. **模板数据面与运行数据面可能混淆**
   - 典型：`self-improvement`

治理建议：后续不要只看 `SKILL.md`/`skill.json` 是否“写得好看”，必须把 **声明、真实入口、可执行面、失败观测** 四件事绑在一起。

# 8. 机器可读基线的使用规则

配套文件：`skills/skills.acceptance.baseline.json`

用途：

- 作为 registry 的 acceptance 草案索引
- 允许后续脚本化检查 L1/L2 项
- 对 L3 / MANUAL 项保留人工判定字段

建议规则：

- `registry_id` 必须与 `skills.registry.json` 的 `entries[].id` 对齐
- `status_hint` 只表示当前基线建议，不自动改 registry 生命周期状态
- `manual_checks` 不得被自动化脚本擅自判 PASS

## 6.5 `desktop-control`（RGA 消息发送安全基线）

**Registry id**: `desktop-control`  
**Inventory 定位**: body / automation  
**Source path**: `/home/user/.openclaw/skills/desktop-control`  
**Spec path**: `skills/desktop-control/RGA_MESSAGE_SAFETY_SPEC.md`  
**Machine-readable draft**: `skills/desktop-control/desktop-control.rga.acceptance.json`

### 职责

- 提供桌面控制能力（鼠标、键盘、截图、窗口操作）
- 对高风险桌面任务，尤其是消息发送类任务，引入 RGA：执行一步 → 快速识别 → 确认 → 再继续
- 明确“动作已执行”不等于“结果已验证”

### 当前建议验收结论

- **当前建议状态**：`PASS-WITH-GAPS`（基础执行面存在，但高风险验证门仍需补齐）
- **核心 gap**：OCR/文本回读标准接口、确认门强制化、发送后验证、任务级状态机与证据结构

### 核心验收原则

1. 消息发送类任务必须包含：`VERIFY_TARGET`、`VERIFY_DRAFT`、`PRE_SEND_CONFIRM`、`VERIFY_SENT`
2. 目标不明确时必须中止，不允许猜测继续
3. 内容未确认时不得发送
4. 发送结果不明时不得自动再发一次
5. 最终 success 必须表示“已验证发送成功”，而不是“已按下发送键”

# 9. 当前仍需人工参与的检查

以下检查当前不能仅靠静态或单条命令自动完成，必须人工参与：

1. `vectorbrain-memory-search` 是否真的执行了 `knowledge -> daily file -> episodic` 全协议
2. `vectorbrain-connector` 应该补实现还是收缩契约
3. `self-improvement` 的实际运行日志面到底以 workspace 为准还是技能目录模板为准
4. `startup-healthcheck` 是否真的接入启动流程，以及是否要继续允许多种集成方式并存

# 10. 建议的后续动作（不在本次直接执行）

1. 将本基线作为治理层 v2 的正式 acceptance 起点
2. 后续把 L1/L2 中低风险项逐步脚本化
3. 对首批 4 个技能分别开 gap 修复任务：
   - memory-search：协议落地
   - connector：入口收敛或补齐脚本
   - self-improvement：模板/运行边界明确
   - startup-healthcheck：入口元数据统一
4. 选定第二批技能时，优先从 `brain-health-monitor`、`memory-extraction-engine`、`auto-reflection-engine`、`auto-archive-system`、`knowledge-dedup` 中挑选
