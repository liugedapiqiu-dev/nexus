---
name: ppt-beautifier
description: PowerPoint PPT 美化和自动化处理技能。使用 Python 脚本读取、美化、格式化 PPT 文件。支持一键统一字体/颜色/版式、智能排版、图片批量处理、模板应用、批量导出。Use when working with PowerPoint presentations (.pptx) for: (1) Beautifying slides, (2) Unifying styles, (3) Batch processing, (4) Template application, (5) Export/conversion
metadata:
  {
    "openclaw":
      {
        "emoji": "📊",
        "requires": { "bins": ["python3"], "python_packages": ["python-pptx", "pillow"] },
        "install":
          [
            {
              "id": "ppt-deps",
              "kind": "pip",
              "packages": ["python-pptx", "pillow"],
              "label": "安装 PPT 处理依赖 (pip)",
            },
          ],
      },
  }
---

# PPT 美化技能

使用 Python 脚本自动化处理和美化 PowerPoint (.pptx) 演示文稿。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install python-pptx pillow
```

### 2. 基本用法

**美化 PPT：**
```bash
python scripts/ppt_beautifier.py beautify input.pptx --output beautified.pptx
```

**统一字体：**
```bash
python scripts/ppt_beautifier.py font input.pptx --font "Microsoft YaHei" --size 18
```

**应用模板：**
```bash
python scripts/ppt_beautifier.py template input.pptx --template assets/template.pptx
```

**批量处理：**
```bash
python scripts/ppt_beautifier.py batch folder/ --output output_folder/
```

---

## 📋 脚本命令说明

### ppt_beautifier.py

| 命令 | 说明 | 示例 |
|------|------|------|
| `beautify` | 一键美化（统一风格） | `beautify input.pptx --output out.pptx` |
| `font` | 统一字体和字号 | `font file.pptx --font "Arial" --size 16` |
| `color` | 统一配色方案 | `color file.pptx --primary "#0066CC"` |
| `layout` | 智能排版优化 | `layout file.pptx --align center` |
| `template` | 应用模板 | `template file.pptx --template template.pptx` |
| `image` | 批量处理图片 | `image file.pptx --resize 1920x1080` |
| `batch` | 批量处理文件夹 | `batch folder/ --output out/` |
| `extract` | 提取幻灯片内容 | `extract file.pptx --to json` |
| `merge` | 合并多个 PPT | `merge file1.pptx file2.pptx --output merged.pptx` |
| `export` | 导出为 PDF/图片 | `export file.pptx --format pdf` |

---

## 🎨 美化功能详情

### 一键美化 (beautify)
- 自动统一所有幻灯片字体
- 应用协调的配色方案
- 调整标题和正文层级
- 优化行距和段落间距
- 对齐文本框和元素

### 字体统一 (font)
- 替换所有字体为指定字体
- 支持中英文字体分别设置
- 统一标题和正文字号
- 保持粗体/斜体等样式

### 配色方案 (color)
- 设置主色调
- 自动生成配色方案（主色、辅色、强调色）
- 应用形状、文本、背景颜色

### 智能排版 (layout)
- 居中对齐
- 统一边距
- 调整元素间距
- 优化视觉层次

### 图片处理 (image)
- 批量调整图片尺寸
- 统一图片风格
- 优化图片质量
- 添加边框/阴影

---

## 💡 使用场景

- 📊 **商业报告美化** - 统一公司视觉风格
- 🎓 **学术演示** - 优化可读性和专业度
- 📈 **销售提案** - 提升视觉吸引力
- 📝 **教学课件** - 批量处理多个课件
- 🎯 **会议材料** - 快速统一多个文件风格

---

## 🎯 预设模板

技能包含以下预设模板（位于 `assets/`）：

| 模板 | 用途 | 风格 |
|------|------|------|
| `business.pptx` | 商务报告 | 专业、简洁 |
| `creative.pptx` | 创意展示 | 活泼、现代 |
| `academic.pptx` | 学术演示 | 严谨、清晰 |
| `minimal.pptx` | 极简风格 | 留白、优雅 |

---

## ⚠️ 注意事项

1. **格式支持**：仅支持 .pptx 格式（不支持旧版 .ppt）
2. **字体兼容性**：确保系统已安装目标字体
3. **大文件处理**：超过 50MB 的文件建议分批处理
4. **复杂动画**：部分复杂动画和过渡效果可能无法保留
5. **嵌入对象**：视频、音频等嵌入对象保持不变

---

## 📦 脚本位置

所有脚本位于 `skills/ppt-beautifier/scripts/` 目录。
模板和资源位于 `skills/ppt-beautifier/assets/` 目录。

使用时请确保从技能目录或 workspace 根目录运行。

---

## 🔧 高级用法

### 自定义配色方案
```bash
python scripts/ppt_beautifier.py color input.pptx \
  --primary "#0066CC" \
  --secondary "#00AA88" \
  --accent "#FF6600"
```

### 保留特定元素
```bash
python scripts/ppt_beautifier.py beautify input.pptx \
  --keep-animations \
  --keep-transitions
```

### 生成预览图
```bash
python scripts/ppt_beautifier.py export input.pptx \
  --format png \
  --preview-folder previews/
```

---

## 📚 参考资料

详细 API 文档和高级用法请参阅 `references/pptx-api.md`。
