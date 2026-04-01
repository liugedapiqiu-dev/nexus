# desktop-control v2 / B 线：OCR 与文字确认链

## 本次交付

基于 `~/.openclaw/skills/desktop-control/__init__.py` 与 `verification_demo.py`，为 desktop-control 的 verification 接口补上了真正可用的文字读取 / 文本确认能力，重点围绕 Feishu / Lark 消息发送前后的低风险确认场景。

## 改动文件

1. `~/.openclaw/skills/desktop-control/__init__.py`
2. `~/.openclaw/skills/desktop-control/verification_demo.py`
3. `workspace/skills/desktop-control/TEXT_VERIFICATION_NOTES.md`（本说明）

## 接口变化

### 1) `extract_text()` 扩展

原先：
- 只能尝试 OCR
- OCR 不可用时仅返回 unavailable

现在：
- 支持多来源文字提取：
  - `source='window_title'`：读取前台窗口标题 / app 名
  - `source='clipboard'`：读取当前剪贴板文本
  - `source='ocr'`：对截图或局部截图跑 OCR
  - `source='auto'`：无 region/image 时优先 `window_title`，否则优先 `ocr`
  - `source='window_title_or_ocr'`
  - `source='clipboard_or_ocr'`
- 返回结构中包含：
  - `source`
  - `attempted_sources`
  - `engine`
  - `text`
  - `image_path` / `ocr_image_path`（OCR 时）
  - `preprocessed`
  - `status` / `reason`

### 2) `verify_text_present()` 扩展

新增参数：
- `source='auto'`
- `contains=True`
- `collapse_whitespace=True`
- `prefer_preprocess=True`
- `psm=None`

行为：
- 统一走 `extract_text()`
- 做规范化匹配（大小写 / 空白折叠）
- 可用于：
  - 前台窗口标题确认
  - 输入框文本确认
  - 局部截图文本确认

### 3) 新增 `verify_input_text()`

用途：
- 为 Feishu / Lark 发消息前做“聚焦输入框内容确认”
- 默认走 `clipboard_or_ocr` 链路
- 默认 `contains=False`，更适合发送前做精确匹配

说明：
- 这是确认接口，不主动做高风险发送动作
- 适合搭配外层流程：手动全选复制 / 自动低风险复制，再校验是否与预期一致

### 4) 新增内部辅助方法

- `_normalize_text()`：统一文本归一化
- `_prepare_image_for_ocr()`：灰度、增强对比度、二值化、放大，提升 OCR 可读性
- `_extract_window_title_text()`：读取前台窗口标题 / app 名
- `_extract_clipboard_text()`：读取剪贴板文本

## 当前验证方式

### A. 前台窗口标题确认

```python
res = dc.verify_text_present('Feishu', source='window_title')
```

适用：
- 确认当前是不是 Feishu / Lark 窗口
- 发消息前先挡一道 app / 窗口级 gate

### B. 输入框文本确认

```python
res = dc.verify_input_text('你好，已收到，明天跟进。')
```

建议流程：
1. 聚焦输入框
2. 手动或脚本执行复制当前输入框文本到剪贴板
3. 调用 `verify_input_text()`
4. 仅在匹配通过后，才进入下一步发送决策

### C. 局部截图文字确认

```python
res = dc.verify_text_present(
    '已发送',
    source='ocr',
    region=(x, y, w, h),
    lang='eng',
    contains=True,
    psm=6,
)
```

适用：
- 发送后确认 toast / 气泡 / 局部消息内容
- 对指定区域做 OCR，降低全屏噪音

## Feishu / Lark 场景建议链路

### 发送前（低风险）

1. `verify_text_present('Feishu' 或 'Lark', source='window_title')`
2. `verify_input_text(expected_message, contains=False)`
3. 如有必要，再对发送按钮附近做 `verify_image_present()` 或局部 OCR
4. **不要在未通过确认时触发 Enter / 点击发送**

### 发送后（低风险观察）

1. 对消息气泡区域截图
2. `verify_text_present(expected_message_fragment, source='ocr', region=...)`
3. 或验证“已发送 / Delivered / Seen”等局部状态文案

## 运行验证

执行：

```bash
cd /home/user/.openclaw/skills/desktop-control
./.venv/bin/python verification_demo.py
```

本次环境实际观察到：
- `pyautogui` 可用
- 本地 OCR **可用**
- `tesseract` 路径：`/opt/homebrew/bin/tesseract`

因此当前 demo 已验证：
- 窗口标题读取可用
- 剪贴板读取可用
- OCR 全屏提取可用
- `verify_text_present(source='ocr')` 已能跑通

同时也暴露出一个现实边界：
- **全屏 OCR 容易有噪音**，更适合对 Feishu / Lark 的局部区域做验证，而不是直接拿全屏结果做强判定

## 当前能力边界

1. **OCR 依赖 tesseract 本地二进制**
   - 当前环境已经具备 `tesseract`
   - 但 OCR 的稳定性仍然强依赖截图区域、字体大小、界面缩放与语言包

2. **输入框文本确认目前优先依赖剪贴板**
   - 若目标应用不允许稳定复制输入框内容，则会回退到 OCR
   - 在 OCR 不可用时，输入框确认能力会受限

3. **窗口标题只适合 app / 页面级确认**
   - 不能替代消息正文确认
   - 适合作为第一道 gate，不适合作为唯一 gate

4. **OCR 目前未做语言包探测**
   - 接口有 `lang` 参数
   - 但未进一步判断本机是否安装了 `chi_sim` 等语言数据

5. **未接入可访问性树 / 原生 UI 文本 API**
   - 当前仍以 window title / clipboard / OCR 为主
   - 对复杂输入框、富文本控件、虚拟列表仍有 gap

## 剩余 gap

1. 安装并探测 tesseract + 语言包
   - 至少补英文 + 中文探测
   - 最好将 `get_ocr_status()` 扩展到语言可用性检查

2. 为 Feishu / Lark 补“局部区域模板”
   - 输入框区域
   - 已发送气泡区域
   - 发送按钮 / 会话头部区域

3. 加一层“安全发送前总闸”
   - app/window gate
   - draft/input gate
   - optional recipient gate
   - 通过后才允许外层发送动作

4. 如果后续允许更深实现，可考虑：
   - macOS Accessibility API 读取焦点输入框值
   - 对 Feishu 原生客户端做更稳定的 UI 文本读取

## 结论

这次 B 线已经把文字确认链从“只有占位 OCR 接口”推进到“可正式调用的统一 verification 接口”：
- 前台窗口标题可读
- 输入框文本确认有 clipboard-first 链路
- 局部截图 OCR 接口已接好
- OCR 可用时直接提取，不可用时也有明确降级结构
- demo 与文档已围绕 Feishu / Lark 的安全确认点收口

当前已经具备最小可用能力；若要进入高可靠消息后验证，下一步重点不是“有没有 OCR”，而是“把 Feishu / Lark 的验证区域模板化、收窄化、稳定化”。