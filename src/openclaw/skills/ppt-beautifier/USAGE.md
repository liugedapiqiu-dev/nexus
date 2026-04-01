# PPT 美化技能使用指南

## 📦 技能已安装

技能位置：`~/.openclaw/skills/ppt-beautifier/`

## 🚀 快速开始

### 1️⃣ 安装依赖（如果还没安装）

```bash
pip install python-pptx pillow
```

### 2️⃣ 使用示例

#### 一键美化 PPT
```bash
cd ~/.openclaw/skills/ppt-beautifier
python scripts/ppt_beautifier.py beautify 你的文件.pptx -o 美化后.pptx
```

#### 统一字体
```bash
python scripts/ppt_beautifier.py font 你的文件.pptx \
  --font "Microsoft YaHei" \
  -s 18 \
  -o output.pptx
```

#### 应用配色方案
```bash
python scripts/ppt_beautifier.py color 你的文件.pptx \
  --primary "#0066CC" \
  --secondary "#00AA88" \
  --accent "#FF6600" \
  -o output.pptx
```

#### 优化排版
```bash
python scripts/ppt_beautifier.py layout 你的文件.pptx \
  --align center \
  -o output.pptx
```

#### 批量处理整个文件夹
```bash
python scripts/ppt_beautifier.py batch ./ppt 文件夹/ \
  -o ./美化后文件夹/
```

#### 提取 PPT 内容
```bash
python scripts/ppt_beautifier.py extract 你的文件.pptx \
  -o content.json
```

## 🎨 可用命令

| 命令 | 说明 | 常用参数 |
|------|------|----------|
| `beautify` | 一键美化（字体 + 配色 + 排版） | `-o` 输出文件 |
| `font` | 统一字体 | `--font` 字体名，`-s` 字号 |
| `color` | 配色方案 | `--primary` 主色，`--secondary` 辅色，`--accent` 强调色 |
| `layout` | 排版优化 | `--align` 对齐方式 (left/center/right) |
| `template` | 应用模板 | `-t` 模板文件路径 |
| `image` | 图片处理 | `--resize` 尺寸如 1920x1080 |
| `batch` | 批量处理 | `-o` 输出文件夹 |
| `extract` | 提取内容 | `-o` 输出 JSON 文件 |
| `export` | 导出格式 | `-f` 格式 (pdf/png/jpg) |

## 🎯 配色方案推荐

### 商务蓝
```bash
--primary "#0066CC" --secondary "#00AA88" --accent "#FF6600"
```

### 简约灰
```bash
--primary "#333333" --secondary "#666666" --accent "#E74C3C"
```

### 科技蓝紫
```bash
--primary "#6366F1" --secondary "#8B5CF6" --accent "#EC4899"
```

### 清新绿
```bash
--primary "#059669" --secondary "#10B981" --accent "#F59E0B"
```

## ⚠️ 注意事项

1. **格式要求**：仅支持 `.pptx` 格式（不支持旧版 `.ppt`）
2. **字体**：确保系统已安装目标字体（如微软雅黑）
3. **备份**：建议先备份原文件再美化
4. **动画**：复杂动画和过渡效果可能无法保留
5. **大文件**：超过 50MB 的文件建议分批处理

## 📝 完整帮助

```bash
python scripts/ppt_beautifier.py --help
python scripts/ppt_beautifier.py beautify --help
```

## 🔧 故障排除

### 问题：导入错误 `cannot import name 'RGBColor'`
**解决**：确保安装了正确版本的 python-pptx
```bash
pip install --upgrade python-pptx
```

### 问题：中文字体显示异常
**解决**：使用系统已有的中文字体
- macOS: `PingFang SC`, `STHeiti`
- Windows: `Microsoft YaHei`, `SimSun`
- Linux: `WenQuanYi Micro Hei`

### 问题：脚本执行权限
**解决**：添加执行权限
```bash
chmod +x scripts/ppt_beautifier.py
```

---

技能创建时间：2026-03-12
版本：1.0.0
