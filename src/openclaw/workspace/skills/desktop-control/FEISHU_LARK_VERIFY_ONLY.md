# Feishu / Lark VERIFY_ONLY 局部确认链（desktop-control v3 / B 线）

日期：2026-03-21  
工作区：`/home/user/.openclaw/workspace`

目标：在现有 `RGA_MESSAGE_SAFETY_SPEC`、`desktop-control` verification 接口基础上，把 Feishu / Lark 的 `VERIFY_TARGET` / `VERIFY_DRAFT` / `VERIFY_SENT` 从“最小可用”推进到更接近实战的**局部确认链**。重点不是全屏盲读，而是：

- 局部区域 OCR
- 窗口标题
- 剪贴板
- 模板匹配
- 多信号汇总证据

**硬边界：不默认真实发送。本文只定义 verify-only / pre-send-safe / post-send-observe 方案。**

---

## 1. 本次改动文件

### 代码
1. `~/.openclaw/skills/desktop-control/__init__.py`
2. `~/.openclaw/skills/desktop-control/verification_demo.py`

### 文档
3. `workspace/skills/desktop-control/FEISHU_LARK_VERIFY_ONLY.md`（本文）

---

## 2. 新增能力摘要

在 `DesktopController` 中新增 Feishu/Lark 专用 verify-only helper：

- `verify_feishu_lark_target(...)`
- `verify_feishu_lark_draft(...)`
- `verify_feishu_lark_sent(...)`

并新增统一信号/证据聚合层：

- `_build_signal(...)`
- `_finalize_signal_set(...)`

这层的目的：
- 把窗口标题、OCR、剪贴板等异构证据统一成机器可读结构
- 明确 `passed / failed / unknown / needs_review`
- 明确每一步**靠什么证据**判定，而不是只返回一个布尔值

---

## 3. 设计原则

### 3.1 区域优先，不做全屏强判

Feishu / Lark 的风险不在“有没有 OCR”，而在：
- 全屏文字太多，噪音极高
- 相似聊天列表很多
- 同名联系人/群聊容易误判
- 发送后历史区滚动、输入框清空、回执文案都可能滞后

所以默认策略：
- **头部区域**确认目标身份
- **侧栏/选中会话区域**确认目标对象
- **输入框区域**确认草稿
- **消息历史最后一屏区域**观察是否出现消息

### 3.2 多信号，而不是单点成功

`VERIFY_TARGET` 需要至少两类证据一致：
- window_title
- header OCR
- sidebar OCR
- 可选 disambiguation OCR（职位/备注/群类型）

`VERIFY_DRAFT` 至少需要一类可靠回读：
- clipboard exact/normalized readback
- composer OCR

`VERIFY_SENT` 默认保守：
- history match 成功 → 可判 passed
- 仅 composer 清空但没看到历史消息 → 只能 `unknown`
- 不能因为“看不清”就假设已经发出

### 3.3 发送动作与效果验证分离

这次只补确认链，不补真实发送默认路径。

即使未来接上 `SEND_ACTION`，也必须维持：
- `SEND_ACTION` = 触发动作
- `VERIFY_SENT` = 观察结果

不能把“按了发送键”当成“消息已验证发出”。

---

## 4. 三段确认链

---

### A. `VERIFY_TARGET`

接口：

```python
verify_feishu_lark_target(
    expected_name: str,
    expected_type: Optional[str] = None,
    disambiguation_hint: Optional[str] = None,
    window_title_hint: Optional[str] = None,
    header_region: Optional[Tuple[int, int, int, int]] = None,
    sidebar_region: Optional[Tuple[int, int, int, int]] = None,
    lang: str = 'chi_sim+eng',
)
```

#### 依赖证据

1. **window_title**
   - 来源：`extract_text(source='window_title')`
   - 作用：确认当前确实在 Feishu / Lark 窗口，或窗口标题包含预期 app hint
   - 只能做 app / 页面级 gate，不能独立证明 target 正确

2. **header_match**
   - 来源：头部局部区域 OCR
   - 作用：读取聊天头部名字 / 群名 / 标签
   - 是最重要的目标证据之一

3. **header_disambiguation**
   - 来源：头部局部区域 OCR
   - 作用：读取职位、备注、附加标签，例如“供应链主管”
   - 用来解决重名人/群

4. **sidebar_match**
   - 来源：侧栏选中会话局部 OCR
   - 作用：确认左侧当前选中项与头部一致
   - 作为第二信号，防止只靠头部单点误判

#### 通过规则

- 至少 **2 个 signal = passed** → `status=passed`
- 否则：
  - 有硬错误 → `failed`
  - 证据不足 → `unknown` 或 `failed`

#### 推荐判定逻辑

**强通过：**
- header_match + sidebar_match
- header_match + header_disambiguation
- window_title + header_match（仅适合作为次优，不能用于高度歧义对象）

#### 失败分类

- `window_title_mismatch`
- `header_target_missing`
- `header_disambiguation_missing`
- `sidebar_target_missing`
- `header_region_missing`
- `sidebar_region_missing`

#### 典型实战用法

```python
res = dc.verify_feishu_lark_target(
    expected_name='[YOUR_NAME]',
    expected_type='person',
    disambiguation_hint='供应链主管',
    window_title_hint='Feishu',
    header_region=(920, 82, 420, 72),
    sidebar_region=(120, 150, 280, 560),
)
```

---

### B. `VERIFY_DRAFT`

接口：

```python
verify_feishu_lark_draft(
    expected_text: str,
    composer_region: Optional[Tuple[int, int, int, int]] = None,
    lang: str = 'chi_sim+eng',
    compare_mode: str = 'normalized',
)
```

#### 依赖证据

1. **clipboard_readback**
   - 来源：`extract_text(source='clipboard')`
   - 作用：如果外层已经做了“低风险复制当前输入框内容”，这是最强回读证据
   - 优点：比 OCR 更稳定，尤其对中文、长文本、富文本轻差异

2. **composer_ocr**
   - 来源：输入框局部 OCR
   - 作用：当剪贴板不可靠时，作为局部视觉回读
   - 适合辅助确认，不适合在极复杂富文本场景做唯一强判

#### 通过规则

- `clipboard_readback` 或 `composer_ocr` 任一通过，即可 `passed`
- 但生产上建议优先追求：
  - clipboard exact/normalized passed
  - OCR 作为辅助交叉验证

#### 失败分类

- `draft_empty`
- `draft_mismatch`
- `draft_unreadable`
- 聚合后映射为：
  - `draft_empty`
  - `draft_unreadable`
  - `draft_corrupted`

#### 为什么把剪贴板放第一位

因为 Feishu / Lark 输入框常见问题是：
- 中文输入法候选未上屏
- 部分文本未进入 composer
- 粘贴成功但 OCR 读不全
- 富文本样式影响视觉判读

而“手动/脚本执行复制当前输入框文本 → 再回读剪贴板”通常比 OCR 稳得多。

#### 典型实战用法

```python
res = dc.verify_feishu_lark_draft(
    expected_text='你好，已收到。明天我再跟进。',
    composer_region=(430, 820, 1100, 210),
    compare_mode='normalized',
)
```

---

### C. `VERIFY_SENT`

接口：

```python
verify_feishu_lark_sent(
    expected_text: str,
    history_region: Optional[Tuple[int, int, int, int]] = None,
    composer_region: Optional[Tuple[int, int, int, int]] = None,
    lang: str = 'chi_sim+eng',
    match_fragment: Optional[str] = None,
)
```

#### 依赖证据

1. **history_match**
   - 来源：消息历史区域局部 OCR
   - 作用：观察最后一屏是否出现期望文本或其稳定片段
   - 这是 `VERIFY_SENT` 最关键证据

2. **history_context**
   - 来源：调用方提供了 history_region 本身
   - 作用：只是上下文辅助，不单独构成成功

3. **composer_empty**
   - 来源：输入框区域 OCR
   - 作用：观察发送后输入框是否清空/接近清空
   - 只能作为辅助信号

#### 通过规则

- `history_match == passed` → `passed`
- 若 `composer_empty == passed` 且存在 `history_context`，但未看到历史区文本 → **默认仍保守**，只在聚合策略认可时给通过；当前实现更偏保守
- 如果只看到输入框清空，没看到历史消息 → `unknown` / `send_uncertain`

#### 失败分类

- `send_not_observed`
- `composer_not_empty`
- `send_uncertain`
- `history_region_missing`
- `composer_region_missing`

#### 安全边界

- **绝不允许**因为 sent 状态看不清就自动再发一次
- `VERIFY_SENT` 看不清时，正确结果是：
  - `unknown`
  - `needs_review`
  - 人工确认

#### 典型实战用法

```python
res = dc.verify_feishu_lark_sent(
    expected_text='你好，已收到。明天我再跟进。',
    history_region=(420, 150, 1130, 620),
    composer_region=(430, 820, 1100, 210),
    match_fragment='已收到。明天我再跟进',
)
```

---

## 5. 统一证据结构

本次新增统一 signal / stage 结果结构。

### 5.1 单个 signal

```json
{
  "name": "header_match",
  "status": "passed",
  "matched": true,
  "expected": "[YOUR_NAME]",
  "actual": "[YOUR_NAME] 供应链主管",
  "source": "ocr",
  "reason": null,
  "confidence": 1.0,
  "meta": {
    "region": [920, 82, 420, 72],
    "role": "target_header"
  },
  "evidence": {
    "ok": true,
    "actual": "[YOUR_NAME] 供应链主管",
    "normalized_actual": "[YOUR_NAME] 供应链主管",
    "normalized_expected": "[YOUR_NAME]",
    "source": "ocr",
    "extraction": {
      "image_path": "...",
      "ocr_image_path": "...",
      "lang": "chi_sim+eng",
      "psm": 6
    }
  }
}
```

### 5.2 聚合后的 stage result

```json
{
  "ok": true,
  "state": "VERIFY_TARGET",
  "status": "passed",
  "reason": "multi_signal_match",
  "confidence": 0.9,
  "signals": [...],
  "summary": {
    "passed": 2,
    "failed": 1,
    "unknown": 0,
    "total": 3
  },
  "target": {
    "expected_name": "[YOUR_NAME]",
    "expected_type": "person",
    "disambiguation_hint": "供应链主管",
    "window_title_hint": "Feishu"
  }
}
```

### 5.3 为什么这结构重要

因为主执行器以后可以直接用它：
- 写审计日志
- 做 RGA step evidence 落盘
- 决定 `next state`
- 给人类展示“为什么通过/为什么失败”

而不是只说一句“验证成功/失败”。

---

## 6. 推荐确认链步骤（Feishu/Lark 局部版）

### 6.1 发消息前

1. `VERIFY_APP_READY`
   - 证据：window title / frontmost app
   - 目的：确认当前确实在 Feishu/Lark

2. `VERIFY_TARGET`
   - 证据：window title + header OCR + sidebar OCR + disambiguation OCR
   - 通过标准：至少两类证据一致

3. `FOCUS_COMPOSER`
   - 不在本次 helper 中实现，由外层动作层处理
   - 但聚焦后建议马上进入局部确认，不要直接输入+发送

4. `COMPOSE_DRAFT`
   - 输入草稿，优先可回读方式

5. `VERIFY_DRAFT`
   - 证据：clipboard readback + composer OCR
   - 通过标准：任一可靠证据通过；实战上最好两者之一强通过

6. `PRE_SEND_CONFIRM`
   - 外层流程必须保留
   - 本次文档不放开默认发送

### 6.2 发送后观察

7. `VERIFY_SENT`
   - 证据：history_region OCR + composer_region OCR
   - 通过标准：优先依赖 history_match
   - 看不清 = `unknown`，不是成功

---

## 7. 验证方式

### 7.1 代码层检查

```bash
python3 -m py_compile ~/.openclaw/skills/desktop-control/__init__.py
python3 -m py_compile ~/.openclaw/skills/desktop-control/verification_demo.py
```

### 7.2 demo 运行

```bash
~/.openclaw/skills/desktop-control/.venv/bin/python ~/.openclaw/skills/desktop-control/verification_demo.py
```

### 7.3 本次实际观察结果

verify-only demo 中：
- `VERIFY_TARGET = failed`
- `VERIFY_DRAFT = passed`
- `VERIFY_SENT = unknown`

这其实是**正确行为**：
- 没提供 Feishu/Lark 头部/侧栏局部区域 → 不该盲判 target 成功
- 剪贴板内有测试文本 → draft 可以通过
- 没提供历史区局部区域、也没真实发送 → sent 不该误报 success

这正符合 RGA 风险边界。

---

## 8. 如何在实战里落地区域

推荐给 Feishu / Lark 单独维护一个平台配置层，例如：

```yaml
app: feishu
window_title_hint: Feishu
regions:
  header: [920, 82, 420, 72]
  sidebar: [120, 150, 280, 560]
  composer: [430, 820, 1100, 210]
  history: [420, 150, 1130, 620]
send_semantics:
  allow_send_via_enter: false
  preferred_send_trigger: button
ocr:
  lang: chi_sim+eng
  psm: 6
```

这样主链就不必每次临时猜区域。

---

## 9. 剩余 gap

### P0

1. **缺少 Feishu/Lark 区域模板与自动锚定**
   - 现在支持 region-first，但 region 仍需调用方提供
   - 下一步应补：
     - 头部锚点
     - 发送按钮模板
     - 左侧会话列表锚点

2. **`VERIFY_TARGET` 还没有真正的“同名歧义检测”**
   - 目前只能靠 `disambiguation_hint` 辅助
   - 还不能自动判断“多个同名候选同时出现”

3. **`VERIFY_SENT` 仍依赖 OCR，对复杂气泡样式不够稳**
   - 尤其中文、深色模式、消息折叠、多行截断时
   - 需要更窄的最后消息区域切片和模板辅助

### P1

4. **未接入发送按钮模板匹配**
   - 这次重点是 target/draft/sent
   - 未来可用 `verify_image_present()` 补 `PRE_SEND_CONFIRM` 辅助证据

5. **未接入 macOS Accessibility API 读取焦点输入框值**
   - 这是 draft verification 最值得做的增强
   - 如果能拿到原生 value，会显著优于 OCR

6. **缺少标准 artifact 落盘路径**
   - 当前 evidence 结构支持挂图，但没统一落到 workspace 审计目录

### P2

7. **语言包可用性没细分到 `chi_sim` / `eng`**
   - 当前 `get_ocr_status()` 只判断 OCR 总体可用
   - 没判断中英语言数据包是否齐全

8. **缺少局部区域自动截图调试工具**
   - 实战调参需要快速保存 header/sidebar/composer/history 四块截图
   - 方便人类校准区域和 OCR 参数

---

## 10. 最终结论

这次 B 线已经把 Feishu / Lark 的确认链从：
- “有 OCR 接口，但缺少平台化确认逻辑”

推进到：
- “有 Feishu/Lark 专用 VERIFY_TARGET / VERIFY_DRAFT / VERIFY_SENT helper”
- “有局部区域优先策略”
- “有统一 signal / evidence 结构”
- “有 verify-only demo”
- “sent 看不清时默认 unknown，不会误判 success，更不会默认重发”

离真正高可靠实战还差：
- 平台区域模板
- 目标歧义识别
- 最后一条消息局部锚定
- accessibility/value 级别回读

但从 RGA 安全基线角度看，这已经比“全屏盲读 + 盲发”靠谱很多，也更适合进入下一阶段收口。