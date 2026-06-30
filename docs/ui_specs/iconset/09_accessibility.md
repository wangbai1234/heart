# 09 无障碍规范 — Icon Set（24×24 系统图标）

## 概述

本文档涵盖 yuoyuo 图标库在实际应用中的完整无障碍设计规范，遵循 WCAG 2.1 AA 级标准及 iOS/Android 平台无障碍指南。

---

## 触控区域（Touch Target）

### 规范要求

| 平台 | 最小触控目标 | 来源标准 |
|------|------------|---------|
| iOS | 44×44 pt | Apple Human Interface Guidelines |
| Android | 48×48 dp | Google Material Design |
| Web | 44×44 px（推荐） | WCAG 2.5.5（AAA 级目标） |

### 图标触控区实施方案

24dp 图标本身远小于最小触控要求，必须通过以下方式扩展：

| 方案 | 实施方式 | 优点 |
|------|---------|------|
| 透明扩展区 | 图标外添加透明 Padding 使总区域达到 44dp | 视觉不变，交互达标 |
| 容器尺寸 | `IconButton` 容器固定 44×44 dp，图标居中 | 最简洁方案（推荐） |
| 点击热区 | 代码层面扩展点击响应区域 | 纯逻辑，不影响布局 |

**建议：** 所有 `<IconButton>` 容器最小尺寸 44×44 dp，内部 `<Icon>` 24×24 dp 居中对齐。

### 各图标触控区配置

| 使用场景 | 图标 | 触控区尺寸 | 备注 |
|---------|------|----------|------|
| 底部导航 NavItem | home/chat/ai-companion/profile | 全宽÷4 × 44dp | 宽度均分 |
| 聊天输入工具栏 | send/microphone/emoji/add | 44×44 dp | 紧密排列 |
| 媒体播放控制 | play/pause/volume-up/mute | 44×44 dp | — |
| 内联操作按钮 | close/check/more/trash | 44×44 dp | 最小不低于此值 |
| 设置列表行图标 | settings/bell/globe 等 | 整行可点击 | 行高 ≥ 44dp |

---

## 颜色对比度

### 图标默认态

| 元素 | 前景色 | 背景色 | 对比度（估算） | 是否达标 |
|------|--------|--------|--------------|---------|
| 图标描边 #4A4A6A | #4A4A6A | #FAF0EC（画布） | 约 8.5:1（估算值） | AA/AAA 均达标 |
| 图标描边 #4A4A6A | #4A4A6A | #FFFFFF（白卡片） | 约 8.8:1（估算值） | AA/AAA 均达标 |

### 图标激活态（品牌粉色）

| 元素 | 前景色 | 背景色 | 对比度（估算） | 是否达标 |
|------|--------|--------|--------------|---------|
| 粉色图标 #FFB7C5 | #FFB7C5 | #FFF8F3 | 约 1.6:1（估算值） | 不达标（WCAG AA要求3:1） |
| 粉色图标 #FFB7C5 | #FFB7C5 | #FFFFFF | 约 1.5:1（估算值） | 不达标 |

**重要警告：** Primary 品牌粉 #FFB7C5 在白色/奶油背景上对比度不足，不可单独作为传递信息的唯一视觉手段。

**补救方案：**
1. 激活状态必须同时使用颜色 + 其他视觉变化（如字重加粗、填充变化、下划线等）
2. 或将激活态粉色加深至 #FF87A0 以提升对比度至约 3.5:1
3. 仅将品牌粉用于装饰性图标（如 Heart 喜爱）而非信息传递

### 禁用态

| 元素 | 前景色 | 背景色 | 对比度 | 说明 |
|------|--------|--------|--------|------|
| 禁用图标 #4A4A6A @ 30% | rgba(74,74,106,0.30) | #FFFFFF | 约 2.0:1 | 刻意低对比表示不可用，符合规范（禁用元素豁免） |

---

## 焦点状态（Keyboard Focus）

### Web 端焦点样式

| 属性 | 规范值 |
|------|--------|
| 焦点轮廓样式 | 2dp 实线外框 |
| 轮廓颜色 | #4A4A6A（默认图标色）或 #FFB7C5（激活态） |
| 轮廓偏移 | 2dp（不紧贴图标边缘） |
| 轮廓圆角 | 12dp（与图标背景圆角一致） |
| 不得隐藏焦点 | 禁止使用 `outline: none` 而不提供替代焦点样式 |

**具体样式：**
```
IconButton 焦点态：
- border: 2px solid #4A4A6A
- border-radius: 12px
- outline-offset: 2px
```

---

## 文字可读性

### 图标配套标签文字

| 元素 | 最小字号 | 字重 | 对比度要求 |
|------|---------|------|----------|
| NavItem 标签 | 10px | Regular | ≥ 4.5:1（小文字WCAG AA） |
| 工具栏提示文字 | 12px | Regular | ≥ 4.5:1 |

**注意：** 10px 中文属于极小字号，必须保证字重不低于 Regular(400)，建议图标标签使用 Medium(500)。

### 可读性建议

- NavItem 未选中标签：#4A4A6A @ 60% 在白色背景上约 3.7:1，刚好低于 AA 标准
- **建议** 未选中标签颜色调整为 #6A6A8A（提升至约 4.6:1）

---

## ARIA 建议

### 图标组件 ARIA 属性

| 场景 | 推荐属性 | 示例值 |
|------|---------|--------|
| 纯装饰图标（无操作） | `aria-hidden="true"` | 隐藏，避免屏幕阅读器读取 |
| 可点击图标按钮 | `role="button"` + `aria-label` | `aria-label="发送消息"` |
| 状态切换图标 | `aria-pressed` 或 `aria-checked` | `aria-pressed="true/false"` |
| 导航标签 | `role="link"` 或 `aria-current` | `aria-current="page"`（当前页） |
| 禁用图标按钮 | `aria-disabled="true"` | 保持可聚焦但无操作 |
| 加载状态 | `aria-busy="true"` | 配合 Loading 状态 |
| 图标 + 文字配对 | 图标用 `aria-hidden="true"` | 文字提供语义，图标纯视觉 |

### 36 个图标的 ARIA Label 建议

| 图标 | 推荐 aria-label |
|------|----------------|
| home | "首页" |
| chat | "聊天" |
| ai-companion | "AI伴侣" |
| settings | "设置" |
| profile | "个人资料" |
| search | "搜索" |
| send | "发送消息" |
| microphone | "语音输入" |
| microphone-off | "语音已禁用" |
| emoji | "选择表情" |
| sticker | "选择贴纸" |
| add | "添加" |
| play | "播放" |
| pause | "暂停" |
| waveform | "录音中" |
| volume-up | "音量" |
| mute | "已静音" |
| headphone | "耳机模式" |
| lock | "隐私锁定" |
| key | "解锁" |
| bell | "通知" |
| moon | "夜间模式" |
| sun | "日间模式" |
| globe | "语言设置" |
| gift | "礼物" |
| coupon | "优惠券" |
| star | "收藏" |
| sparkle | "AI特效" |
| crown | "VIP会员" |
| heart | "喜爱" |
| arrow-left | "返回" |
| arrow-right | "前进" |
| close | "关闭" |
| check | "确认" |
| more | "更多操作" |
| trash | "删除" |

---

## Keyboard Navigation（键盘导航）

### 焦点顺序

| 顺序规则 | 说明 |
|---------|------|
| Tab 顺序 | 遵循视觉从左到右、从上到下的自然顺序 |
| 底部导航 | Tab 可在各 NavItem 间移动，Enter/Space 激活 |
| 工具栏 | Tab 在各 IconButton 间移动，无需进入内部 |
| 弹窗内焦点陷阱 | 模态弹窗打开时，Tab 焦点限制在弹窗内循环 |
| 返回 | 弹窗关闭后，焦点回到触发图标 |

### 快捷键建议

| 功能 | 快捷键 |
|------|--------|
| 激活图标按钮 | Enter 或 Space |
| 导航 NavItem 切换 | Tab / Shift+Tab |
| 关闭弹窗 | Escape |
| 提交/发送 | Ctrl+Enter 或 Enter |

---

## Screen Reader（屏幕阅读器）支持

### iOS VoiceOver

| 要求 | 实施方式 |
|------|---------|
| 每个 IconButton 必须有可读标签 | `accessibilityLabel` 属性 |
| 状态变化需播报 | `accessibilityValue` 或 `accessibilityHint` |
| 禁用状态播报 | `accessibilityTraits: .notEnabled` |
| 图标装饰性时隐藏 | `accessibilityElementsHidden = true` |

**示例（MicrophoneOff）：**
- 正常态：VoiceOver 读 "语音输入，按钮"
- 禁用态：VoiceOver 读 "语音已禁用，按钮，变暗"

### Android TalkBack

| 要求 | 实施方式 |
|------|---------|
| 内容描述 | `contentDescription` 属性 |
| 状态播报 | `stateDescription` |
| 禁用状态 | `isEnabled = false` 自动播报 |
| 分组元素 | `importantForAccessibility` |

---

## 移动端操作建议

### 手势操作

| 手势 | 图标组件响应 |
|------|------------|
| 单指点击 | 激活图标按钮默认动作 |
| 长按 | 显示图标功能提示（Tooltip） |
| 滑动（左/右） | 不作用于单个图标按钮，由父容器处理 |
| 双指捏合 | 不作用于图标按钮 |

### 防误触建议

| 场景 | 建议 |
|------|------|
| 危险操作图标（Trash） | 要求二次确认，不允许单次点击执行删除 |
| 发送按钮（Send） | 防止重复点击（点击后立即禁用，响应完成后恢复） |
| 关闭按钮（Close） | 提供充足的 44dp 触控区域，减少误关闭 |

### 视觉辅助

| 建议 | 说明 |
|------|------|
| 图标+文字配对 | 对于导航等关键图标，始终配合文字标签，不依赖单独图标传达语义 |
| 避免纯色区分 | 不使用单一颜色区分图标状态，始终配合形状、尺寸、文字等多维信息 |
| 动效可关闭 | 提供关闭图标动效的系统设置选项（遵循 `prefers-reduced-motion`） |

---

## WCAG 合规摘要

| 成功标准 | 等级 | 状态 | 说明 |
|---------|------|------|------|
| 1.1.1 非文本内容 | A | 需实施 | 所有图标按钮需 aria-label |
| 1.4.3 对比度（普通） | AA | 部分不达标 | 品牌粉激活态需补救 |
| 1.4.11 非文本对比度 | AA | 达标 | 默认图标色 8.5:1 |
| 2.1.1 键盘可访问 | A | 需实施 | IconButton 需键盘可聚焦 |
| 2.4.3 焦点顺序 | A | 需实施 | Tab 顺序遵循视觉顺序 |
| 2.4.7 焦点可见 | AA | 需实施 | 焦点轮廓必须可见 |
| 2.5.3 名称中包含标签 | A | 需实施 | aria-label 与视觉标签匹配 |
| 2.5.5 目标尺寸 | AAA | 需实施 | 44×44dp 触控目标 |
| 4.1.2 名称/角色/值 | A | 需实施 | role + aria 属性完整 |
