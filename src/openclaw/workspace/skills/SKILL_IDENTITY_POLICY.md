# Skill Identity Policy

Status: adopted in governance v2 A-line  
Purpose: 为技能治理提供一套稳定的命名、别名、目录、状态判定规则。

## 1. Identity Triplet

每个正式技能都应该至少能回答三个问题：

1. **canonical_name 是什么？**
2. **display_name 是什么？**
3. **aliases 有哪些？**

如果这三个问题答不清，这个技能就还没有完成治理收口。

---

## 2. canonical_name

### 定义
规范主名；用于治理、去重、引用、迁移。

### 规则
- 使用 lowercase kebab-case
- 不包含实现语言、目录后缀、大小写展示偏好
- 不随目录迁移而改变
- 一旦确定，不轻易变更

### 好例子
- `todoist`
- `find-skills`
- `mission-control`
- `productivity`
- `schedule`

### 坏例子
- `Todoist`
- `todoist-rs`
- `find-skills-skill`
- `openclaw-mission-control`

这些坏例子不是“不能存在”，而是应该降级到 display_name 或 aliases。

---

## 3. display_name

### 定义
面向人类阅读和展示的名称。

### 可以保留的内容
- 品牌大小写
- 中文名
- 副标题
- 更自然的营销/说明写法

### 示例
- canonical: `mission-control`
- display: `Mission Control — Dashboard for OpenClaw`

---

## 4. aliases

### 定义
所有非 canonical 但仍应被识别的名称。

### 典型来源
- 目录名
- ClawHub slug
- 历史大小写写法
- 仓库实现名
- 旧版名字

### 规则
- aliases 可多值
- aliases 可用于搜索/兼容/映射
- aliases 不能取代 canonical_name

---

## 5. directory_name

目录名只是**当前磁盘落点**，不是治理主名。

允许出现：
- directory_name != canonical_name
- directory_name ∈ aliases

推荐：
- 新技能尽量让 directory_name 与 canonical_name 接近
- 旧技能若已在运行，不为“好看”强行改目录

---

## 6. Status Policy

### active
正式技能，处于主线。

### experimental
仍在探索，尚未稳定。

### deprecated
还存在，但已退出主线。

### disabled
明确不纳入正式可用集合。

### 特别规则
- 伪技能目录默认 `disabled`
- `.disabled` 目录默认 `disabled`
- 同名双版本中，非 authoritative 版本优先考虑 `deprecated`

---

## 7. Pseudo-skill Policy

以下情况按伪技能目录处理：
- 没有 `SKILL.md`
- 只是普通代码仓库
- 只是空目录 / 占位目录
- 无法证明其为当前可调用技能

处置：
- inventory 标 `disabled`
- registry 显式备注 pseudo / non-skill
- 后续迁出 `skills/` 根或补齐标准结构后再评审

---

## 8. Adopted Decisions in This Round

- `find-skills-skill` → canonical `find-skills`
- `todoist-rs` → canonical `todoist`
- `openclaw-mission-control` → canonical `mission-control`
- `Productivity` → canonical `productivity`
- `Schedule` → canonical `schedule`
- `skill-creator` 平台版 `active`，workspace 版 `deprecated`
- `triple-memory-skill.disabled` / `skillguard` / `claw-skill-guard` → `disabled`

---

## 9. Human Review Triggers

出现以下情况时，需要人工确认：
- 同一 canonical_name 出现两个都像主版本的目录
- 需要物理改目录名
- 需要让 deprecated 重新回到 active
- 需要把 pseudo 目录升级成正式技能
- 需要把 nested payload 改造成标准 skill 结构
