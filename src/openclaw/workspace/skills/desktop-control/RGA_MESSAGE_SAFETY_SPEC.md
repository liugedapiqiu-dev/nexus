# Desktop Control RGA 消息发送安全规范（v0.1-draft）

状态：draft / 可直接用于实现设计与验收  
适用技能：`desktop-control`  
重点场景：桌面端消息发送、回复、转发、提交类高风险动作  
设计原则：**执行一步 → 快速识别 → 确认 → 再继续**（RGA: Run → Glance/Recognize → Approve）

---

## 1. 文档目标

这份规范不是概念说明，而是给 `desktop-control` 后续实现、任务编排、验收测试直接使用的操作合同。

它解决的问题是：

1. 不能再只靠“动作链成功执行”判定成功；
2. 对消息发送类高风险动作，必须把“目标是否正确”“内容是否正确”“发送是否真的发生”变成显式状态；
3. 让后续实现能知道：
   - 哪些步骤允许自动继续；
   - 哪些步骤必须停下来确认；
   - 哪些失败必须立即中止；
   - 当前 desktop-control 已有能力能覆盖到哪里；
   - 还缺哪些能力。

---

## 2. 适用范围

### 2.1 强制适用（必须走 RGA 状态机）

以下属于**高风险桌面动作**，不得使用“盲执行链”直接完成：

- 发送即时消息（飞书 / 微信 / WhatsApp / Telegram / 企业 IM / 网页聊天）
- 回复已有会话
- 转发消息
- 提交表单
- 点击“发送 / 提交 / 发布 / 确认 / 删除 / 转账”这类最终生效按钮
- 面向外部对象的消息外发

### 2.2 建议适用（中风险）

- 搜索并打开联系人/群聊
- 在未知 UI 中进行批量输入
- 上传附件后点击发送
- 编辑已有内容并保存

### 2.3 可不强制适用（低风险）

- 单纯截图
- 读取窗口信息
- 鼠标移动到安全区域
- 本地无副作用浏览

---

## 3. 风险分级与确认门原则

## 3.1 风险级别

### L0 - 观察类
只读、无外部副作用。  
例：截图、窗口枚举、坐标读取。

### L1 - 导航类
会改变焦点或选中对象，但不立即产生外部副作用。  
例：激活应用、搜索联系人、打开会话。

### L2 - 预备写入类
进入可输入状态，可能修改草稿，但尚未最终提交。  
例：把文本输入到消息框。

### L3 - 生效类（高风险）
一旦执行会产生外部副作用，且通常不可撤销或成本高。  
例：按发送、点击提交、确认删除。

## 3.2 确认门规则

### Gate A：目标确认门（必须）
**在进入具体会话 / 目标对象后，发送前必须确认当前目标就是预期对象。**

适用：所有消息发送、回复、转发。

最小确认信号至少满足其一：
- 窗口/会话标题精确匹配；
- OCR/截图识别到目标名字且与预期一致；
- UI 标签区域（聊天头部、侧栏选中项）双重一致；
- 系统提供结构化元素识别时，元素 label 精确匹配。

若不能确认：**中止，不允许猜测继续。**

### Gate B：内容确认门（必须）
**在最终发送前，必须确认输入框中的待发送内容与任务期望一致。**

最小确认信号至少满足其一：
- 输入后截图 + OCR 回读，与规范化文本一致；
- 使用粘贴板回读 / 选中复制回读，与期望一致；
- 有结构化文本框读取能力时，读取值一致。

若不能确认：**中止或回退到重输；不得直接发送。**

### Gate C：最终发送确认门（必须）
**L3 生效动作前必须有最后一道显式确认。**

确认方式允许两种：
1. **策略确认**：任务 schema 明确 `send_confirmation: required`，且调度器/上层已批准；
2. **运行时确认**：执行器在按下发送前，要求明确 approval token / human confirm / policy allow。

若没有最终确认：**不得按发送键。**

### Gate D：发送结果确认门（必须）
**发送动作执行后，必须确认消息确实已发送，而不是只按了键。**

最小确认信号至少满足其一：
- 聊天记录区出现新消息气泡且内容匹配；
- 输入框清空且消息历史新增；
- 平台出现“已发送/送达”视觉反馈；
- OCR 检测到新增最后一条消息与草稿一致。

若无法确认发送成功：判定为 **unknown / needs-human-review**，不能报 success。

---

## 4. 消息发送任务状态机

以下状态机是消息发送类任务的**标准主线**。

```text
INIT
  -> ACTIVATE_APP
  -> VERIFY_APP_READY
  -> LOCATE_TARGET
  -> VERIFY_TARGET            [Gate A]
  -> FOCUS_COMPOSER
  -> COMPOSE_DRAFT
  -> VERIFY_DRAFT             [Gate B]
  -> PRE_SEND_CONFIRM         [Gate C]
  -> SEND_ACTION
  -> VERIFY_SENT              [Gate D]
  -> DONE

任何一步失败：
  -> RETRY_STEP | RECOVER | ABORT | ESCALATE_TO_HUMAN
```

## 4.1 状态定义

### `INIT`
输入任务、风险级别、目标对象、消息内容、允许重试次数、确认策略。

进入条件：任务参数完整。  
失败条件：目标为空、消息为空、策略缺失。  
失败处理：直接 `ABORT_INVALID_TASK`。

### `ACTIVATE_APP`
激活目标应用或窗口（如飞书）。

允许动作：
- activate window
- app switch hotkey
- launch app（若明确允许）

成功信号：
- 目标应用成为前台；或
- 活动窗口标题匹配应用名。

失败策略：
- 可重试 1~2 次；
- 仍失败则 `ABORT_APP_NOT_READY`。

### `VERIFY_APP_READY`
快速识别应用已进入可交互状态，而不是仍在启动/卡死/焦点错位。

成功信号示例：
- 截图中存在应用主界面关键区域；
- 活动窗口标题/进程/界面元素符合预期；
- 非登录页、非更新弹窗、非系统权限弹窗。

必须中止的失败：
- 出现登录页但任务无登录授权；
- 出现权限弹窗影响后续；
- 当前前台根本不是目标应用。

### `LOCATE_TARGET`
搜索并打开目标会话/联系人/群聊。

允许动作：
- 点击搜索框
- 输入目标名称
- 键盘导航结果
- 点击候选结果

成功信号：
- 某个候选项被选中，或
- 会话已打开。

注意：此时**还不能认为目标正确**，只能说明“找到某个候选”。

### `VERIFY_TARGET`（Gate A）
确认当前会话头部、侧栏选中项、标题信息与目标对象一致。

必须校验的字段：
- `target_name_expected`
- `target_type`（person/group/channel，可选但建议）
- `verification_source`（title/sidebar/header/ocr）

通过条件：
- 至少两类信号一致；或
- 一类高置信结构化信号精确一致。

失败分类：
- `target_mismatch`: 识别到错误对象 → **立即中止**
- `target_ambiguous`: 多个同名对象无法区分 → **升级人工**
- `target_unreadable`: OCR/识别失败 → 可重试一次后中止

### `FOCUS_COMPOSER`
把焦点放进正确的输入框。

成功信号：
- 光标进入输入框；
- 输入框高亮/闪烁；
- 粘贴测试或极小输入可被识别在 composer 内（仅在安全模式下）。

失败策略：
- 可重试；
- 若疑似焦点在搜索框、全局快捷搜索、其他输入框，则回退到 `VERIFY_TARGET` 或 `LOCATE_TARGET`。

### `COMPOSE_DRAFT`
输入消息草稿。

允许动作：
- type text
- paste text
- 分段输入（长文本）

约束：
- 默认优先使用**可回读**方式（粘贴或可 OCR 的整段输入）；
- 禁止“输入完立即发送”的连续盲链。

### `VERIFY_DRAFT`（Gate B）
确认输入框中的文本与期望文本一致。

建议标准化比较：
- trim 首尾空白
- 统一换行
- 允许平台自动表情/富文本轻微差异
- 必要时支持 exact / normalized / prefix 三种比较模式

失败分类：
- `draft_empty`: 输入框为空 → 可重输
- `draft_partial`: 只输入了一部分 → 可清空后重输
- `draft_corrupted`: 文本被输入法/快捷键污染 → 清空后重输；连续失败则中止
- `draft_unreadable`: 无法 OCR/回读 → 中止，不允许发送

### `PRE_SEND_CONFIRM`（Gate C）
发送前最终确认。

必须输出一份最小确认摘要：
- app: 飞书
- target: [YOUR_NAME]
- target_verified_by: header+sidebar
- message_preview: 前 80~120 字
- risk_level: L3
- policy: send_confirmation=required

通过条件：
- 明确获得运行策略许可；
- 如果策略要求人工确认，则收到人工确认。

失败策略：
- 没有确认 → `ABORT_NOT_APPROVED`

### `SEND_ACTION`
执行最终生效动作。

允许动作：
- press Enter（仅当平台约定 Enter=send 且已确认）
- click Send button
- hotkey for send

约束：
- 必须记录实际发送方式（`enter` / `button` / `hotkey`）；
- 若平台存在“Enter 换行”歧义，默认不用 Enter，优先点击 Send。

### `VERIFY_SENT`（Gate D）
确认消息已实际发出。

通过条件至少满足其一：
- 新消息出现在历史中，且内容匹配草稿；
- 输入框清空 + 历史区新增本人消息；
- 平台出现发送成功状态。

失败分类：
- `send_not_observed`: 没观察到新消息 → 可等待短暂 UI 刷新后重检
- `send_uncertain`: 看不清最后一条消息是谁/内容是什么 → 升级人工
- `send_failed_ui`: 出现失败标记/红点/重试提示 → 报 failed，不自动重复发送

### `DONE`
仅当 Gate A/B/C/D 都通过，才允许报 `success`。

---

## 5. 失败策略（必须落地）

## 5.1 可重试 vs 必须中止

### 可重试（通常最多 1~2 次）
- 应用未激活
- 搜索结果未刷新
- 输入框未聚焦
- OCR 临时读取失败
- 发送后 UI 刷新慢

### 必须中止
- 目标对象识别为错误人/错误群
- 目标对象存在歧义且无法消歧
- 草稿内容无法确认
- 未获得最终发送确认
- 发送后结果不明但存在重复发送风险
- 遇到删除/覆盖/支付等更高风险弹窗

## 5.2 不允许自动重试发送

对 `SEND_ACTION` 有一个硬规则：

**只要已经触发过一次真实发送动作，就不能因为“没看清”而直接再发一次。**

原因：
- 再发一次的代价是重复外发；
- 对消息类任务，重复发送通常比“需要人工确认”更糟。

所以：
- 发送后看不清 → `UNKNOWN_SENT_STATE`
- 不是 `RETRY_SEND`

## 5.3 恢复策略

允许的恢复动作：
- 重新激活 app
- 清空错误输入框后重输草稿
- 返回会话列表重新定位目标
- 重新截图/重新 OCR

不允许的恢复动作：
- 在目标不明确时继续输入
- 在草稿未确认时直接发送
- 在发送结果不明时再次发送

---

## 6. 与当前 desktop-control 能力的映射

## 6.1 当前已有能力（可直接复用）

根据现有 `desktop-control` 文档/skill.json，可直接映射：

- `activate window` → `ACTIVATE_APP`
- `mouse_click` / `mouse_move` → `LOCATE_TARGET`, `FOCUS_COMPOSER`, `SEND_ACTION`
- `keyboard_type` / `keyboard_press` → `LOCATE_TARGET`, `COMPOSE_DRAFT`, `SEND_ACTION`
- `screenshot` → `VERIFY_APP_READY`, `VERIFY_TARGET`, `VERIFY_DRAFT`, `VERIFY_SENT`
- `image_search` → 定位按钮、图标、输入区候选
- 窗口枚举 / active window（见 SKILL.md）→ `VERIFY_APP_READY`
- approval mode（文档已声明）→ `PRE_SEND_CONFIRM`

## 6.2 当前明显不足（必须补）

这是本规范真正要求补齐的能力缺口：

1. **OCR / 文本回读能力未成为标准接口**
   - 没有稳定的 `read_text_from_region` / `ocr_region` 能力，就无法可靠实现 Gate A/B/D。

2. **结构化验证结果未标准化**
   - 目前更像“执行 API 列表”，缺少 `verification_result`、`confidence`、`matched_text` 这类统一返回。

3. **高风险动作没有强制确认门**
   - 现有文档提到 approval mode，但没有规定哪些动作必须经过哪一道门。

4. **未区分“已执行动作”与“已验证成功”**
   - 例如按了 Enter ≠ 已发送成功。

5. **缺少任务级状态机与审计日志结构**
   - 后续实现至少要记录：当前状态、截图证据、识别结果、决策原因、是否人工批准。

6. **缺少平台差异策略**
   - 如 Enter 是发送还是换行，必须平台化配置，而不是默认假设。

---

## 7. 实现合同：执行器至少应输出什么

建议 `desktop-control` 后续执行器在每一步输出统一事件：

```json
{
  "state": "VERIFY_TARGET",
  "status": "passed",
  "risk_level": "L3",
  "evidence": {
    "screenshot": "artifacts/step-04.png",
    "active_window": "Feishu",
    "ocr_text": "[YOUR_NAME]",
    "matched": true,
    "confidence": 0.93
  },
  "decision": {
    "next": "FOCUS_COMPOSER",
    "reason": "header and sidebar both match expected target"
  }
}
```

最低要求字段：
- `state`
- `status` (`passed` / `failed` / `needs_confirmation` / `aborted` / `unknown`)
- `evidence`
- `decision.next`
- `reason`

---

## 8. 建议的任务 schema（消息发送类）

```yaml
kind: desktop.message.send
version: 0.1
risk_level: L3
app:
  name: feishu
  window_hint: 飞书
target:
  name: [YOUR_NAME]
  type: person
  disambiguation_hint: 供应链主管
message:
  text: "测试消息：RGA 规范验证"
  compare_mode: normalized
policy:
  require_target_verification: true
  require_draft_verification: true
  require_send_confirmation: true
  require_sent_verification: true
  max_retries_per_step: 1
  allow_send_via_enter: false
verification:
  target_sources: [header, sidebar, ocr]
  draft_sources: [ocr, clipboard-readback]
  sent_sources: [message-list, composer-empty]
artifacts:
  save_screenshots: true
  save_ocr_text: true
```

真实 machine-readable 版本见配套 JSON 文件：`skills/desktop-control/desktop-control.rga.acceptance.json`。

---

## 9. 验收基线（Acceptance）

## 9.1 L1 结构验收

必须能表达以下状态：
- `VERIFY_TARGET`
- `VERIFY_DRAFT`
- `PRE_SEND_CONFIRM`
- `VERIFY_SENT`

并且任务定义里必须有以下布尔策略：
- `require_target_verification`
- `require_draft_verification`
- `require_send_confirmation`
- `require_sent_verification`

## 9.2 L2 运行验收

最小 smoke test 应证明：

1. 可以激活飞书窗口；
2. 可以打开指定会话；
3. 在**不真实发送**前提下，能完成 target verification；
4. 可以输入草稿并回读校验；
5. 若无确认令牌，执行器会停在 `PRE_SEND_CONFIRM`，而不是直接发送；
6. 发送后若看不清结果，会返回 `unknown` / `needs-human-review`，不是误报 success。

## 9.3 L3 合同验收

人工检查必须确认：

1. 高风险消息任务不能绕过 Gate A/B/C/D；
2. 目标不明确时会中止，不会猜一个继续；
3. 内容未确认时不会发送；
4. 发送结果不明时不会自动重复发送；
5. 最终 success 代表“已验证发出”，不是“按了发送键”。

---

## 10. 平台配置建议

不同平台应当允许覆盖以下参数：

- `send_trigger`: `enter` / `cmd-enter` / `button`
- `enter_behavior`: `send` / `newline` / `unknown`
- `target_identity_regions`: 头部、侧栏、会话列表区域坐标/锚点
- `composer_region`: 输入框区域
- `sent_message_region`: 最后一条消息候选区域
- `ocr_language`: `zh`, `en`, mixed

没有平台配置时，默认按**保守策略**处理：
- 不用 Enter 作为发送；
- 没法验证就中止。

---

## 11. 剩余 gap 清单（给实现负责人）

P0：
1. 增加 OCR/区域文本读取标准接口；
2. 给高风险任务接入强制确认门；
3. 引入任务状态机执行器，而不是裸动作序列；
4. 统一 step evidence / confidence / next-state 返回结构。

P1：
5. 增加平台级消息发送配置（Feishu/微信/WhatsApp）；
6. 增加截图工件与审计日志落盘；
7. 增加“目标消歧”能力（同名联系人时提示人工）。

P2：
8. 增加 UI label detection / accessibility tree 优先于 OCR；
9. 增加 message preview diff；
10. 增加 dry-run / verify-only 模式。

---

## 12. 结论

对 `desktop-control` 来说，消息发送类任务以后不能再定义成：

`search -> enter -> type -> enter`

而必须定义成：

`activate app -> verify app -> locate target -> verify target -> focus composer -> compose -> verify draft -> pre-send confirm -> send -> verify sent`

这不是“更啰嗦”，而是把**不会验证的自动化**升级成**可审计、可中止、可验收的自动化**。
