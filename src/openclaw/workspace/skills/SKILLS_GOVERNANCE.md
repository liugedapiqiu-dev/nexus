# Skills Governance

Status: governed v0.2  
Scope: OpenClaw 当前 live skill estate 的正式治理基线（命名收口 + 状态落标 + 伪技能目录处置）。  
Non-goal: 本文件**不**直接修改 runtime loader、发现顺序、安装路径或技能源码实现。

## 1. 本轮治理要解决什么

前一轮 inventory / registry 已经证明：当前技能体系的主要问题不是“技能太少”，而是：

1. **命名漂移**：目录名、frontmatter 名、展示名、slug、历史名混在一起。
2. **状态混乱**：active / experimental / disabled 的判定口径不统一，deprecated 基本缺位。
3. **伪技能目录混入**：例如普通 Node 仓库、空占位目录落在 `skills/` 根下，污染正式技能集合。
4. **同名双版本未裁决**：如 `skill-creator` 同时存在平台版与 workspace 版，但没有 authoritative 决定。

本轮治理原则：**先定身份与状态，再谈迁移与自动化**。

---

## 2. 正式身份模型

### 2.1 `canonical_name`

定义：治理层的规范主名。

规则：
- 一律使用 **lowercase kebab-case**。
- 不能直接等同目录名；目录迁移时 canonical_name 应保持稳定。
- 不能混入品牌大小写、实现细节、仓库后缀、目录后缀。

示例：
- `Productivity` → `productivity`
- `Schedule` → `schedule`
- `todoist-rs` → `todoist`
- `openclaw-mission-control` → `mission-control`

### 2.2 `display_name`

定义：面向人类展示的名称。

规则：
- 允许保留品牌大小写、副标题、中英文混排。
- 可与 canonical_name 不同。
- 若同一技能存在多个展示写法，选最稳定、最面向用户的一种作为 display_name。

### 2.3 `aliases`

定义：所有非 canonical 的有效别名集合。

必须放入 aliases 的内容：
- 目录名
- 发布 slug（如 ClawHub slug）
- 历史名 / legacy 名
- 大小写变体
- 仓库实现名

规则：
- aliases 用于检索、兼容、去重；**不用于正式命名裁决**。
- 只要 canonical_name 已知，就不再把 alias 回写成 canonical。

---

## 3. 正式状态机（治理层）

本轮对 inventory 正式使用四档：

- `active`
- `experimental`
- `deprecated`
- `disabled`

### 3.1 含义

#### `active`
当前正式技能，可继续调用、维护、被引用。

#### `experimental`
仍处试验期；结构、触发语义或依赖边界未稳定。

#### `deprecated`
仍保留，但已不再作为主版本继续演进；通常用于：
- 被 authoritative 同名版本替代
- 历史分叉仍需短期保留
- 等待迁出 / 收敛的旧实现

#### `disabled`
明确不进入正式可用集合；常见于：
- `.disabled` 目录
- 旧架构停用物
- 伪技能目录
- 空占位目录

### 3.2 关键规则

1. `deprecated` 不是“还能凑合用的 active”。它表示**治理上已退出主线**。
2. `disabled` 不是“暂时没测”。它表示**显式不纳入正式技能集合**。
3. 伪技能目录不能再用 `experimental` 冒充“未来可能变成技能”。若当前不是技能，就先 `disabled`。

---

## 4. authoritative 规则

当同一 canonical_name 出现多个真实目录时，必须指定：

- 哪个目录是 **authoritative**（正式主版本）
- 哪个目录是历史分叉、镜像、覆写候选或待淘汰版本

裁决优先级（本轮治理建议）：
1. 先看当前运行体系实际依赖与平台分发来源
2. 再看版本成熟度与文档完整度
3. 最后才考虑 workspace 本地副本是否需要保留

没有 authoritative 裁决的同名双版本，视为治理未完成。

---

## 5. 本轮正式裁决

### 5.1 `skill-creator` 双版本

- 平台内置目录：`/home/user/.npm-global/lib/node_modules/openclaw/skills/skill-creator`
  - 状态：`active`
  - 角色：**authoritative**
- workspace 目录：`/home/user/.openclaw/workspace/skills/skill-creator`
  - 状态：`deprecated`
  - 角色：历史分叉 / 本地覆写候选

治理理由：
- 平台版更接近默认分发面。
- workspace 版虽存在，但当前没有足够证据证明其应覆盖平台版。
- 在不改 loader 的前提下，最安全的做法是：**先裁决主版本，再保留本地分叉供人工后续处理**。

### 5.2 `find-skills-skill`

- 正式技能
- `canonical_name = find-skills`
- 目录名 `find-skills-skill` 进入 aliases
- 状态：`active`

治理理由：目录名显然是发布 slug，而不是最稳定的人类主名。

### 5.3 `todoist-rs`

- 正式技能
- `canonical_name = todoist`
- `todoist-rs` 视为实现/仓库别名
- 状态：`active`

治理理由：用户触发语义是 Todoist，不是 Rust 实现细节。

### 5.4 `openclaw-mission-control`

- 正式技能
- `canonical_name = mission-control`
- `openclaw-mission-control` 作为目录/发布 slug 保留到 aliases
- 状态：`active`

治理理由：产品识别重心是 Mission Control，而不是目录前缀。

### 5.5 `triple-memory-skill.disabled`

- `canonical_name = triple-memory`
- 状态：`disabled`
- 定位：legacy memory line

治理理由：其 LanceDB / Git-Notes 路线与当前 VectorBrain 主线冲突；在未定义替代关系前，不能恢复为 active 或 experimental。

### 5.6 `skillguard`

- 非标准技能目录
- 状态：`disabled`
- 定位：普通 Node 仓库 / 伪技能目录

治理理由：缺少标准技能入口，不应占据正式技能名额。

### 5.7 `claw-skill-guard`

- 空占位目录
- 状态：`disabled`
- 定位：placeholder / install residue

治理理由：当前不是技能，也不是可验证的仓库实现。

### 5.8 `Productivity` / `Schedule`

- `canonical_name` 分别收口为 `productivity`、`schedule`
- `display_name` 保留 `Productivity`、`Schedule`
- 状态：`active`

治理理由：frontmatter 大小写属于展示问题，不应污染规范主名。

### 5.9 `gupiaozhushou`

- 父目录：正式技能，`active`
- 子目录 `gupiaozhushou-财经分析工具包`：按 bundled content / nested payload 处理

治理理由：当前结构不够标准，但直接拆解会动到现有实现；先治理“不双计数”，后续再做结构收束。

---

## 6. 伪技能目录处置原则

伪技能目录包括但不限于：
- 缺失 `SKILL.md`
- 实际是普通代码仓库 / 工具仓库
- 空占位目录
- 安装残留目录

正式处置规则：
1. inventory 中标记为 `disabled`
2. registry 中显式登记为 pseudo / non-skill / placeholder 类型说明
3. 不纳入正式技能集合与后续优先治理主线
4. 后续只允许两条路：
   - 迁出 `skills/` 根目录
   - 或补成标准技能后重新评审

---

## 7. 与 registry / inventory 的关系

- `SKILLS_INVENTORY.md`：人类读的正式台账
- `SKILLS_INVENTORY.json`：机器可读台账，补充 aliases / directory_name / manifest_types / governance_notes
- `skills.registry.json`：治理注册表，负责 authoritative / source_origin / compat / rollback / acceptance

三者分工不同，但本轮必须在命名和状态上保持一致。

---

## 8. 本轮仍不做的事

1. 不改 runtime loader
2. 不强制改真实目录名
3. 不大规模改技能源码
4. 不把 registry 直接升格为 runtime source of truth

这是刻意的：先把身份与状态收口，避免“治理文档先把生产系统搞坏”。

---

## 9. 后续建议

1. 为 `skills.registry.json` 增加自动校验脚本：检查 canonical/alias/status 是否一致
2. 将 pseudo 目录逐步迁出 `skills/` 根，减少扫描污染
3. 对 authoritative 双版本冲突建立差异审计清单（从 `skill-creator` 开始）
4. 对 `gupiaozhushou` 一类嵌套目录，后续设计标准化 `references/` / `assets/` 改造方案

---

## 10. 本轮文件交付

本轮已更新/新增：
- `skills/SKILLS_INVENTORY.md`
- `skills/SKILLS_INVENTORY.json`
- `skills/skills.registry.json`
- `skills/SKILLS_GOVERNANCE.md`
- `skills/SKILL_IDENTITY_POLICY.md`
