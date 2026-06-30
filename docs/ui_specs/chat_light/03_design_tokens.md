# 03 Design Tokens — 聊天页 Chat（浅色模式）

## Color

### Brand / Semantic Colors
| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-primary` | `#FFB7C5` | 樱花粉；发送按钮背景、播放按钮图标色、Typing 圆点色 |
| `color-secondary` | `#A7C7E7` | 天蓝；User 消息 Bubble 背景色 |
| `color-accent` | `#C8B6FF` | 薰衣草；背景光晕辅助色、波形渐变终点色 |
| `color-surface` | `#FFF8F3` | 奶油白；背景渐变起始色 |
| `color-glass` | `rgba(255, 255, 255, 0.55)` | 毛玻璃基础透明度；Header 背景 |
| `color-glass-light` | `rgba(255, 255, 255, 0.75)` | 较高透明度毛玻璃；AI Bubble 背景、Voice Bubble 背景 |
| `color-glass-composer` | `rgba(255, 255, 255, 0.65)` | Composer 输入框背景毛玻璃 |

### Background Colors
| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-bg-top` | `#FFF0EC` | 背景渐变顶部颜色（估算值） |
| `color-bg-bottom` | `#E8D5F5` | 背景渐变底部颜色（估算值） |
| `color-bg-glow-center` | `rgba(255, 255, 255, 0.40)` | 中央椭圆白色光晕（估算值） |
| `color-bg-glow-purple` | `rgba(200, 182, 255, 0.30)` | 右下角薰衣草光晕（估算值） |

### Text Colors
| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-text-primary` | `#3A3A4A` | 主要文字色；AI Bubble 文字、角色名、Header 元素 |
| `color-text-secondary` | `#888888` | 次要文字色；在线状态"温柔在线"文字（估算值） |
| `color-text-caption` | `#AAAAAA` | 辅助说明文字；"AI朗读 · 可点击播放"、时长"0:18"（估算值） |
| `color-text-placeholder` | `#BBBBBB` | Placeholder 文字；"想和小屿说点什么..."（估算值） |
| `color-text-date` | `#999999` | 日期分隔符文字（估算值） |
| `color-text-on-primary` | `#FFFFFF` | User Bubble 文字（白色，在蓝色背景上） |
| `color-text-on-surface` | `#FFFFFF` | 发送按钮图标色 |

### Border / Divider
| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-border` | `rgba(255, 255, 255, 0.60)` | Bubble/Card 边框（若有，极细，估算值） |
| `color-divider` | `rgba(0, 0, 0, 0.06)` | Header 底部分隔线阴影色（估算值） |

### Status Colors
| Token Name | Hex | 用途 |
|------------|-----|------|
| `color-online` | `#5FC8E8` | 在线状态蓝点（估算值） |
| `color-success` | `#6DD5A0` | 备用成功色（当前页未使用） |
| `color-warning` | `#FFD580` | 备用警告色（当前页未使用） |
| `color-danger` | `#FF6B6B` | 备用危险色（当前页未使用） |
| `color-info` | `#A7C7E7` | 信息色（复用 Secondary） |

### Overlay
| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-overlay` | `rgba(0, 0, 0, 0.40)` | 全局遮罩（当前页未激活） |
| `color-overlay-light` | `rgba(0, 0, 0, 0.20)` | 轻量遮罩（当前页未激活） |

---

## Gradient

| Token Name | 起点颜色 | 终点颜色 | 方向 | 透明度 | 用途 |
|------------|---------|---------|------|--------|------|
| `gradient-bg-main` | `#FFF0EC` | `#E8D5F5` | 180°（从上到下） | 100% | 页面背景主渐变（估算值） |
| `gradient-wave-pink` | `#FFB7C5` | `#C8B6FF` | 90°（从左到右） | 100% | Voice Bubble 波形颜色渐变（估算值） |
| `gradient-send-btn` | `#FFB7C5` | `#FFB7C5` | 无渐变（实色） | 100% | 发送按钮背景（实色）（估算值） |
| `gradient-bg-glow` | `rgba(255,255,255,0.4)` | `rgba(255,255,255,0)` | 径向渐变（圆心到边缘） | — | 页面中央白色光晕（估算值） |

---

## Radius

| Token Name | 值 | 使用场景 |
|------------|---|---------|
| `radius-xs` | 4 pt | 极小元素（当前页未明确使用） |
| `radius-sm` | 6 pt | AI Bubble 左下角（气泡尾部）（估算值） |
| `radius-md` | 12 pt | 中等卡片（当前页未明确使用） |
| `radius-lg` | 20 pt | AI Bubble 其余三角、User Bubble 主圆角（估算值） |
| `radius-xl` | 24 pt | Header 底部圆角（估算值） |
| `radius-2xl` | 32 pt | Composer 输入框（胶囊形）（估算值） |
| `radius-full` | 9999 pt | 圆形按钮（发送按钮、头像、在线圆点） |

---

## Shadow

| Token Name | 颜色 | 透明度 | Blur | X Offset | Y Offset | Spread | 使用场景 |
|------------|-----|--------|------|----------|----------|--------|---------|
| `shadow-header` | `#000000` | 6% | 12 pt | 0 | 2 pt | 0 | Header 底部柔和投影（估算值） |
| `shadow-composer` | `#000000` | 8% | 16 pt | 0 | -4 pt | 0 | Composer 顶部向上阴影（估算值） |
| `shadow-bubble` | `#FFB7C5` | 10% | 8 pt | 0 | 2 pt | 0 | AI Bubble 轻微粉色投影（估算值） |
| `shadow-send-btn` | `#FFB7C5` | 30% | 12 pt | 0 | 4 pt | 0 | 发送按钮粉色光晕阴影（估算值） |

---

## Blur

| Token Name | 值 | 使用场景 |
|------------|---|---------|
| `blur-glass-sm` | 10 pt | 轻量毛玻璃（当前页备用） |
| `blur-glass-md` | 20 pt | Header 毛玻璃效果（估算值） |
| `blur-glass-lg` | 24 pt | Composer 毛玻璃效果（估算值） |
| `blur-bg-glow` | 40 pt | 背景光晕模糊（估算值） |

---

## Opacity

| Token Name | 值 | 使用场景 |
|------------|---|---------|
| `opacity-glass-header` | 55% | Header 背景白色不透明度 |
| `opacity-glass-bubble` | 75% | AI Bubble 白色背景不透明度 |
| `opacity-glass-composer` | 65% | Composer 白色背景不透明度 |
| `opacity-bg-glow` | 40% | 页面背景中央光晕 |
| `opacity-bg-glow-purple` | 30% | 页面背景紫色光晕 |
| `opacity-disabled` | 40% | 禁用状态（当前页未激活） |

---

## Typography

### 字体族
| 用途 | 字体族 | Fallback |
|------|-------|---------|
| 中文主字体 | PingFang SC | HarmonyOS Sans SC, Noto Sans SC, system-ui |
| 拉丁/数字字体 | SF Pro Rounded | -apple-system, BlinkMacSystemFont |

### 文字层级规范
| Token Name | 字号 | 字重 | 行高 | 字间距 | 颜色 | 用途 |
|------------|-----|------|------|--------|------|------|
| `text-display` | 24 pt | 700 | 1.3 | -0.5 | `color-text-primary` | 大标题（当前页未使用） |
| `text-title` | 20 pt | 600 | 1.4 | -0.3 | `color-text-primary` | 页面标题（当前页未使用） |
| `text-headline` | 17 pt | 600 | 1.4 | 0 | `color-text-primary` | 角色名"小屿"（估算值） |
| `text-body-lg` | 16 pt | 400 | 1.6 | 0 | `color-text-primary` | Bubble 正文（估算值） |
| `text-body-md` | 15 pt | 400 | 1.6 | 0 | `color-text-placeholder` | Composer Placeholder（估算值） |
| `text-caption` | 13 pt | 400 | 1.4 | 0 | `color-text-secondary` | 在线状态、时长"0:18"（估算值） |
| `text-overline` | 12 pt | 400 | 1.4 | 0.5 | `color-text-caption` | "AI朗读 · 可点击播放"、日期分隔符（估算值） |

---

## Spacing Scale

| Token Name | 值 | 用途 |
|------------|---|------|
| `spacing-1` | 4 pt | 极小间距（在线点与文字之间） |
| `spacing-2` | 8 pt | 小间距（Bubble 内元素间距、Typing 圆点间距） |
| `spacing-3` | 12 pt | 中小间距（Bubble 相邻 Gap、Composer 底部间距） |
| `spacing-4` | 16 pt | 基础间距（页面水平 Padding、Bubble 内 Padding 水平） |
| `spacing-5` | 20 pt | 中间距（Header 水平 Padding） |
| `spacing-6` | 24 pt | 中大间距（段落之间） |
| `spacing-8` | 32 pt | 大间距（区块之间） |
| `spacing-10` | 40 pt | 超大间距（备用） |
| `spacing-12` | 48 pt | 极大间距（备用） |
| `spacing-16` | 64 pt | Header+Status Bar 合计高度参考（估算值） |

---

## Motion

| Token Name | 值 | 用途 |
|------------|---|------|
| `duration-instant` | 100 ms | 按压反馈（Pressed state） |
| `duration-fast` | 200 ms | 按钮 scale/opacity 过渡 |
| `duration-normal` | 300 ms | Bubble 出现动画、页面滑入 |
| `duration-slow` | 500 ms | 背景渐变过渡、大面积动画 |
| `delay-stagger` | 50 ms | Typing 圆点错开动画延迟（每个点 +50ms） |
| `easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | 标准 Material-style easing |
| `easing-decelerate` | `cubic-bezier(0, 0, 0.2, 1)` | 元素进场（减速） |
| `easing-accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | 元素退场（加速） |
| `spring-bubble` | `stiffness: 300, damping: 20` | Bubble 弹入动画弹簧参数（推荐值） |
| `spring-typing-dot` | `stiffness: 400, damping: 15` | Typing 圆点呼吸弹簧参数（推荐值） |
