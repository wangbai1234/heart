# 03 设计 Token — Splash Screen（启动屏）

> 所有颜色值通过目视采样 + 项目 Design DNA 规范（#FFB7C5 / #A7C7E7 / #C8B6FF 等）结合估算得出。精确值需通过 Figma 吸色工具验证。

---

## Color Tokens

### 主色板（Brand Palette）

| Token 名称 | 色值（HEX） | 色值（RGBA） | 用途说明 |
|------------|-------------|--------------|----------|
| `color.brand.cherry-pink` | `#FFB7C5` | `rgba(255, 183, 197, 1)` | 品牌主色，心形宝石左侧主色调 |
| `color.brand.sky-blue` | `#A7C7E7` | `rgba(167, 199, 231, 1)` | 品牌副色，心形宝石右下蓝色区域 |
| `color.brand.lavender` | `#C8B6FF` | `rgba(200, 182, 255, 1)` | 强调色，心形宝石右侧紫蓝渐变 |
| `color.brand.cream` | `#FFF8F3` | `rgba(255, 248, 243, 1)` | Surface 色，背景顶部奶油高光 |
| `color.brand.charcoal` | `#3A3A4A` | `rgba(58, 58, 74, 1)` | Ink，"yuoyuo" 字标主色 |

### 背景色（Background）

| Token 名称 | 色值（HEX / 估算） | 用途说明 |
|------------|-------------------|----------|
| `color.bg.sky-top` | `#FDE8D8`（估算值） | 背景渐变顶部：浅橘粉 |
| `color.bg.sky-mid` | `#F8C8D4`（估算值） | 背景渐变中段：粉红 |
| `color.bg.sky-bottom` | `#E8C0E8`（估算值） | 背景渐变底部：淡紫粉 |
| `color.bg.page` | `#F5D0E0`（估算值） | 整体背景基色（渐变中间值参考） |

### 文字色（Typography）

| Token 名称 | 色值 | 用途 |
|------------|------|------|
| `color.text.wordmark` | `#3A3A4A` | "yuoyuo" 字标 |
| `color.text.tagline` | `#5A5A6A`（估算值） | "陪你聊聊吧" tagline，比字标略浅 |
| `color.text.on-dark` | `#FFFFFF` | 深色背景上的文字（本屏暂未使用） |

### 指示器色（Indicator）

| Token 名称 | 色值 | 用途 |
|------------|------|------|
| `color.indicator.active` | `#E87A9A`（估算值） | 底部中间点（较大，较亮） |
| `color.indicator.inactive` | `#F0A0B8`（估算值） | 底部两侧点（较小，较暗） |

### 语义色（Semantic — 本屏 N/A）

| Token 名称 | 色值 | 状态 |
|------------|------|------|
| `color.semantic.success` | `#52C41A` | 本屏不使用 |
| `color.semantic.error` | `#FF4D4F` | 本屏不使用 |
| `color.semantic.warning` | `#FAAD14` | 本屏不使用 |

### 玻璃/叠加色（Glass & Overlay）

| Token 名称 | 色值 | 用途 |
|------------|------|------|
| `color.glass.surface` | `rgba(255,255,255,0.55)` | 玻璃质感表面（本屏心形宝石透明层） |
| `color.glass.border` | `rgba(255,255,255,0.35)` | 玻璃边框高光描边 |
| `color.overlay.dark` | `rgba(0,0,0,0.3)` | 通用遮罩（本屏不使用） |

---

## Gradient Tokens

### 背景天空渐变

| Token 名称 | 方向 | 起始色 | 结束色 | 用途 |
|------------|------|--------|--------|------|
| `gradient.bg.sky` | 180°（从上到下） | `#FCEACB`（奶油黄，估算值）| `#D9B8E8`（淡紫，估算值）| 全屏背景天空 |

更精确的多节点渐变（Gradient Stop）：

```
0%   → #FCEACB（奶油黄/暖白）
15%  → #F8D0C0（浅橘粉）
40%  → #F5C0CF（粉红）
70%  → #EDB8D8（玫粉）
100% → #D9B8E8（淡紫）
```

### 心形宝石渐变（从左上到右下）

| Token 名称 | 方向 | 起始色 | 结束色 | 用途 |
|------------|------|--------|--------|------|
| `gradient.gem.primary` | 135°（左上→右下） | `#FFB7C5`（樱花粉）| `#A7C7E7`（天蓝）| 宝石主体基色 |
| `gradient.gem.overlay` | 135° | `#C8B6FF`（薰衣草紫）| `#A7C7E7`（天蓝）| 宝石右侧渐变叠加层 |

### 宝石高光渐变

| Token 名称 | 方向 | 起始色 | 结束色 | 透明度 | 用途 |
|------------|------|--------|--------|--------|------|
| `gradient.gem.highlight` | 120°（左上→右下）| `rgba(255,255,255,0.9)` | `rgba(255,255,255,0)` | 变化 | 宝石左上角白色高光 |

### 背景右上角光晕

| Token 名称 | 类型 | 颜色 | 透明度 | 用途 |
|------------|------|------|--------|------|
| `gradient.glow.top-right` | Radial | `#FFFDE8`（暖白，估算值）| 0.8→0 | 右上角太阳光晕效果 |

---

## Radius Tokens

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `radius.gem` | 完全有机曲线（自然心形轮廓） | 心形宝石（非标准圆角） |
| `radius.dot.large` | 50%（圆形） | 底部中间指示点 |
| `radius.dot.small` | 50%（圆形） | 底部两侧指示点 |
| `radius.cloud` | 有机曲线（自然边缘） | 云朵装饰 |
| `radius.sm` | 4px | 通用小圆角 |
| `radius.md` | 8px | 通用中圆角 |
| `radius.lg` | 16px | 通用大圆角 |
| `radius.xl` | 24px | 通用超大圆角 |
| `radius.full` | 9999px | 完整圆形 |

---

## Shadow Tokens

### 宝石阴影

| Token 名称 | 颜色 | 透明度 | Blur | X Offset | Y Offset | Spread | 场景 |
|------------|------|--------|------|----------|----------|--------|------|
| `shadow.gem.drop` | `#C8A0D0`（紫粉，估算值）| 0.35 | 60px（估算值） | 0 | 20px（估算值） | 0 | 心形宝石外部投影 |
| `shadow.gem.inner` | `rgba(255,255,255,0.6)` | — | 30px（估算值） | 0 | 0 | 内凹 | 宝石内部高光光晕 |

### 文字阴影（本屏未明显使用）

| Token 名称 | 色值 | 透明度 | Blur | 场景 |
|------------|------|--------|------|------|
| `shadow.text.soft` | `rgba(0,0,0,0)` | 0 | — | 本屏文字无阴影，N/A |

---

## Blur Tokens（毛玻璃）

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `blur.cloud` | 8～16px（估算值） | 云朵边缘模糊，产生大气感 |
| `blur.glow` | 40～60px（估算值） | 顶部光晕散射效果 |
| `blur.gem.inner-glow` | 20px（估算值） | 宝石内部发光柔化 |
| `blur.backdrop.glass` | 12px | 通用玻璃模糊（本屏宝石质感参考） |

---

## Opacity Tokens

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `opacity.cloud.primary` | 0.7（估算值） | 主要云朵层透明度 |
| `opacity.cloud.secondary` | 0.4（估算值） | 次要/远景云朵透明度 |
| `opacity.glow.top` | 0.8（估算值） | 顶部光晕层 |
| `opacity.indicator.active` | 1.0 | 底部活跃圆点 |
| `opacity.indicator.inactive` | 0.6（估算值） | 底部非活跃圆点 |
| `opacity.gem.glass` | 0.55 | 玻璃表面层透明度 |
| `opacity.page.fade-in` | 0 → 1 | 进入动画起止透明度 |
| `opacity.page.fade-out` | 1 → 0 | 退出动画起止透明度 |

---

## Typography Tokens

### 字体栈（Font Stack）

| Token 名称 | 字体 | 权重 | 用途 |
|------------|------|------|------|
| `font.family.latin` | `'SF Pro Rounded', system-ui` | — | 拉丁字母（yuoyuo） |
| `font.family.chinese` | `'PingFang SC', 'HarmonyOS Sans SC', sans-serif` | — | 中文（陪你聊聊吧） |

### 文字规格

| Token 名称 | 字体 | 字号（画布px） | 字号（逻辑pt，估算） | 字重 | 行高 | 字距 | 颜色 |
|------------|------|----------------|----------------------|------|------|------|------|
| `type.wordmark` | SF Pro Rounded | ≈ 96px（估算值） | ≈ 37pt | Bold（700）| 1.0 | -0.02em（估算值）| `#3A3A4A` |
| `type.tagline` | PingFang SC | ≈ 48px（估算值） | ≈ 18pt | Regular（400）| 1.5 | 0.12em（宽松，估算值）| `#5A5A6A`（估算值）|

### 字体层级（Type Scale）

| 层级 | Token | 字号（逻辑pt） | 用途 |
|------|-------|----------------|------|
| Display | `type.scale.display` | 37pt（估算值）| App 名称字标 |
| Subtitle | `type.scale.subtitle` | 18pt（估算值）| Tagline / 副标题 |

---

## Spacing Scale（间距体系）

| Token 名称 | 值（逻辑pt） | 值（画布px，×2.625） |
|------------|--------------|----------------------|
| `spacing.xxs` | 4pt | 10px |
| `spacing.xs` | 8pt | 21px |
| `spacing.sm` | 12pt | 32px |
| `spacing.md` | 16pt | 42px |
| `spacing.lg` | 24pt | 63px |
| `spacing.xl` | 32pt | 84px |
| `spacing.xxl` | 48pt | 126px |
| `spacing.icon-to-wordmark` | 22pt（估算值）| 58px（估算值）|
| `spacing.wordmark-to-tagline` | 11pt（估算值）| 30px（估算值）|

---

## Motion Tokens（动画）

### 页面级动画

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `motion.splash.fade-in.duration` | 400ms | 启动屏淡入时长 |
| `motion.splash.fade-in.delay` | 0ms | 淡入延迟 |
| `motion.splash.fade-in.easing` | `ease-out` | 淡入缓动 |
| `motion.splash.fade-out.duration` | 300ms | 退出淡出时长 |
| `motion.splash.fade-out.easing` | `ease-in` | 淡出缓动 |
| `motion.splash.hold.duration` | 1000～2000ms | 应用初始化期间保持显示 |

### 宝石图标动画

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `motion.gem.scale-in.duration` | 600ms（推荐）| 宝石从小到大弹性出现 |
| `motion.gem.scale-in.easing` | `spring(1, 80, 10, 0)` | 弹性进入感 |
| `motion.gem.float.duration` | 3000ms（推荐）| 宝石悬浮呼吸动画周期 |
| `motion.gem.float.amplitude` | ±8px（推荐）| 上下浮动幅度 |
| `motion.gem.float.easing` | `ease-in-out` | 呼吸缓动 |

### 底部呼吸点动画

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `motion.dots.breathe.duration` | 1200ms | 单点一次呼吸周期 |
| `motion.dots.breathe.delay.left` | 0ms | 左侧点延迟 |
| `motion.dots.breathe.delay.center` | 200ms | 中间点延迟 |
| `motion.dots.breathe.delay.right` | 400ms | 右侧点延迟 |
| `motion.dots.breathe.easing` | `ease-in-out` | 呼吸缓动 |
| `motion.dots.scale.min` | 0.7 | 呼吸最小缩放 |
| `motion.dots.scale.max` | 1.2 | 呼吸最大缩放（中间点）|
| `motion.dots.opacity.min` | 0.5 | 呼吸最小透明度 |
| `motion.dots.opacity.max` | 1.0 | 呼吸最大透明度 |

### 字标动画

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `motion.wordmark.fade-in.duration` | 500ms（推荐）| 字标渐现 |
| `motion.wordmark.fade-in.delay` | 300ms（推荐）| 晚于宝石出现 |
| `motion.wordmark.slide-up.distance` | 16px（推荐）| 从下往上滑入距离 |

### 通用 Easing 函数

| Token 名称 | 值 | 用途 |
|------------|-----|------|
| `motion.easing.standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | 标准过渡 |
| `motion.easing.decelerate` | `cubic-bezier(0, 0, 0.2, 1)` | 元素进入 |
| `motion.easing.accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | 元素退出 |
| `motion.easing.spring` | `spring(1, 80, 10, 0)` | 弹性效果 |
