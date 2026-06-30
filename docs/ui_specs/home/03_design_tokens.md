# 03 Design Tokens — 首页 Home

## Color

### 基础调色板
| Token 名称 | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-primary` | `#FFB7C5` | 樱花粉：CTA 按钮文字、Active Tab 图标/文字/指示器、未读红点 |
| `color-secondary` | `#A7C7E7` | 天蓝色：（本页面未直接使用，保留 Token） |
| `color-accent` | `#C8B6FF` | 薰衣草紫：宝珠渐变之一、切换角色图标颜色 |
| `color-background` | `#FFF0F3` | 奶油粉：全局页面底色 |
| `color-surface` | `#FFF8F3` | 奶油白：快速操作瓷砖背景、对话行背景 |
| `color-surface-card` | `rgba(255,255,255,0.60)` | 英雄卡片底部信息区玻璃层背景（估算值） |
| `color-glass` | `rgba(255,255,255,0.55)` | 毛玻璃组件通用背景色 |
| `color-border` | `rgba(255,183,197,0.25)` | 卡片/瓷砖边框（粉色半透明，估算值） |
| `color-divider` | `rgba(58,58,74,0.08)` | 分隔线（本页面暂未显示明确分隔线） |
| `color-text-primary` | `#3A3A4A` | 主文字：角色名称、标题、"yuoyuo" App 名 |
| `color-text-secondary` | `#8E8E9A` | 次级文字：对话预览文字、时间戳、状态文字 |
| `color-text-placeholder` | `#BDBDC8` | 占位文字（本页面未使用） |
| `color-overlay` | `rgba(0,0,0,0.20)` | 遮罩层（本页面未使用） |
| `color-success` | `#72C472` | 成功状态绿色（本页面未使用） |
| `color-warning` | `#FFD166` | 警告色（本页面未使用） |
| `color-danger` | `#FF6B6B` | 危险/错误色（本页面未使用） |
| `color-info` | `#A7C7E7` | 信息色（本页面未使用） |
| `color-tab-inactive` | `#ADADB8` | Tab 非激活状态图标与文字色 |
| `color-tab-active` | `#FFB7C5` | Tab 激活状态图标与文字色（等同 primary） |
| `color-unread-badge` | `#FFB7C5` | 未读消息角标红点色（即樱花粉，非纯红） |
| `color-cta-text` | `#FF7A9A` | "开始聊天 →"按钮文字（比 primary 深，估算值）|
| `color-app-name` | `#3A3A4A` | "yuoyuo" 字体颜色 |

---

## Gradient

| Token 名称 | 起点颜色 | 终点颜色 | 方向 | 透明度 | 用途 |
|-----------|---------|---------|------|--------|------|
| `gradient-hero-sky` | `#F5D89C`（暖黄） | `#D0A8D8`（浅紫粉） | 从底部→顶部（270°） | 100% | 英雄卡片云彩背景底色渐变 |
| `gradient-hero-sky-mid` | `#F4C0CF`（粉） | `#C5A9E0`（紫） | 水平左→右（90°） | 100% | 英雄卡片云彩背景中层 |
| `gradient-orb-body` | `#FFB7C5`（粉） | `#A89FD8`（蓝紫） | 从右上→左下（135°） | 100% | 心形宝珠主体渐变 |
| `gradient-orb-shine` | `rgba(255,255,255,0.80)` | `rgba(255,255,255,0.0)` | 从左上→右下（45°） | 渐变透明 | 宝珠高光内反射 |
| `gradient-orb-glow` | `rgba(200,182,255,0.60)` | `rgba(200,182,255,0.0)` | 径向（Radial，从中心向外）| 渐变透明 | 宝珠外发光光晕 |
| `gradient-background-page` | `#FFF0F3` | `#FFF0F3` | 纯色（无渐变） | 100% | 页面底色 |
| `gradient-tab-bar-blur` | `rgba(255,248,243,0.90)` | `rgba(255,248,243,1.0)` | 从顶→底（180°） | — | Tab Bar 背景模糊叠加 |

> 注：英雄卡片云彩背景为复合多层渐变，有云朵插图叠加，估算自截图色值。

---

## Radius

| Token 名称 | 值 | 使用场景 |
|-----------|---|---------|
| `radius-xs` | 4 pt | 极小元素（未直接使用） |
| `radius-sm` | 8 pt | 小型角标、Tag（未直接使用） |
| `radius-md` | 12 pt | 中型组件（未直接使用） |
| `radius-lg` | 16 pt | 快速操作瓷砖、"开始聊天"按钮 |
| `radius-xl` | 20 pt | 英雄卡片（估算值，实测约 20-24 pt） |
| `radius-2xl` | 24 pt | 英雄卡片主卡（采用此值） |
| `radius-full` | 9999 pt | 头像圆形、Tab Active 指示器点 |
| `radius-orb` | — | 心形宝珠为不规则心形路径，非 CSS 圆角 |

---

## Shadow

| Token 名称 | 颜色 | 透明度 | Blur | Offset X | Offset Y | Spread | 使用场景 |
|-----------|------|--------|------|----------|----------|--------|---------|
| `shadow-card` | `#FFB7C5` | 15% | 20 pt | 0 | 4 pt | -2 pt | 英雄卡片底部阴影（估算值） |
| `shadow-tile` | `#3A3A4A` | 6% | 8 pt | 0 | 2 pt | 0 | 快速操作瓷砖阴影（估算值） |
| `shadow-orb-glow` | `#C8B6FF` | 50% | 40 pt | 0 | 0 | 0 | 宝珠外发光（径向模糊，估算值） |
| `shadow-avatar` | `#3A3A4A` | 10% | 6 pt | 0 | 2 pt | 0 | 角色头像边缘阴影（估算值） |
| `shadow-tab-bar` | `#3A3A4A` | 8% | 12 pt | 0 | -2 pt | 0 | Tab Bar 顶部阴影（估算值） |
| `shadow-user-avatar` | `#FFB7C5` | 30% | 8 pt | 0 | 2 pt | 0 | 右上角用户头像发光边框（估算值） |

---

## Blur

| Token 名称 | 值 | 使用场景 |
|-----------|---|---------|
| `blur-glass-card` | 16 pt | 英雄卡片信息区毛玻璃背景（估算值） |
| `blur-glass-tile` | 8 pt | 快速操作瓷砖毛玻璃（估算值） |
| `blur-tab-bar` | 20 pt | Tab Bar 背景模糊（估算值） |
| `blur-orb-glow` | 40 pt | 宝珠外发光模糊半径（估算值） |

---

## Opacity

| Token 名称 | 值 | 使用场景 |
|-----------|---|---------|
| `opacity-glass-card` | 0.60 | 英雄卡片信息区玻璃背景（估算值） |
| `opacity-glass-tile` | 0.80 | 快速操作瓷砖（估算值） |
| `opacity-tab-bar` | 0.92 | Tab Bar 背景（估算值） |
| `opacity-cloud-layer` | 0.85 | 云朵插图叠加在渐变背景上（估算值） |
| `opacity-orb-shine` | 0.80 | 宝珠高光反射（估算值） |
| `opacity-border` | 0.25 | 卡片边框半透明（估算值） |
| `opacity-text-secondary` | 0.55 | 次级文字在卡片内的透明度（估算值） |

---

## Typography

### 字体族
| Token 名称 | 字体栈 | 用途 |
|-----------|-------|------|
| `font-family-chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` | 所有中文文字 |
| `font-family-latin` | `SF Pro Rounded, -apple-system, sans-serif` | 数字、英文、App 名 |

### 字号 / 字重 / 行高 / 颜色体系
| 层级 | Token 名称 | 字号 | 字重 | 行高 | 字间距 | 颜色 Token | 示例文字 |
|------|-----------|------|------|------|--------|-----------|---------|
| Display | `type-display` | 28 pt（估算） | Bold (700) | 1.2 | -0.5 pt | `color-text-primary` | — |
| App Name | `type-app-name` | 26 pt（估算） | Bold (700) | 1.0 | -0.3 pt | `color-text-primary` | "yuoyuo" |
| Title / H1 | `type-title-lg` | 22 pt（估算） | SemiBold (600) | 1.3 | -0.3 pt | `color-text-primary` | "神无月凛"（英雄卡片） |
| Headline / H2 | `type-headline` | 16 pt（估算） | SemiBold (600) | 1.4 | 0 | `color-text-primary` | 对话列表角色名 |
| Section Label | `type-section-label` | 16 pt（估算） | Bold (700) | 1.3 | 0 | `color-text-primary` | "最近的......" |
| Body | `type-body` | 14 pt（估算） | Regular (400) | 1.5 | 0 | `color-text-secondary` | 对话预览文字 |
| Caption | `type-caption` | 13 pt（估算） | Regular (400) | 1.4 | 0 | `color-text-secondary` | 状态文字 "刚刚和你聊过 · 心情：温柔"、时间戳 |
| Tab Label | `type-tab-label` | 10 pt（估算） | Regular (400) | 1.2 | 0 | `color-tab-active/inactive` | "首页""聊天"等 |
| CTA | `type-cta` | 15 pt（估算） | Medium (500) | 1.0 | 0 | `color-cta-text` | "开始聊天 →" |
| View All | `type-view-all` | 13 pt（估算） | Regular (400) | 1.0 | 0 | `color-text-secondary` | "查看全部 >" |

---

## Spacing Scale
| Token 名称 | 值 | 主要用途 |
|-----------|---|---------|
| `space-1` | 4 pt | 图标与文字最小间距、Tab Active 点大小 |
| `space-2` | 8 pt | 图标下方文字间距（瓷砖内）、对话行间距 |
| `space-3` | 12 pt | 瓷砖 Gap、卡片内元素间距 |
| `space-4` | 16 pt | 页面水平内边距（卡片）、按钮内边距 |
| `space-5` | 20 pt | 页面水平内边距（文字区）、Section 上边距 |
| `space-6` | 24 pt | Hero Card 圆角、Section 间距 |
| `space-8` | 32 pt | 大块区域间距 |
| `space-10` | 40 pt | 英雄卡片内顶部内边距（估算值） |
| `space-12` | 48 pt | — |
| `space-16` | 64 pt | — |

---

## Motion

| Token 名称 | 值 | 用途 |
|-----------|---|------|
| `duration-fast` | 150 ms | 按钮 pressed 状态、Tab 切换图标色变化 |
| `duration-normal` | 250 ms | 卡片出现、列表行进入 |
| `duration-slow` | 400 ms | 页面级进场动画、英雄卡片展开 |
| `duration-orb-pulse` | 2000 ms | 宝珠脉冲发光循环 |
| `delay-stagger` | 50 ms | 列表行交错进入延迟（每行递增） |
| `easing-standard` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | 标准运动曲线（Material Motion） |
| `easing-decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 元素进入屏幕 |
| `easing-accelerate` | `cubic-bezier(0.4, 0.0, 1.0, 1)` | 元素离开屏幕 |
| `easing-spring` | `spring(1, 160, 18, 0)` | 弹性动画（宝珠浮动、按钮 bounce） |
