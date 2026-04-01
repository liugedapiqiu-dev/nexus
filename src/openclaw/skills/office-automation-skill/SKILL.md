# Office Automation Skill

Office 自动化技能 - 处理 Word 和 Excel 文件

## 触发意图

当用户提到以下需求时调用此技能：

- 处理 Excel / 处理 Word
- 读取 Excel / 读取 Word
- 写入 Excel / 写入 Word
- 合并 Excel 文件
- 转换 Excel 格式
- Excel 数据分析
- 批量生成文档
- 填充 Word 模板
- 提取表格数据

## 功能列表

### Excel 处理

| 功能 | 命令 | 说明 |
|------|------|------|
| 读取 | `excel_read` | 读取 Excel 文件内容 |
| 写入 | `excel_write` | 写入数据到 Excel |
| 合并 | `excel_merge` | 合并多个 Excel 文件 |
| 转换 | `excel_convert` | Excel 转 CSV 等格式 |
| 分析 | `excel_analyze` | 数据分析统计 |

### Word 处理

| 功能 | 命令 | 说明 |
|------|------|------|
| 读取 | `word_read` | 读取 Word 文档内容 |
| 写入 | `word_write` | 写入 Word 文档 |
| 模板填充 | `word_template` | 用数据填充模板 |
| 内容提取 | `word_extract` | 提取文档内容 |

## 使用示例

```
读取 data.xlsx 的内容
合并 reports 文件夹中的所有 Excel 文件
将 sales.xlsx 转换为 CSV
分析 sales.xlsx 的销售数据
用 data.json 填充 contract.docx 模板
```

## 依赖要求

需要安装以下 Python 包：
- `python-docx` - Word 处理
- `openpyxl` - Excel 处理
- `pandas` - 数据分析

## 注意事项

1. 大文件处理可能需要较长时间
2. 合并 Excel 时确保格式一致
3. 模板填充需要 JSON 格式数据
4. 支持 .xlsx 和 .docx 格式

## 相关文件

- 脚本目录：`~/.openclaw/skills/office-automation-skill/scripts/`
- Excel 处理器：`excel_processor.py`
- Word 处理器：`word_processor.py`
