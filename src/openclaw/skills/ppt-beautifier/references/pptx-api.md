# python-pptx API 参考

## 核心对象

### Presentation
```python
from pptx import Presentation

# 打开现有 PPT
prs = Presentation('input.pptx')

# 创建新 PPT
prs = Presentation()

# 保存
prs.save('output.pptx')
```

### Slide
```python
# 获取幻灯片
slide = prs.slides[0]

# 添加幻灯片
slide = prs.slides.add_slide(prs.slide_layouts[0])

# 遍历所有幻灯片
for slide in prs.slides:
    # 处理每张幻灯片
    pass
```

### Shape
```python
# 遍历形状
for shape in slide.shapes:
    # 获取形状类型
    shape_type = shape.shape_type
    
    # 获取文本
    if hasattr(shape, "text_frame"):
        text = shape.text_frame.text
    
    # 获取图片
    if shape.shape_type == MSO_SHAPE.PICTURE:
        image = shape.image
```

### TextFrame 和 Paragraph
```python
# 获取文本框
text_frame = shape.text_frame

# 遍历段落
for paragraph in text_frame.paragraphs:
    # 设置对齐
    paragraph.alignment = PP_ALIGN.CENTER
    
    # 设置行距
    paragraph.space_after = Pt(12)
    
    # 遍历文本运行
    for run in paragraph.runs:
        run.font.name = "Arial"
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = RgbColor(0, 102, 204)
```

## 常用枚举

```python
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# 对齐方式
PP_ALIGN.LEFT
PP_ALIGN.CENTER
PP_ALIGN.RIGHT
PP_ALIGN.JUSTIFY

# 形状类型
MSO_SHAPE.RECTANGLE
MSO_SHAPE.ROUNDED_RECTANGLE
MSO_SHAPE.OVAL
MSO_SHAPE.PICTURE
```

## 颜色处理

```python
from pptx.dml.color import RgbColor

# RGB 颜色
color = RgbColor(255, 0, 0)  # 红色

# 从十六进制转换
hex_color = "#FF0000"
rgb = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
color = RgbColor(*rgb)
```

## 单位转换

```python
from pptx.util import Inches, Pt, Cm

# 英寸
width = Inches(10)

# 磅（字体大小）
font_size = Pt(18)

# 厘米
margin = Cm(2.5)
```

## 常用操作示例

### 添加文本框
```python
left = top = width = height = Inches(1)
textbox = slide.shapes.add_textbox(left, top, width, height)
text_frame = textbox.text_frame
text_frame.text = "Hello World"
```

### 添加图片
```python
slide.shapes.add_picture('image.jpg', Inches(1), Inches(1), width=Inches(5))
```

### 添加形状
```python
shape = slide.shapes.add_shape(
    MSO_SHAPE.ROUNDED_RECTANGLE,
    Inches(1), Inches(1), Inches(3), Inches(1)
)
shape.fill.solid()
shape.fill.fore_color.rgb = RgbColor(0, 102, 204)
```

### 添加表格
```python
rows = cols = 3
left = top = Inches(2)
width = Inches(6)
height = Inches(2)

table = slide.shapes.add_table(rows, cols, left, top, width, height).table
table.cell(0, 0).text = 'Header 1'
```

## 注意事项

1. **字体名称**：使用系统已安装的字体名称
2. **图片格式**：支持 JPG、PNG、GIF 等常见格式
3. **文件大小**：大文件建议分批处理
4. **兼容性**：生成的 PPTX 兼容 PowerPoint 2007+
5. **动画和过渡**：部分复杂动画可能无法保留

## 常见问题

### Q: 如何修改母版？
```python
master = prs.slide_master
for layout in master.slide_layouts:
    # 修改布局
    pass
```

### Q: 如何提取所有图片？
```python
for shape in slide.shapes:
    if shape.shape_type == MSO_SHAPE.PICTURE:
        image = shape.image
        with open(f'image_{i}.png', 'wb') as f:
            f.write(image.blob)
```

### Q: 如何设置背景色？
```python
background = slide.background
fill = background.fill
fill.solid()
fill.fore_color.rgb = RgbColor(240, 240, 240)
```

## 参考资料

- 官方文档：https://python-pptx.readthedocs.io/
- GitHub: https://github.com/scanny/python-pptx
- PyPI: https://pypi.org/project/python-pptx/
