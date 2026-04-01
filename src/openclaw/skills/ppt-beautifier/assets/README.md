# PPT 模板说明

本目录用于存放 PPT 模板文件 (.pptx)

## 推荐模板结构

### 商务模板 (business.pptx)
- 封面页
- 目录页
- 章节过渡页
- 内容页（标题 + 正文）
- 图片展示页
- 数据图表页
- 结束页

### 配色建议
- 主色：#0066CC (蓝色)
- 辅色：#00AA88 (青色)
- 强调色：#FF6600 (橙色)
- 背景：#FFFFFF (白色)
- 文字：#333333 (深灰)

### 字体建议
- 中文：微软雅黑 (Microsoft YaHei)
- 英文：Arial 或 Calibri
- 标题：32-40pt
- 正文：18-24pt

## 如何创建模板

1. 在 PowerPoint 中设计母版
2. 设置好字体、配色、布局
3. 保存为 .pptx 文件
4. 放入此目录

## 使用模板

```bash
python scripts/ppt_beautifier.py template input.pptx \
  --template assets/business.pptx \
  --output output.pptx
```

## 预设模板（待添加）

- [ ] business.pptx - 商务风格
- [ ] creative.pptx - 创意风格
- [ ] academic.pptx - 学术风格
- [ ] minimal.pptx - 极简风格

您可以将自己的模板文件放入此目录使用。
