# Skills Inventory

> 正式技能台账（治理层 v2 A 线收口版）。基于当前机器真实目录扫描，并叠加命名/状态治理决定。生成时间：2026-03-21 Asia/Shanghai。

## 1. 范围与判定口径

- 扫描根：`~/.npm-global/lib/node_modules/openclaw/skills`、`~/.npm-global/lib/node_modules/openclaw/extensions/feishu/skills`、`~/.openclaw/skills`、`~/.openclaw/workspace/skills`。
- 只记录当前机器**真实存在的目录**。
- 本文件是**人类可读正式台账**；机器索引以 `SKILLS_INVENTORY.json` 为准。
- 本轮新增治理约束：
  - `canonical_name`：统一使用 **lowercase kebab-case**。
  - `display_name`：保留产品名、品牌名、大小写、中文/英文展示写法。
  - `aliases`：收纳目录名、历史名、slug、大小写变体，不再与 `canonical_name` 混用。
  - `status`：本轮正式使用 `active / experimental / deprecated / disabled` 四档，强调治理可用性而非运行时健康度。

## 2. 总览

- 扫描目录总数：**96**
- active：**91**；experimental：**1**；deprecated：**1**；disabled：**3**
- 第一优先级技能集合：`vectorbrain-memory-search, brain-health-monitor, memory-extraction-engine, auto-reflection-engine, auto-archive-system, knowledge-dedup`

## 3. 命名规范（正式收口）

### 3.1 canonical_name

- 作为治理层主键的人类语义名。
- 必须稳定、可迁移、可去重。
- 一律使用 **lowercase kebab-case**。
- 不直接跟目录名绑定；目录迁移时 canonical_name 不应变化。

示例：
- `Productivity` → canonical 收口为 `productivity`
- `Schedule` → canonical 收口为 `schedule`
- `todoist-rs` 目录 → canonical 收口为 `todoist`
- `openclaw-mission-control` 目录 → canonical 收口为 `mission-control`

### 3.2 display_name

- 面向展示层/文档层。
- 保留大小写、品牌、中文名、副标题。
- 可以与目录名不同，也可以与 canonical_name 不同。

### 3.3 aliases

以下名称都进入 `aliases`，不再污染 canonical：
- 目录名
- ClawHub slug
- 历史大小写写法
- 仓库/实现名
- 旧版本名 / legacy 名

## 4. 状态规范（正式落标）

- `active`：当前正式技能，可继续使用与维护。
- `experimental`：仍在探索，接口/结构未稳定。
- `deprecated`：仍保留，但不应继续作为主版本演进。
- `disabled`：明确不进入正式可用集合；可因 legacy、占位、伪技能、停用而存在。

## 5. 重点争议目录的正式治理决定

- **find-skills-skill**：正式技能，`canonical_name=find-skills`，目录名保留为 alias / 发布 slug，状态 `active`。
- **todoist-rs**：正式技能，`canonical_name=todoist`，目录名保留为实现别名，状态 `active`。
- **openclaw-mission-control**：正式技能，`canonical_name=mission-control`，目录名保留为发布 slug，状态 `active`。
- **skill-creator` 双版本**：平台内置版为 authoritative `active`；workspace 版降为 `deprecated`，仅保留历史/本地覆写参考。
- **triple-memory-skill.disabled**：正式落标为 `disabled`，且视为 legacy memory line，不得自动复活。
- **skillguard**：伪技能目录，正式落标 `disabled`；建议迁出 `skills/` 根。
- **claw-skill-guard**：空占位目录，正式落标 `disabled`；建议迁出或删除。
- **Productivity / Schedule**：canonical_name 分别收口为 `productivity` / `schedule`；首字母大写写法仅保留为 display/alias。
- **gupiaozhushou**：父目录为正式技能；子目录按 nested payload 管理，避免双计数。

## 6. 第一优先级技能备注

- `vectorbrain-memory-search` → `P0-highest`
- `brain-health-monitor` → `P1-core`
- `memory-extraction-engine` → `P1-core`
- `auto-reflection-engine` → `P1-core`
- `auto-archive-system` → `P1-core`
- `knowledge-dedup` → `P1-core`

## 7. 正式 Inventory（全量）

| canonical_name | display_name | directory_name | status | path | aliases | notes |
|---|---|---|---|---|---|---|
| 1password | 1Password CLI | 1password | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/1password |  |  |
| apple-notes | Apple Notes CLI | apple-notes | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/apple-notes |  |  |
| apple-reminders | Apple Reminders CLI (remindctl) | apple-reminders | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/apple-reminders |  |  |
| bear-notes | Bear Notes | bear-notes | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/bear-notes |  |  |
| blogwatcher | blogwatcher | blogwatcher | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/blogwatcher |  |  |
| blucli | blucli (blu) | blucli | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/blucli |  |  |
| bluebubbles | BlueBubbles Actions | bluebubbles | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/bluebubbles |  |  |
| camsnap | camsnap | camsnap | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/camsnap |  |  |
| canvas | Canvas Skill | canvas | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/canvas |  |  |
| clawhub | ClawHub CLI | clawhub | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/clawhub |  |  |
| coding-agent | Coding Agent (bash-first) | coding-agent | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/coding-agent |  |  |
| discord | Discord (Via `message`) | discord | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/discord |  |  |
| eightctl | eightctl | eightctl | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/eightctl |  |  |
| gemini | Gemini CLI | gemini | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/gemini |  |  |
| gh-issues | gh-issues — Auto-fix GitHub Issues with Parallel Sub-agents | gh-issues | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/gh-issues |  |  |
| gifgrep | gifgrep | gifgrep | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/gifgrep |  |  |
| github | GitHub Skill | github | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/github |  |  |
| gog | gog | gog | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/gog |  |  |
| goplaces | goplaces | goplaces | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/goplaces |  |  |
| healthcheck | OpenClaw Host Hardening | healthcheck | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/healthcheck |  |  |
| himalaya | Himalaya Email CLI | himalaya | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/himalaya |  |  |
| imsg | imsg | imsg | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/imsg |  |  |
| mcporter | mcporter | mcporter | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/mcporter |  |  |
| model-usage | Model usage | model-usage | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/model-usage |  |  |
| nano-banana-pro | Nano Banana Pro (Gemini 3 Pro Image) | nano-banana-pro | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/nano-banana-pro |  |  |
| nano-pdf | nano-pdf | nano-pdf | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/nano-pdf |  |  |
| node-connect | Node Connect | node-connect | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/node-connect |  |  |
| notion | notion | notion | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/notion |  |  |
| obsidian | Obsidian | obsidian | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/obsidian |  |  |
| openai-image-gen | OpenAI Image Gen | openai-image-gen | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/openai-image-gen |  |  |
| openai-whisper | Whisper (CLI) | openai-whisper | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/openai-whisper |  |  |
| openai-whisper-api | OpenAI Whisper API (curl) | openai-whisper-api | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/openai-whisper-api |  |  |
| openhue | OpenHue CLI | openhue | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/openhue |  |  |
| oracle | oracle — best use | oracle | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/oracle |  |  |
| ordercli | ordercli | ordercli | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/ordercli |  |  |
| peekaboo | Peekaboo | peekaboo | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/peekaboo |  |  |
| sag | sag | sag | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/sag |  |  |
| session-logs | session-logs | session-logs | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/session-logs |  |  |
| sherpa-onnx-tts | sherpa-onnx-tts | sherpa-onnx-tts | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/sherpa-onnx-tts |  |  |
| skill-creator | Skill Creator | skill-creator | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/skill-creator | `skill-creator-system` | 存在平台版与 workspace 版双份实现，需明确主版本。 治理决定：平台内置 skill-creator 为当前 authoritative 版本。 |
| slack | Slack Actions | slack | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/slack |  |  |
| songsee | songsee | songsee | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/songsee |  |  |
| sonoscli | Sonos CLI | sonoscli | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/sonoscli |  |  |
| spotify-player | spogo / spotify_player | spotify-player | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/spotify-player |  |  |
| summarize | Summarize | summarize | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/summarize |  |  |
| things-mac | Things 3 CLI | things-mac | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/things-mac |  |  |
| tmux | tmux Session Control | tmux | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/tmux |  |  |
| trello | Trello Skill | trello | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/trello |  |  |
| video-frames | Video Frames (ffmpeg) | video-frames | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/video-frames |  |  |
| voice-call | Voice Call | voice-call | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/voice-call |  |  |
| wacli | wacli | wacli | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/wacli |  |  |
| weather | Weather Skill | weather | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/weather |  |  |
| xurl | xurl — Agent Skill Reference | xurl | active | /home/user/.npm-global/lib/node_modules/openclaw/skills/xurl |  |  |
| feishu-doc | Feishu Document Tool | feishu-doc | active | /home/user/.npm-global/lib/node_modules/openclaw/extensions/feishu/skills/feishu-doc |  |  |
| feishu-drive | Feishu Drive Tool | feishu-drive | active | /home/user/.npm-global/lib/node_modules/openclaw/extensions/feishu/skills/feishu-drive |  |  |
| feishu-perm | Feishu Permission Tool | feishu-perm | active | /home/user/.npm-global/lib/node_modules/openclaw/extensions/feishu/skills/feishu-perm |  |  |
| feishu-wiki | Feishu Wiki Tool | feishu-wiki | active | /home/user/.npm-global/lib/node_modules/openclaw/extensions/feishu/skills/feishu-wiki |  |  |
| agent-browser | Browser Automation with agent-browser | agent-browser | active | /home/user/.openclaw/skills/agent-browser |  |  |
| ahao-auto-updater | [YOUR_AI_NAME]文件变更检测器 (Ahao Auto-Updater) | ahao-auto-updater | active | /home/user/.openclaw/skills/ahao-auto-updater |  |  |
| ahao-core-context | [YOUR_AI_NAME]核心上下文 (Ahao Core Context) | ahao-core-context | active | /home/user/.openclaw/skills/ahao-core-context |  |  |
| ahao-loader | [YOUR_AI_NAME]后台加载器 (Ahao Loader) | ahao-loader | active | /home/user/.openclaw/skills/ahao-loader |  |  |
| auto-archive-system | 自动归档系统 (Auto Archive System) | auto-archive-system | active | /home/user/.openclaw/skills/auto-archive-system |  | 归档旧版本与历史内容；有治理价值，但需避免误归档。 优先级标记：P1-core。 |
| auto-reflection-engine | 自动反思引擎 (Auto Reflection Engine) | auto-reflection-engine | active | /home/user/.openclaw/skills/auto-reflection-engine |  | 任务完成后自动复盘；偏自动化后台能力。 优先级标记：P1-core。 |
| brain-health-monitor | 大脑健康监控 (Brain Health Monitor) | brain-health-monitor | active | /home/user/.openclaw/skills/brain-health-monitor |  | [YOUR_AI_NAME]核心脑健康监控；主要面向 VectorBrain 运维。 优先级标记：P1-core。 |
| desktop-control | Desktop Control Skill | desktop-control | active | /home/user/.openclaw/skills/desktop-control |  |  |
| gupiaozhushou | 财经分析工具包 (Gupiaozhushou) | gupiaozhushou | active | /home/user/.openclaw/skills/gupiaozhushou | `gupiaozhushou-财经分析工具包` | 顶层技能存在，但业务内容主要落在其子目录，需防父子双重计数。 治理决定：父目录视为正式技能；子目录视为 bundled content / legacy nested payload，不单独计作并列正式技能。 |
| knowledge-dedup | 知识去重 (Knowledge Dedup) | knowledge-dedup | active | /home/user/.openclaw/skills/knowledge-dedup |  | 知识去重；适合数据治理，但需防误判合并。 优先级标记：P1-core。 |
| memory-extraction-engine | 记忆提炼引擎 (Memory Extraction Engine) | memory-extraction-engine | active | /home/user/.openclaw/skills/memory-extraction-engine |  | 把情景记忆提炼为知识记忆；对记忆质量有长期影响。 优先级标记：P1-core。 |
| office-automation | Office Automation Skill | office-automation-skill | active | /home/user/.openclaw/skills/office-automation-skill |  | 目录名与 canonical_name 不同（dir=office-automation-skill）。 |
| ppt-beautifier | PPT 美化技能 | ppt-beautifier | active | /home/user/.openclaw/skills/ppt-beautifier |  |  |
| self-improvement | Self-Improvement Skill | self-improvement | active | /home/user/.openclaw/skills/self-improvement |  |  |
| session-history-archiver | 会话历史自动归档系统 | session-history-archiver | active | /home/user/.openclaw/skills/session-history-archiver |  |  |
| startup-healthcheck | OpenClaw 启动自检技能 | startup-healthcheck | active | /home/user/.openclaw/skills/startup-healthcheck |  |  |
| tavily | Tavily Search | tavily | active | /home/user/.openclaw/skills/tavily |  |  |
| vectorbrain-connector | VectorBrain Connector | vectorbrain-connector | active | /home/user/.openclaw/skills/vectorbrain-connector |  |  |
| vectorbrain-memory-search | VectorBrain 记忆检索技能 | vectorbrain-memory-search | active | /home/user/.openclaw/skills/vectorbrain-memory-search |  | 最高优先级记忆检索技能；AGENTS/TOOLS/IDENTITY 中均被引用。 优先级标记：P0-highest。 |
| ai-web-automation | SKILL.md | ai-web-automation | active | /home/user/.openclaw/workspace/skills/ai-web-automation |  | 结构较粗糙，更像服务宣传/概念稿，不像成熟 Agent Skill。 |
| automation-workflows | Automation Workflows | automation-workflows | experimental | /home/user/.openclaw/workspace/skills/automation-workflows |  |  |
| claw-skill-guard | claw-skill-guard (placeholder) | claw-skill-guard | disabled | /home/user/.openclaw/workspace/skills/claw-skill-guard | `claw-skill-guard-dir` | 空目录，疑似预留或安装残留。 治理决定：按空占位目录处理；保留 disabled，建议迁出或删除，不应继续出现在技能候选扫描语境中。 |
| clickup | ClickUp Skill | clickup | active | /home/user/.openclaw/workspace/skills/clickup |  |  |
| data-automation-service | Data Automation Service | data-automation-service | active | /home/user/.openclaw/workspace/skills/data-automation-service |  |  |
| find-skills | Find Skills Skill | find-skills-skill | active | /home/user/.openclaw/workspace/skills/find-skills-skill | `find-skills-skill` | 目录名与 canonical_name 不同（dir=find-skills-skill）。 治理决定：规范名保留 `find-skills`；目录名 `find-skills-skill` 视为发行 slug / legacy alias，不建议仅为命名洁癖改目录。 |
| flowmind | FlowMind | flowmind | active | /home/user/.openclaw/workspace/skills/flowmind |  |  |
| habit-tracker | Habit Tracker | habit-tracker | active | /home/user/.openclaw/workspace/skills/habit-tracker |  |  |
| jira | Jira | jira | active | /home/user/.openclaw/workspace/skills/jira |  |  |
| lark-calendar | Lark Calendar & Task Skill | lark-calendar | active | /home/user/.openclaw/workspace/skills/lark-calendar |  |  |
| meeting-notes | Meeting Notes 整理 Skill | meeting-notes | active | /home/user/.openclaw/workspace/skills/meeting-notes |  |  |
| openclaw-live-monitor | OpenClaw Live Monitor | openclaw-live-monitor | active | /home/user/.openclaw/workspace/skills/openclaw-live-monitor |  |  |
| mission-control | Mission Control — Dashboard for OpenClaw | openclaw-mission-control | active | /home/user/.openclaw/workspace/skills/openclaw-mission-control | `openclaw-mission-control` | 目录名与 canonical_name 不同（dir=openclaw-mission-control）。 治理决定：规范名使用较稳定的产品名 `mission-control`；目录名 `openclaw-mission-control` 作为发布 slug 保留。 |
| productivity | Productivity | productivity | active | /home/user/.openclaw/workspace/skills/productivity | `Productivity` | 目录名与 canonical_name 不同（dir=productivity）。 治理决定：canonical_name 一律收口为 lowercase kebab-case；`Productivity` 作为 display_name / alias 保留。 |
| programming-assistant | Programming Assistant Skill | programming-assistant | active | /home/user/.openclaw/workspace/skills/programming-assistant |  |  |
| schedule | Schedule | schedule | active | /home/user/.openclaw/workspace/skills/schedule | `Schedule` | 目录名与 canonical_name 不同（dir=schedule）。 治理决定：canonical_name 一律收口为 lowercase kebab-case；`Schedule` 作为 display_name / alias 保留。 |
| skill-creator | Skill Creator | skill-creator | deprecated | /home/user/.openclaw/workspace/skills/skill-creator | `skill-creator-workspace` | 存在平台版与 workspace 版双份实现，需明确主版本。 治理决定：workspace 版标记为 deprecated，仅作本地历史/覆写候选；当前 authoritative 版本为平台内置目录。非必要不再继续分叉演进。 |
| skillguard | skillguard (non-skill repo) | skillguard | disabled | /home/user/.openclaw/workspace/skills/skillguard | `skillguard-repo` | 非标准技能目录（缺少 SKILL.md），更像独立 Node 工具仓库。 治理决定：按伪技能目录处理；不是标准 skill，保留目录但不计入可调用技能集合，后续建议迁出 skills 根或补独立隔离区。 |
| todoist | Todoist Integration | todoist-rs | active | /home/user/.openclaw/workspace/skills/todoist-rs | `todoist-rs` | 目录名与 canonical_name 不同（dir=todoist-rs）。 治理决定：规范名使用用户触发词 `todoist`；目录名 `todoist-rs` 视为实现/仓库别名。 |
| triple-memory | Triple Memory System | triple-memory-skill.disabled | disabled | /home/user/.openclaw/workspace/skills/triple-memory-skill.disabled | `triple-memory-skill.disabled`, `triple-memory-skill` | 目录名显式 disabled；依赖旧 LanceDB / git-notes 路线，与现行 VectorBrain 路线不一致。 目录名与 canonical_name 不同（dir=triple-memory-skill.disabled）。 治理决定：保持 disabled；其 LanceDB / Git-Notes 路线与现行 VectorBrain 主线冲突，未完成替代关系设计前不得复活。 |

## 8. 当前仍需人工确认

1. `skill-creator` workspace 版是否还需要保留为“本地覆写实验田”；若不需要，后续可物理迁出或归档。
2. `skillguard` 与 `claw-skill-guard` 是要彻底迁出 `skills/` 根，还是建立 `tools/` / `sandbox/` 隔离区承载。
3. `gupiaozhushou` 子目录是否未来要改造成正式 `references/` / `assets/` 结构；本轮仅做治理落标，不动源码结构。
4. 若后续要让 registry 驱动更多自动化，是否将 `aliases / directory_name / manifest_types / source_origin` 上升为强制字段。

## 9. 维护要求

1. 新技能入库时，先定 `canonical_name`，再决定目录名，而不是反过来。
2. 出现同名技能双版本时，必须立即指定 authoritative 版本与非主版本状态。
3. 伪技能目录不得继续以 `active` 或 `experimental` 混入正式台账。
4. 除非先验证 loader，不因治理文档而直接改现有运行路径。
