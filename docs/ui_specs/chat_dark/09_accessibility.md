# 09 Accessibility — 聊天页 Chat（深色模式）

## 触摸目标尺寸（iOS HIG 标准：≥ 44 × 44 pt）

| 组件 | 视觉尺寸（估算）| 触摸目标（估算）| 是否达标 |
|------|--------------|--------------|---------|
| BackButton（返回"<"） | 约 24 × 24 pt 图标 | 约 44 × 44 pt 热区 | ✅ 达标（建议确保热区 ≥ 44pt） |
| AvatarWithGlow（头像） | 约 50 × 50 pt | 约 50 × 50 pt | ✅ 达标 |
| MoreButton（"···"） | 约 24 × 24 pt 图标 | 约 44 × 44 pt 热区 | ✅ 达标（建议确保热区） |
| PlayButton（播放） | 约 36 × 36 pt | 约 44 × 44 pt 含内边距 | ✅ 达标（边距补充后） |
| PlusButton（"+"） | 约 40 × 40 pt | 约 44 × 44 pt | ✅ 达标（边距补充后） |
| SendButton（发送） | 约 42 × 42 pt | 约 44 × 44 pt | ✅ 达标（接近临界值，建议提升至 48pt） |
| TextInput（输入框） | 约 全宽 × 40 pt | 全宽 × 40 pt | ⚠️ 高度略低于44pt，建议提升至 44pt |
| AITextBubble（长按） | 按内容宽高 | 同视觉尺寸 | ✅ 内容区域通常足够 |
| WaveformVisualizer（波形） | 约 190 × 30 pt | 建议扩展至整个波形行 | ⚠️ 高度不足，需扩大触摸区域 |
| HomeIndicator | 系统组件 | 系统接管 | N/A |

**总结**：所有主要交互按钮基本达标，SendButton 和 TextInput 高度建议提升至 44pt 以上；波形区域需扩大热区。

---

## 颜色对比度（WCAG AA/AAA 评估）

> WCAG AA 标准：正文文字 ≥ 4.5:1，大字/UI组件 ≥ 3:1
> WCAG AAA 标准：正文文字 ≥ 7:1

### 文字与背景对比

| 元素 | 文字颜色 | 背景颜色 | 估算对比度 | WCAG AA | WCAG AAA |
|------|---------|---------|----------|---------|---------|
| 角色名"小屿" | `#FFFFFF` | `rgba(30,27,40,0.75)` ≈ `#1E1B28` | ~18:1 | ✅ 通过 | ✅ 通过 |
| 状态"温柔在线" | `rgba(255,255,255,0.70)` | `#1E1B28` | ~10:1 | ✅ 通过 | ✅ 通过 |
| 时间戳 | `rgba(255,255,255,0.45)` | `#1B1923` | ~5:1 | ✅ 通过（大字） | ⚠️ 接近临界 |
| AI 消息正文 | `#F0EEFF` | `rgba(45,40,65,0.90)` ≈ `#2D2841` | ~14:1 | ✅ 通过 | ✅ 通过 |
| 用户消息正文 | `#FFFFFF` | `#3B5BDB` | ~4.7:1 | ✅ 通过（接近临界） | ⚠️ 不通过 |
| 语音时长"0:18" | `rgba(255,255,255,0.60)` | `#2D2841` | ~7:1 | ✅ 通过 | ✅ 通过 |
| AI 朗读提示 | `rgba(255,255,255,0.45)` | `#2D2841` | ~5:1 | ✅ 通过（小字警戒） | ⚠️ 不通过 |
| 占位文字 | `rgba(255,255,255,0.40)` | `#1E1B28` | ~4.2:1 | ⚠️ 略低（正文） | ❌ 不通过 |
| 状态栏时间"9:41" | `#FFFFFF` | 透明叠 `#1B1923` | ~18:1 | ✅ 通过 | ✅ 通过 |

**需关注项**：
- 占位文字对比度 ~4.2:1，略低于正文 AA 标准（4.5:1），建议提升至 `rgba(255,255,255,0.50)` 改善
- "AI朗读·可点击播放"为小字，需确保字号 ≥ 12pt 且对比度满足大字标准（3:1）
- 用户消息气泡正文与靛蓝背景的对比度接近临界，生产实现需精确测量

---

## 焦点状态（Focus State）

| 组件 | 建议焦点环样式 | 说明 |
|------|-------------|------|
| BackButton | 粉色圆形焦点环，2px，`#FFB7C5`，offset 2px | 深色背景上粉色可见 |
| MoreButton | 同 BackButton | |
| PlayButton | 粉色圆形焦点环 | |
| PlusButton | 白色圆形焦点环 | |
| SendButton | 粉色+白色双层焦点环（视觉强调） | 主要操作，焦点更显著 |
| TextInput | 粉色底边框焦点线，宽 2px | 胶囊形输入框用底部线焦点 |
| AITextBubble | 粉色虚线边框，radius 匹配气泡 | 长按操作对应键盘 Enter |
| WaveformVisualizer | 浅色虚线框 | |

**Tab 顺序建议**：
1. BackButton（左上）
2. AvatarWithGlow（可选，跳转角色详情）
3. MoreButton（右上）
4. 消息列表内可交互元素（PlayButton 等，Tab 顺序从上到下）
5. PlusButton（输入栏左）
6. TextInput（输入栏中）
7. SendButton（输入栏右）

---

## 文本可读性

| 元素 | 字号（估算）| 行高（估算）| ≥ 12pt | 行高 ≥ 1.4 |
|------|----------|----------|--------|----------|
| AI 消息正文 | ~14 pt（28px/2） | ~1.5 | ✅ | ✅ |
| 用户消息正文 | ~14 pt | ~1.5 | ✅ | ✅ |
| 角色名 | ~16 pt | ~1.3 | ✅ | ⚠️（接近） |
| 状态文字 | ~11 pt | ~1.2 | ⚠️（接近临界） | ⚠️ |
| 时间戳 | ~11 pt | ~1.4 | ⚠️（接近临界） | ✅ |
| 语音时长 | ~13 pt | ~1.0 | ✅ | ⚠️（单行可接受） |
| AI 朗读提示 | ~11 pt | ~1.4 | ⚠️（接近临界） | ✅ |
| 占位文字 | ~14 pt | ~1.0 | ✅ | ⚠️（单行可接受） |
| 状态栏时间 | ~12 pt | ~1.0 | ✅ | N/A（单行） |

**建议**：状态文字"温柔在线"和时间戳字号接近 11pt，在低视力用户场景下可能不够清晰，建议不低于 12pt（24px 设计稿）。

---

## ARIA 建议

| 组件 | 推荐 role | 推荐 aria-label / aria-* | 说明 |
|------|----------|------------------------|------|
| BackButton | `button` | `aria-label="返回"` | 无文字标签，必须提供 aria-label |
| AvatarWithGlow | `img` 或 `button` | `alt="小屿头像"` / `aria-label="查看小屿资料"` | 可点击时用 button role |
| AgentNameStatus | `heading` (h2) + `p` | `aria-label="小屿，温柔在线"` | 整体可作为一个朗读单元 |
| MoreButton | `button` | `aria-label="更多选项"` | 三点图标无文字，必须 aria-label |
| TimestampDivider | `time` + `aria-label` | `datetime="2026-06-28T09:41"` | 使用语义化 `<time>` 元素 |
| AITextBubble | `article` 或 `listitem` | `aria-label="小屿说：[消息内容]"` | 消息列表用 `<ul><li>` 结构 |
| UserTextBubble | `article` 或 `listitem` | `aria-label="我说：[消息内容]"` | |
| AIVoiceBubble | `listitem` | `aria-label="小屿的语音消息，时长18秒，可点击播放"` | 包含时长信息 |
| PlayButton | `button` | `aria-label="播放语音消息"` / `aria-pressed="false"` | 播放中时：`aria-label="暂停语音消息"` + `aria-pressed="true"` |
| WaveformVisualizer | `presentation` | `aria-hidden="true"` | 纯装饰性，不需要朗读 |
| DurationLabel | `span` | `aria-label="时长0分18秒"` | 提供完整时间朗读 |
| TypingIndicatorBubble | `status` | `aria-live="polite"` + `aria-label="小屿正在输入"` | 动态内容用 aria-live |
| PlusButton | `button` | `aria-label="更多功能"` | |
| TextInput | `textbox` | `aria-label="输入消息"` + `placeholder="想和小屿说点什么..."` | |
| SendButton | `button` | `aria-label="发送消息"` + `aria-disabled="true/false"` | 空输入时禁用 |
| MessageList | `list` / `log` | `aria-label="聊天记录"` + `aria-live="polite"` | 新消息动态播报 |

---

## Keyboard Navigation 键盘导航

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 在可交互元素间跳转 | Tab / Shift+Tab | 按上述 Tab 顺序 |
| 激活按钮 | Enter 或 Space | BackButton、MoreButton、PlayButton、SendButton、PlusButton |
| 发送消息 | Enter（在 TextInput 中）| 等同于点击 SendButton |
| 换行 | Shift+Enter（在 TextInput 中）| 如支持多行输入 |
| 关闭弹出菜单 | Escape | MoreButton 弹出菜单、附加功能面板 |
| 消息列表滚动 | 方向键上/下 或 PageUp/PageDown | 消息列表聚焦时 |

---

## Screen Reader 朗读文本建议（中文）

| 元素 | 朗读文本建议 |
|------|------------|
| 整页标题 | "与小屿的聊天" |
| 状态栏 | "现在是上午9点41分，信号满格，WiFi已连接，电量充足" |
| 返回按钮 | "返回，按两下激活" |
| 头像 | "小屿头像，双击查看资料" |
| 角色状态 | "小屿，温柔在线" |
| 更多按钮 | "更多选项，按两下激活" |
| 时间分隔 | "今天上午9点41分" |
| AI消息01 | "小屿说：早上好，昨晚睡得怎么样？" |
| 用户消息01 | "我说：做了个奇怪的梦。" |
| AI消息02 | "小屿说：讲给我听呀～我陪着你。" |
| 语音消息 | "小屿发来一条语音消息，时长18秒，AI朗读，双击播放" |
| 播放按钮 | "播放小屿的语音消息" |
| 用户消息02 | "我说：好。" |
| 输入中气泡 | "小屿正在输入" |
| 输入框 | "消息输入框，想和小屿说点什么" |
| 发送按钮 | "发送消息" |

---

## 移动端操作友好度

### 单手操作分析（iPhone 14，390pt 宽）

| 区域 | 拇指可达性（右手） | 说明 |
|------|----------------|------|
| 顶部 Header（BackButton、MoreButton） | ⚠️ 较难（需要拇指拉伸） | 建议支持双击下拉/手势返回作为补充 |
| 消息列表（主体内容区） | ✅ 良好 | 中部区域，拇指轻松触达 |
| 底部 Input Bar（PlusButton、TextInput、SendButton） | ✅ 优秀 | 底部区域，拇指自然落位 |
| PlayButton（消息列表内，偏上区域） | ⚠️ 中等 | 需要单手上移操作 |

### 拇指区域建议
- **舒适区**（底部 40%）：Input Bar 完全落在舒适区，体验最佳
- **可达区**（中部 40%）：消息列表大部分消息可达
- **需伸展区**（顶部 20%）：Header 区域对单手操作不友好
- **建议**：支持 iOS 系统手势返回（左滑边缘），减少对顶部返回按钮的依赖

### 操作安全距离
- 发送按钮与 PlusButton 间距约 16 pt（估算值），误触风险低
- "好。"等短消息气泡较小，但长按操作不属于精准操作，可接受
