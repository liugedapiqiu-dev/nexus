# 自动归档系统 (Auto Archive System)

自动检测并归档旧版本文件，保持工作区整洁

## 触发意图

当用户提到以下需求时调用此技能：

- 归档文件
- 清理旧版本
- 整理文件
- 清理备份
- 版本管理

## 自动触发

- **频率**：每周自动运行一次
- **手动运行**：`python3 auto_archive.py --force`

## 核心功能

| 功能 | 说明 |
|------|------|
| **Dashboard 清理** | 保留最新 2 个 Dashboard 版本，归档旧版 |
| **备份清理** | 归档所有 `.bak` 和 `.backup` 文件 |
| **报告清理** | 归档 30 天前的旧报告 |
| **统一归档** | 归档到 `~/.vectorbrain/archive/` |
| **生成报告** | 生成清理报告并保存到 VectorBrain |

## 文件清理规则

| 文件类型 | 规则 |
|----------|------|
| **Dashboard** | `dashboard*.py` - 保留最新 2 个 |
| **备份文件** | `*.bak`, `*.backup` - 全部归档 |
| **报告** | `*_report_*.md` - 保留 30 天 |

## 归档目录

统一归档到：`~/.vectorbrain/archive/`

## 使用示例

```
归档旧文件
清理 Dashboard 版本
整理备份文件
清理工作区
```

## 注意事项

1. **自动触发**：每周运行一次
2. **安全操作**：移动文件到归档目录，不删除
3. **记录保存**：所有归档记录保存到 VectorBrain
4. **手动运行**：`python3 auto_archive.py --force`

## 相关文件

- 主脚本：`auto_archive.py`
- 技能目录：`~/.openclaw/skills/auto-archive-system/`

## 作者

[YOUR_AI_NAME] 🧠 | 版本：1.0.0 | 创建于：2026-03-10
