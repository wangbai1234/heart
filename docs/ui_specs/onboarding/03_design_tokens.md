# 03 Design Tokens — 首次引导 FirstVisitGuide

## Color

### Brand Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-primary` | `#FFB7C5` | 主品牌色：樱花粉，分页激活点、描边、次按钮文字、主按钮渐变起点 |
| `color-primary-deep` | `#FF9EB5` | 深粉，主按钮渐变终点 |
| `color-secondary` | `#A7C7E7` | 天蓝色（本屏未直接使用，保留品牌token） |
| `color-accent` | `#C8B6FF` | 薰衣草紫，水晶心紫色调、背景渐变色之一 |

### Background Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-bg-canvas` | `#FEF0F0` | 拼版画布底色（奶油粉） |
| `color-bg-page` | `#FDE8D8`（渐变中心，估算值） | 单屏页面背景基底色 |
| `color-bg-gradient-top` | `#E8D8F5` | 背景渐变顶部：薰衣草紫 |
| `color-bg-gradient-center` | `#F9D0E0` | 背景渐变中心：玫瑰粉 |
| `color-bg-gradient-bottom` | `#FDE8C8` | 背景渐变底部：暖奶油黄 |

### Surface Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-surface` | `#FFF8F3` | 内容区域表面色（奶油白） |
| `color-surface-glass` | `rgba(255, 255, 255, 0.55)` | 毛玻璃面板表面色 |
| `color-surface-button-ghost` | `rgba(255, 255, 255, 0.70)` | Ghost按钮背景 |

### Glass Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-glass-fill` | `rgba(255, 255, 255, 0.55)` | 玻璃态填充色 |
| `color-glass-border` | `rgba(255, 183, 197, 0.40)` | 玻璃态边框色（粉色半透明） |
| `color-glass-shadow` | `rgba(255, 183, 197, 0.20)` | 玻璃态阴影色 |

### Border / Divider

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-border-default` | `#FFB7C5` | Ghost按钮描边颜色（粉色实色） |
| `color-border-light` | `rgba(255, 183, 197, 0.40)` | 轻量边框（卡片边缘） |
| `color-divider` | `rgba(255, 183, 197, 0.20)` | 分隔线（本屏未使用，保留token） |

### Text Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-text-primary` | `#3A3A4A` | 主文字色：标题、正文深色文字 |
| `color-text-secondary` | `#7A7A8A` | 次文字色：副标题、说明文字（估算值） |
| `color-text-brand` | `#FFB7C5` | 品牌色文字：按钮文字、链接文字 |
| `color-text-on-primary` | `#FFFFFF` | 主CTA按钮上的白色文字 |
| `color-text-placeholder` | `rgba(58, 58, 74, 0.35)` | 占位文字（本屏未使用） |
| `color-text-label` | `#8A8A9A` | 拼版底部标签文字色（估算值） |

### State Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-overlay` | `rgba(0, 0, 0, 0.30)` | 遮罩层（本屏未使用，保留） |
| `color-success` | `#A8D8B0` | 成功态（本屏未使用） |
| `color-warning` | `#FFD6A0` | 警告态（本屏未使用） |
| `color-danger` | `#FF8FAB` | 危险/错误态（本屏未使用） |
| `color-info` | `#A7C7E7` | 信息态（本屏未使用） |

### Pagination Dot Colors

| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `color-dot-active` | `#FFB7C5` | 当前页分页点（实心粉色） |
| `color-dot-inactive` | `rgba(255, 183, 197, 0.30)` | 非当前页分页点（低透明粉） |

---

## Gradient

| Token | 起点颜色 | 终点颜色 | 方向 | 透明度 | 用途 |
|-------|---------|---------|------|--------|------|
| `gradient-bg-page` | `#E8D8F5`（顶部） | `#FDE8C8`（底部），经由 `#F9D0E0`（中部） | 上→下（180°） | 100% | 每屏页面背景渐变 |
| `gradient-bg-radial` | `#F9D0E0`（中心） | `#FDE8D0`（边缘） | 径向，从中心向外 | 100% | 插画区光晕背景叠加 |
| `gradient-btn-primary` | `#FFB7C5` | `#FF9EB5` | 左→右（90°） | 100% | Step3主CTA按钮背景 |
| `gradient-illustration-fade` | 插画底部颜色 | 透明 `rgba(255,232,220,0)` | 上→下（180°） | 100%→0% | 插画底部羽化淡出到内容区 |
| `gradient-glow-soft` | `rgba(255,183,197,0.40)` | `rgba(255,183,197,0.00)` | 径向，从光源中心 | 40%→0% | 插画背景散射光效（bokeh光斑） |

---

## Radius

| Token | 值 | 使用场景 |
|-------|----|---------|
| `radius-xs` | 4 px | 极小元素（本屏未使用） |
| `radius-sm` | 8 px | 小型组件（本屏未直接使用） |
| `radius-md` | 12 px | 中型卡片内圆角 |
| `radius-lg` | 16 px | 内容卡片区域（本屏未使用独立卡片） |
| `radius-xl` | 20 px | 中等圆角容器 |
| `radius-2xl` | 24 px | 大型容器 |
| `radius-pill` | 9999 px（50%） | 按钮：Ghost"下一步"、实心"开始体验"（全圆角胶囊型） |
| `radius-phone-frame` | ~40 px（估算值） | 手机帧外框圆角 |
| `radius-dot-active` | 4 px（估算值） | 激活分页点（较大实心圆） |
| `radius-dot-inactive` | 3 px（估算值） | 非激活分页点（较小实心圆） |

---

## Shadow

| Token | 颜色 | 透明度 | Blur | Offset X | Offset Y | Spread | 使用场景 |
|-------|------|--------|------|----------|----------|--------|---------|
| `shadow-illustration` | `#FFB7C5` | 25% | 40 px | 0 | 8 px | 0 | 插画主体投影（粉色软阴影） |
| `shadow-btn-ghost` | `#FFB7C5` | 15% | 12 px | 0 | 4 px | 0 | Ghost按钮轻微阴影（估算值） |
| `shadow-btn-primary` | `#FF9EB5` | 30% | 20 px | 0 | 8 px | 0 | 主CTA按钮发光阴影 |
| `shadow-phone-frame` | `rgba(0,0,0,0.12)` | 12% | 24 px | 0 | 8 px | 0 | 手机帧投影（拼版用） |

---

## Blur

| Token | 值 | 使用场景 |
|-------|----|---------|
| `blur-glass-light` | 8 px | 轻度毛玻璃（Ghost按钮背景，估算值） |
| `blur-glass-medium` | 16 px | 中度毛玻璃（内容区背景，估算值） |
| `blur-glass-heavy` | 24 px | 重度毛玻璃（玻璃罩插画内部模糊效果） |
| `blur-bg-bokeh` | 40 px | 背景 bokeh 光斑模糊（插画区环境光） |

---

## Opacity

| Token | 值 | 使用场景 |
|-------|----|---------|
| `opacity-glass-fill` | 55% | 玻璃态填充层 |
| `opacity-glass-border` | 40% | 玻璃态边框 |
| `opacity-btn-ghost-bg` | 70% | Ghost按钮背景透明度 |
| `opacity-dot-inactive` | 30% | 非激活分页点 |
| `opacity-shadow-soft` | 15–25% | 软阴影通用范围 |
| `opacity-text-secondary` | 60% | 次级文字相对主文字的视觉权重（估算值） |
| `opacity-illustration-fade` | 0%（底部） | 插画底部渐变淡出终值 |

---

## Typography

### 字体族

| Token | 字体 | 语言 |
|-------|------|------|
| `font-family-chinese` | PingFang SC / HarmonyOS Sans SC | 中文主字体 |
| `font-family-latin` | SF Pro Rounded | 英文/数字辅助字体 |
| `font-family-fallback` | system-ui, sans-serif | 降级字体 |

### 文字层级（Text Scale）

| 层级 | Token | 字号 | 字重 | 行高 | 字间距 | 颜色 | 使用场景 |
|------|-------|------|------|------|--------|------|---------|
| Title | `text-title` | 22–24 px | Bold (700) | 1.35 | -0.3 px | `#3A3A4A` | 每屏主标题（估算值） |
| Headline | `text-headline` | 18 px | SemiBold (600) | 1.4 | 0 | `#3A3A4A` | 单行标题变体 |
| Body | `text-body` | 14 px | Regular (400) | 1.6 | 0.1 px | `#7A7A8A` | 副标题/说明文字 |
| Button | `text-button` | 16 px | Medium (500) | 1.0 | 0.3 px | 见各按钮颜色 | 按钮文字 |
| Caption | `text-caption` | 12–13 px | Regular (400) | 1.5 | 0 | `#8A8A9A` | 小字说明、拼版标签 |
| Link | `text-link` | 14 px | Regular (400) | 1.5 | 0 | `#FFB7C5` | "我有兑换码 →"文字链接 |
| Status | `text-status` | 15 px（估算值） | Medium (500) | 1.0 | 0 | `#3A3A4A` | 状态栏时间 |

---

## Spacing Scale

统一 4px 基准网格体系：

| Token | 值 | 使用场景 |
|-------|----|---------|
| `spacing-1` | 4 px | 极小间距（点间距） |
| `spacing-2` | 8 px | 小间距 |
| `spacing-3` | 12 px | 标题与副文本间距，主次按钮间距 |
| `spacing-4` | 16 px | 常规间距 |
| `spacing-5` | 20 px | 副文本与分页点间距，分页点与按钮间距 |
| `spacing-6` | 24 px | 页面左右内边距，内容顶部内边距 |
| `spacing-8` | 32 px | 大间距 |
| `spacing-10` | 40 px | 特大间距 |
| `spacing-12` | 48 px | 状态栏高度参考 |
| `spacing-16` | 64 px | 超大间距 |
| `spacing-safe-bottom` | 34 px | iOS Safe Area Bottom |
| `spacing-safe-top` | 47 px | iOS Safe Area Top |

---

## Motion

### 推荐动效参数

| Token | 值 | 用途 |
|-------|----|------|
| `motion-duration-fast` | 150 ms | 按钮按压反馈 |
| `motion-duration-normal` | 300 ms | 屏幕切换过渡 |
| `motion-duration-slow` | 500 ms | 插画进场动画 |
| `motion-duration-enter` | 400 ms | 屏幕进入动画 |
| `motion-delay-stagger` | 80 ms | 元素错落进场间隔 |
| `motion-easing-standard` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | 通用缓动 |
| `motion-easing-decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 元素进场（减速进入） |
| `motion-easing-accelerate` | `cubic-bezier(0.4, 0.0, 1.0, 1)` | 元素退场（加速离开） |
| `motion-easing-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1.0)` | 插画弹入，分页点切换弹跳 |
| `motion-spring-damping` | 0.8 | Spring弹性阻尼（估算值） |
| `motion-spring-stiffness` | 200 | Spring弹性刚度（估算值） |
