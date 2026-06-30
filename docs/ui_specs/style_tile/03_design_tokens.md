# 03 Design Tokens — Style Tile（视觉总谱）

> 所有 Token 均直接提取自 PNG 视觉稿。带（估算值）标注者为目视估算。
> Token 命名采用 kebab-case，与 CSS 自定义属性及 Tailwind v4 Theme 兼容。

---

## 颜色 Color Tokens

### 品牌主色

| Token 名称 | Hex / RGBA | 用途 |
|------------|-----------|------|
| `color-primary` | `#FFB7C5` | 樱花粉；Primary 按钮填充、AI 气泡文字色（sender name）、爱心图标 |
| `color-secondary` | `#A7C7E7` | 天蓝；用户气泡背景、辅助图标色 |
| `color-accent` | `#C8B6FF` | 薰衣草紫；点缀装饰、强调色 |

### 背景 / 表面

| Token 名称 | Hex / RGBA | 用途 |
|------------|-----------|------|
| `color-background` | `#FFF8F3` | 奶霜白；全局底色 |
| `color-surface` | `#FFF8F3` | 与 background 同色，卡片内部底色 |
| `color-surface-glass` | `rgba(255,255,255,0.55)` | 毛玻璃卡片背景（调色板标注） |
| `color-surface-card` | `rgba(255,255,255,0.80)` | 展示卡片白色背景（估算值，视觉较实） |
| `color-surface-bubble-ai` | `rgba(255,255,255,0.85)` | AI 气泡背景，偏白（估算值） |
| `color-surface-bubble-user` | `#A7C7E7` at ~80% opacity（估算值） | 用户气泡背景，天蓝半透明 |

### 文字

| Token 名称 | Hex | 用途 |
|------------|-----|------|
| `color-ink` | `#3A3A4A` | 深炭灰；主要正文、标题、时间戳 |
| `color-ink-secondary` | 约 `#7A7A8A`（估算值） | 次级说明文字（"AI（左侧）"等标注） |
| `color-ink-placeholder` | 约 `#B0B0C0`（估算值） | 占位文字（输入框等，Style Tile 未直接展示） |
| `color-ink-primary` | `#FFB7C5` | 品牌粉文字；AI 气泡中 "yuoyuo" sender name |
| `color-ink-link` | `#C8B6FF` | 文字链接色；"了解更多" 按钮文字 |
| `color-ink-secondary-label` | 约 `#9A9AB0`（估算值） | 图标标签文字、时间戳、说明文字 |

### 语义色

| Token 名称 | Hex | 用途 |
|------------|-----|------|
| `color-success` | 未在 Style Tile 中展示 | 设计稿未定义，建议 `#6FCF97` |
| `color-warning` | 未在 Style Tile 中展示 | 设计稿未定义，建议 `#F2C94C` |
| `color-error` | 未在 Style Tile 中展示 | 设计稿未定义，建议 `#EB5757` |
| `color-check-tick` | 约 `#A7C7E7`（估算值）| 用户气泡右下角已读对勾 ✓ |
| `color-star-inactive` | 约 `#E0D8F0`（估算值）| 温暖时刻星星图标（空心星） |

### 边框 / 分割线

| Token 名称 | Hex / RGBA | 用途 |
|------------|-----------|------|
| `color-border` | `rgba(255,255,255,0.60)`（估算值） | 卡片边框（视觉上几乎不可见，依赖阴影） |
| `color-divider` | `rgba(0,0,0,0.05)`（估算值） | 内容分割线（Style Tile 未直接展示） |

### 叠加层

| Token 名称 | RGBA | 用途 |
|------------|------|------|
| `color-overlay` | `rgba(0,0,0,0.35)`（估算值） | 模态底部遮罩（Style Tile 未展示，保留） |

---

## 渐变 Gradient Tokens

### 背景渐变

| Token 名称 | 描述 |
|------------|------|
| `gradient-background-top` | 方向：从上至下；起点：`#FFD6DD`（估算值，浅樱桃粉）约 0%；终点：`#FFF8F3` 约 40%；用途：画布顶部背景晕染 |
| `gradient-background-canvas` | 整体底色：线性从 `#FFE8EC` → `#FFF8F3`（估算值），用于 App 全局背景 |

### 按钮渐变

| Token 名称 | 描述 |
|------------|------|
| `gradient-button-primary` | Primary 按钮；方向：从左至右（或左上至右下）；起点：`#FFB7C5` → 终点：`#FFAAB8`（估算值，略深一阶）；用途："确认" 按钮 |
| `gradient-button-primary-hover` | hover/pressed 态：整体加深约 10%（设计稿未定义，参考建议） |

### 卡片/气泡渐变

| Token 名称 | 描述 |
|------------|------|
| `gradient-bubble-user` | 用户气泡：天蓝纯色（#A7C7E7）+ 白色混调（估算值），非明显渐变 |
| `gradient-card-avatar-bg` | 头像背景圆形：淡粉白渐变，从 `#FFE8EC` → `#FFF0F5`（估算值） |

---

## 圆角 Radius Tokens

| Token 名称 | 值（估算值） | 用途 |
|------------|-------------|------|
| `radius-none` | 0px | 无圆角 |
| `radius-xs` | 4px | 极小元素（徽章等） |
| `radius-sm` | 8px | 小型组件 |
| `radius-md` | 12px | 次要按钮、输入框 |
| `radius-lg` | 16px | 气泡、卡片内层 |
| `radius-xl` | 20px | 主卡片容器 |
| `radius-2xl` | 24px | Primary 按钮（"确认"） |
| `radius-pill` | 999px | 全圆角按钮、头像、颜色椭圆 |
| `radius-full` | 50% | 正圆形（头像、Icon 容器） |

**实测关键值：**
- 调色板颜色椭圆：`radius-pill`（长轴方向完全圆润）
- "确认" 按钮：`radius-pill`（胶囊形）
- "取消" 按钮：`radius-pill`（胶囊形，白底）
- AI/用户气泡：约 `radius-lg`（16px），用户气泡右下角为 `radius-xs`（尖角约 4px，估算值）
- 主卡片容器：`radius-xl`（20px，估算值）
- 头像圆形：`radius-full`

---

## 阴影 Shadow Tokens

| Token 名称 | 值（估算值） | 用途 |
|------------|-------------|------|
| `shadow-card` | `0 4px 16px rgba(0,0,0,0.06)` | 主内容卡片 |
| `shadow-button-primary` | `0 4px 12px rgba(255,183,197,0.45)` | Primary 按钮（樱花粉光晕） |
| `shadow-button-secondary` | `0 2px 8px rgba(0,0,0,0.05)` | Secondary 按钮 |
| `shadow-bubble` | `0 2px 8px rgba(0,0,0,0.04)` | 气泡轻微投影 |
| `shadow-avatar` | `0 4px 12px rgba(255,183,197,0.25)` | 头像圆形外发光（估算值） |
| `shadow-icon-bar` | 无（图标条直接贴合卡片） | — |

---

## 模糊 Blur Tokens

| Token 名称 | 值（估算值） | 用途 |
|------------|-------------|------|
| `blur-glass` | `12px` backdrop-filter blur | 毛玻璃卡片/气泡效果 |
| `blur-glow` | `20px`（估算值） | 按钮光晕、头像光晕 |
| `blur-background` | `0px`（底色无模糊） | — |

---

## 透明度 Opacity Tokens

| Token 名称 | 值 | 用途 |
|------------|----|----|
| `opacity-glass` | 0.55 | Glass 卡片背景（调色板标注） |
| `opacity-glass-card` | 0.80（估算值） | 展示卡片背景 |
| `opacity-glass-bubble` | 0.85（估算值） | AI 气泡背景 |
| `opacity-overlay` | 0.35（估算值） | 模态遮罩 |
| `opacity-disabled` | 0.40（估算值） | 禁用态元素 |
| `opacity-ink-secondary` | 0.55（估算值） | 次级文字 |
| `opacity-decoration` | 0.60（估算值） | 背景装饰粒子 |

---

## 字体排版 Typography Tokens

### 字体族

| Token 名称 | 字体值 | 用途 |
|------------|--------|------|
| `font-family-chinese` | `"PingFang SC", "HarmonyOS Sans SC", sans-serif` | 中文内容 |
| `font-family-latin` | `"SF Pro Rounded", "SF Pro Display", system-ui` | 英文 / 数字 |

### 字号层级（从 PNG 直接观测）

| Token 名称 | 字号（估算值） | 字重 | 行高（估算值） | 用途 |
|------------|---------------|------|---------------|------|
| `text-display` | 40px | Bold (700) | 1.2 | 中文大标题（"你今天还好吗" 第一行大字） |
| `text-title-lg` | 20px | Semibold (600) | 1.4 | 英文大标题（"Hello, yuoyuo."） |
| `text-title-md` | 18px | Semibold (600) | 1.4 | 卡片主标题（"yuoyuo"角色名） |
| `text-body` | 16px | Regular (400) | 1.5 | 正文（气泡内文字、"你今天还好吗" 第二行正文） |
| `text-body-sm` | 14px | Regular (400) | 1.5 | 次级说明（字体名标注 "PingFang SC Regular"） |
| `text-caption` | 12px | Regular (400) | 1.4 | 辅助标注（时间戳 "09:30"、"AI（左侧）"等） |
| `text-label` | 11px（估算值） | Regular (400) | 1.3 | 图标标签文字（"首页"、"聊天"等） |
| `text-hex-label` | 10px（估算值） | Regular (400) | 1.2 | 颜色 Hex 标注文字 |

### 字号 — 区块标题

| 用途 | 字号（估算值） | 颜色 | 字重 |
|------|---------------|------|------|
| 区块编号标题（"1. 调色板" 等） | 14px | `#3A3A4A` ~60% opacity | Regular (400) |

### 字距

| Token 名称 | 值 | 用途 |
|------------|----|----|
| `letter-spacing-tight` | -0.5px（估算值） | 大标题中文 |
| `letter-spacing-normal` | 0px | 正文 |
| `letter-spacing-wide` | 0.5px（估算值） | 图标标签文字 |
| `letter-spacing-logo` | 约 1px（估算值） | "yuoyuo" Logo 字 |

---

## 间距 Spacing Scale

| Token 名称 | 值 | 用途 |
|------------|----|----|
| `spacing-1` | 4px | 极小间距（标注、徽章内边距） |
| `spacing-2` | 8px | 颜色椭圆间距、气泡内 padding 垂直 |
| `spacing-3` | 12px | 按钮间距、列表行距 |
| `spacing-4` | 16px | 卡片网格间距、气泡内 padding 水平 |
| `spacing-5` | 20px | 卡片内边距 |
| `spacing-6` | 24px | 画布外边距 |
| `spacing-8` | 32px | Logo 距左边距 |
| `spacing-10` | 40px | Logo 距顶距离 |
| `spacing-16` | 64px（估算值） | 区块大间距 |

---

## 动效 Motion Tokens

> Style Tile 为静态资产，以下 Token 为设计系统推断值，供后续屏幕规格引用。

| Token 名称 | 值 | 用途 |
|------------|----|----|
| `duration-instant` | 0ms | 即时反馈（纯状态切换） |
| `duration-fast` | 150ms | 按钮 pressed 态颜色变化 |
| `duration-normal` | 250ms | 卡片出现、气泡入场 |
| `duration-slow` | 400ms | 页面过渡、模态弹出 |
| `duration-extra-slow` | 600ms | 角色插画加载淡入 |
| `delay-stagger` | 50ms | 列表/图标逐项入场延迟 |
| `easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | 默认缓动（Material Design standard） |
| `easing-decelerate` | `cubic-bezier(0.0, 0, 0.2, 1)` | 元素进入屏幕 |
| `easing-accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | 元素离开屏幕 |
| `easing-spring` | `spring(1, 100, 10, 0)` | 弹簧动效（按钮按下回弹、卡片展开） |
