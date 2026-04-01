# PPT Beautifier 技能

PowerPoint PPT 美化和自动化处理技能。

## 安装

```bash
# 安装依赖
pip install python-pptx pillow
```

## 快速使用

```bash
# 一键美化
python scripts/ppt_beautifier.py beautify input.pptx -o output.pptx

# 统一字体
python scripts/ppt_beautifier.py font file.pptx --font "Microsoft YaHei" -s 18

# 应用配色
python scripts/ppt_beautifier.py color file.pptx --primary "#0066CC"

# 批量处理
python scripts/ppt_beautifier.py batch folder/ -o output/
```

## 所有命令

| 命令 | 说明 |
|------|------|
| `beautify` | 一键美化（统一字体、配色、排版） |
| `font` | 统一字体和字号 |
| `color` | 应用配色方案 |
| `layout` | 优化排版布局 |
| `template` | 应用模板 |
| `image` | 批量处理图片 |
| `batch` | 批量处理文件夹中的 PPT |
| `extract` | 提取幻灯片内容到 JSON |
| `export` | 导出为 PDF/图片 |

## 技能位置

`~/.openclaw/skills/ppt-beautifier/`

## 依赖

- Python 3.x
- python-pptx
- Pillow

## 注意事项

- 仅支持 .pptx 格式
- 确保系统已安装目标字体
- 复杂动画可能无法保留
