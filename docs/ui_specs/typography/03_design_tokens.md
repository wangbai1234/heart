# 03 Design Tokens — Typography Specimen（字样规范）

## 一、颜色 Tokens（Color）

### 基础调色板

| Token 名称 | HEX 值 | 用途说明 |
|------------|--------|----------|
| `color.primary` | `#FFB7C5` | 樱花粉；级别标签文字（Display/Title/Headline等）、粉色圆点装饰 |
| `color.secondary` | `#A7C7E7` | 天蓝；用户端聊天气泡背景色 |
| `color.accent` | `#C8B6FF` | 薰衣草紫；本看板未直接使用，为系统保留 |
| `color.surface` | `#FFF8F3` | 奶油白；画布背景色、浅色模式卡片背景 |
| `color.ink` | `#3A3A4A` | 炭黑；主要正文文字、标题文字 |
| `color.ink.secondary` | `#6B6B7E` | 次要文字（估算值，字体注释灰色） |
| `color.placeholder` | `#8A8A98` | 辅助文字颜色；Caption 级别明确标注此色值 |

### 文字颜色层级

| Token 名称 | 值 | 使用场景 |
|------------|-----|----------|
| `color.text.primary` | `#3A3A4A` | Display、Title、Headline、Body 级文字 |
| `color.text.secondary` | `#8A8A98` | Caption 级文字（刚刚 · 已读）；设计稿明确标注 |
| `color.text.tabular` | `#3A3A4A` | Tabular 数字（时间戳、时长） |
| `color.text.label` | `#FFB7C5` | 字级标签文字（Display / Title / Headline / Body / Caption / Tabular） |
| `color.text.annotation` | `#8A8A98` | 字体注释小字（PingFang SC SemiBold + SF Pro Rounded 等） |

### 深色模式颜色（Dark Mode Card 观察值）

| Token 名称 | 估算值 | 用途 |
|------------|--------|------|
| `color.dark.background` | `#2A2A38`（估算值） | 深色模式卡片背景 |
| `color.dark.surface` | `#3A3A48`（估算值） | 深色模式 AI 气泡背景 |
| `color.dark.bubble.user` | `#4A4A62`（估算值） | 深色模式用户气泡背景 |
| `color.dark.text.primary` | `#F0F0F8`（估算值） | 深色模式主要文字 |
| `color.dark.text.secondary` | `#9090A0`（估算值） | 深色模式次要文字（已读、时间） |

### 语义颜色

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `color.semantic.success` | `#52C41A`（估算值） | 消息已读 ✓ 勾（蓝绿色调） |
| `color.bubble.ai.light` | `#FFFFFF` 或 `#FFF8F3` | 浅色模式 AI 气泡背景 |
| `color.bubble.user.light` | `#A7C7E7` | 浅色模式用户气泡背景（天蓝） |

---

## 二、渐变 Tokens（Gradient）

本看板未展示明显的渐变背景；画布背景为纯色 #FFF8F3。

| Token 名称 | 起点 | 终点 | 方向 | 透明度 | 用途 |
|------------|------|------|------|--------|------|
| `gradient.canvas.bg` | `#FFF8F3` | `#FFF8F3` | — | 100% | 画布背景（纯色，无渐变） |

> 注：渐变 Tokens 将在后续屏幕（如 Chat Screen、Onboarding）中完整定义；本字体看板不包含渐变元素。

---

## 三、圆角 Tokens（Radius）

| Token 名称 | 值（估算值） | 用途 |
|------------|-------------|------|
| `radius.sm` | `8 px` | 字体注释标签、小型装饰元素 |
| `radius.md` | `12 px` | 聊天气泡圆角 |
| `radius.lg` | `16 px` | 浅色/深色模式预览卡片外框 |
| `radius.xl` | `20 px` | 大型卡片（保留） |
| `radius.full` | `999 px` | Aa 图标圆形背景 |

---

## 四、阴影 Tokens（Shadow）

| Token 名称 | 颜色 | 透明度 | Blur | X Offset | Y Offset | Spread | 场景 |
|------------|------|--------|------|----------|----------|--------|------|
| `shadow.card.light` | `#3A3A4A` | 6%（估算值） | 16 px | 0 | 4 px | 0 | 浅色模式预览卡片投影 |
| `shadow.card.dark` | `#000000` | 20%（估算值） | 24 px | 0 | 8 px | 0 | 深色模式预览卡片投影 |
| `shadow.bubble` | `#FFB7C5` | 8%（估算值） | 8 px | 0 | 2 px | 0 | AI 气泡柔光（估算值） |

---

## 五、模糊 Tokens（Blur / Glassmorphism）

本看板为字体展示规范板，未使用毛玻璃效果。

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `blur.glass.sm` | `8 px` | 保留（用于聊天输入框等场景） |
| `blur.glass.md` | `16 px` | 保留（用于弹窗、底部导航栏等场景） |

---

## 六、不透明度 Tokens（Opacity）

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `opacity.annotation` | `60%` | 字体注释小字视觉权重 |
| `opacity.dot.label` | `100%` | 字级标签圆点 |
| `opacity.disabled` | `40%` | 禁用态文字（本看板未直接展示） |

---

## 七、字体 Tokens（Typography）—— 核心定义

### 字体家族

| Token 名称 | 值 | 适用语言 | 特点 |
|------------|-----|----------|------|
| `font.family.zh` | `"PingFang SC", "HarmonyOS Sans SC"` | 中文 | 圆润几何，柔和气质 |
| `font.family.latin` | `"SF Pro Rounded"` | 拉丁/英文 | 圆角末端，友好可读性高 |
| `font.family.tabular` | `"SF Pro Rounded"` + `font-variant-numeric: tabular-nums` | 数字（等宽） | 等宽数字，时间/数据对齐整洁 |

### 字号阶梯（Type Scale）

| 级别 | Token 名称 | Font Size | Line Height | Font Weight | Font Family | 颜色 Token | 用途 |
|------|------------|-----------|-------------|-------------|-------------|-----------|------|
| Display | `type.display` | **40 px** | **48 px** | SemiBold（600） | PingFang SC + SF Pro Rounded | `color.text.primary` | 情感标语、欢迎语、大标题 |
| Title | `type.title` | **28 px** | **36 px** | Medium（500） | PingFang SC | `color.text.primary` | 页面标题、章节名 |
| Headline | `type.headline` | **22 px** | **30 px** | Medium（500） | PingFang SC | `color.text.primary` | 卡片标题、列表大标题 |
| Body | `type.body` | **16 px** | **24 px** | Regular（400） | PingFang SC | `color.text.primary` | 正文、聊天气泡内容 |
| Caption | `type.caption` | **13 px** | **18 px** | Regular（400） | PingFang SC | `#8A8A98`（`color.text.secondary`） | 时间戳、已读状态、辅助说明 |
| Tabular | `type.tabular` | **14 px** | **（等同 Caption，约 20 px）**（估算值） | Regular（400） | SF Pro Rounded Tabular | `color.text.primary` | 数字时间戳（12:34）、时长（32m） |

> 注：Line Height 值直接来自设计稿标注（格式为 fontSize/lineHeight）。

### 字间距（Letter Spacing）

设计稿未明确标注字间距数值，保持字体默认值：

| 级别 | 字间距 | 说明 |
|------|--------|------|
| Display | 0（默认） | 大字号下默认间距已足够宽松 |
| Title / Headline | 0（默认） | 中文字体通常不额外调整 |
| Body | 0（默认） | 正文使用默认间距保持自然 |
| Caption | 0（默认） | — |
| Tabular | 0（使用 tabular-nums） | 等宽数字通过 font-variant 实现 |

---

## 八、间距比例 Tokens（Spacing Scale）

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `spacing.xs` | `4 px` | 气泡内小间距 |
| `spacing.sm` | `8 px` | 组件内 Padding |
| `spacing.md` | `12 px` | 气泡垂直 Padding |
| `spacing.lg` | `16 px` | 气泡水平 Padding、组件间距 |
| `spacing.xl` | `24 px` | 卡片间距、大间距 |
| `spacing.2xl` | `32 px` | 字级行间距 |
| `spacing.3xl` | `40 px` | Header 下方 Margin |
| `spacing.4xl` | `48 px` | 画布垂直边距 |
| `spacing.5xl` | `64 px` | 画布水平边距 |

---

## 九、动效 Tokens（Motion）

N/A for this asset type — 字体规范看板不涉及动效定义。

以下为通用系统保留 Token（供其他屏幕参考）：

| Token 名称 | 值 | 用途场景 |
|------------|-----|----------|
| `motion.duration.fast` | `150 ms` | 微交互（按钮按压） |
| `motion.duration.normal` | `250 ms` | 标准过渡（页面切换） |
| `motion.duration.slow` | `400 ms` | 情感动画（角色出场） |
| `motion.easing.ease-out` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 进入动画 |
| `motion.easing.spring` | `spring(1, 80, 10, 0)` | 弹性交互 |
