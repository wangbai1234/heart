# 08 Tailwind v4 映射规则 — Splash Screen（启动屏）

> 本文档仅建立 Design Token → Tailwind v4 映射规则，不生成任何业务代码。
> Tailwind v4 采用 CSS 变量 + `@theme` 指令定义自定义 token。

---

## Tailwind v4 Design System 架构说明

Tailwind v4 通过 CSS 文件中的 `@theme` 块定义设计 token，覆盖或扩展默认主题。所有自定义 token 均以 CSS 变量形式存在，类名自动从变量生成。

```
@theme {
  --color-*         → 颜色 token → bg-*, text-*, border-* 类名
  --spacing-*       → 间距 token → p-*, m-*, gap-* 类名（Tailwind v4 新机制）
  --radius-*        → 圆角 token → rounded-* 类名
  --blur-*          → 模糊 token → blur-* 类名
  --shadow-*        → 阴影 token → shadow-* 类名
  --font-*          → 字体 token → font-* 类名
  --animate-*       → 动画 token → animate-* 类名
  --transition-*    → 过渡 token
}
```

---

## 颜色映射（Color Tokens）

### 品牌主色

| Design Token | CSS 变量名 | Tailwind 类名前缀 | 值 |
|--------------|-----------|-------------------|----|
| `color.brand.cherry-pink` | `--color-brand-cherry-pink` | `bg-brand-cherry-pink` / `text-brand-cherry-pink` | `#FFB7C5` |
| `color.brand.sky-blue` | `--color-brand-sky-blue` | `bg-brand-sky-blue` | `#A7C7E7` |
| `color.brand.lavender` | `--color-brand-lavender` | `bg-brand-lavender` | `#C8B6FF` |
| `color.brand.cream` | `--color-brand-cream` | `bg-brand-cream` | `#FFF8F3` |
| `color.brand.charcoal` | `--color-brand-charcoal` | `text-brand-charcoal` | `#3A3A4A` |

### 文字色

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `color.text.wordmark` | `--color-text-wordmark` | `text-wordmark` | `#3A3A4A` |
| `color.text.tagline` | `--color-text-tagline` | `text-tagline` | `#5A5A6A`（估算值）|

### 背景渐变色

| Design Token | CSS 变量名 | 用途 |
|--------------|-----------|------|
| `color.bg.sky-top` | `--color-sky-top` | 渐变起点（`from-sky-top`）|
| `color.bg.sky-bottom` | `--color-sky-bottom` | 渐变终点（`to-sky-bottom`）|

### 指示器色

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `color.indicator.active` | `--color-indicator-active` | `bg-indicator-active` | `#E87A9A`（估算值）|
| `color.indicator.inactive` | `--color-indicator-inactive` | `bg-indicator-inactive` | `#F0A0B8`（估算值）|

### 玻璃色

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `color.glass.surface` | `--color-glass-surface` | `bg-glass-surface` | `rgba(255,255,255,0.55)` |
| `color.glass.border` | `--color-glass-border` | `border-glass` | `rgba(255,255,255,0.35)` |

---

## 间距映射（Spacing Tokens）

Tailwind v4 通过 `--spacing-*` 自定义间距（或沿用 Tailwind 默认 4px 倍数体系）。

| Design Token | CSS 变量名 | Tailwind 类名 | 逻辑 pt 值 | px 值 |
|--------------|-----------|---------------|-----------|-------|
| `spacing.xxs` | `--spacing-xxs` | `p-xxs`, `m-xxs`, `gap-xxs` | 4pt | 10px |
| `spacing.xs` | `--spacing-xs` | `p-xs` 等 | 8pt | 21px |
| `spacing.sm` | `--spacing-sm` | `p-sm` 等 | 12pt | 32px |
| `spacing.md` | `--spacing-md` | `p-md` 等 | 16pt | 42px |
| `spacing.lg` | `--spacing-lg` | `p-lg` 等 | 24pt | 63px |
| `spacing.xl` | `--spacing-xl` | `p-xl` 等 | 32pt | 84px |
| `spacing.xxl` | `--spacing-xxl` | `p-xxl` 等 | 48pt | 126px |
| `spacing.icon-to-wordmark` | `--spacing-icon-to-wordmark` | `mb-icon-to-wordmark` | 22pt（估算值）| 58px（估算值）|
| `spacing.wordmark-to-tagline` | `--spacing-wordmark-to-tagline` | `mb-wordmark-to-tagline` | 11pt（估算值）| 30px（估算值）|

> Tailwind v4 支持将所有 spacing token 统一在 `--spacing` 命名空间下，类名自动生成（如 `gap-[22pt]` 或自定义 `gap-icon-to-wordmark`）。

---

## 圆角映射（Radius Tokens）

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `radius.sm` | `--radius-sm` | `rounded-sm` | 4px |
| `radius.md` | `--radius-md` | `rounded-md` | 8px |
| `radius.lg` | `--radius-lg` | `rounded-lg` | 16px |
| `radius.xl` | `--radius-xl` | `rounded-xl` | 24px |
| `radius.full` | `--radius-full` | `rounded-full` | 9999px |
| `radius.gem` | `--radius-gem` | N/A（有机曲线，使用 clip-path）| 心形路径 |

---

## 模糊映射（Blur Tokens）

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `blur.cloud` | `--blur-cloud` | `blur-cloud` | 12px（估算值）|
| `blur.glow` | `--blur-glow` | `blur-glow` | 48px（估算值）|
| `blur.gem.inner` | `--blur-gem-inner` | `blur-gem-inner` | 20px（估算值）|
| `blur.backdrop.glass` | `--blur-backdrop-glass` | `backdrop-blur-glass` | 12px |

> Tailwind v4 中 `backdrop-blur-*` 和 `blur-*` 分别映射 CSS `backdrop-filter: blur()` 和 `filter: blur()`。

---

## 阴影映射（Shadow Tokens）

| Design Token | CSS 变量名 | Tailwind 类名 | CSS 值 |
|--------------|-----------|---------------|--------|
| `shadow.gem.drop` | `--shadow-gem-drop` | `shadow-gem` | `0 20px 60px rgba(200,160,210,0.35)`（估算值）|
| `shadow.soft` | `--shadow-soft` | `shadow-soft` | `0 4px 24px rgba(200,160,210,0.15)` |

---

## 字体映射（Font Tokens）

### 字体族

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `font.family.latin` | `--font-latin` | `font-latin` | `'SF Pro Rounded', 'Nunito', system-ui, sans-serif` |
| `font.family.chinese` | `--font-chinese` | `font-chinese` | `'PingFang SC', 'HarmonyOS Sans SC', sans-serif` |

### 字号（Type Scale）

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `type.scale.display` | `--text-display` | `text-display` | 37pt / `2.3125rem`（估算值）|
| `type.scale.subtitle` | `--text-subtitle` | `text-subtitle` | 18pt / `1.125rem`（估算值）|

### 字重

| 值 | Tailwind 类名 | 用途 |
|----|---------------|------|
| 700 | `font-bold` | yuoyuo 字标 |
| 400 | `font-normal` | tagline |

### 字距

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `tracking.wordmark` | `--tracking-wordmark` | `tracking-wordmark` | `-0.02em`（估算值）|
| `tracking.tagline` | `--tracking-tagline` | `tracking-tagline` | `0.12em`（估算值）|

---

## 动画映射（Animation Tokens）

### Keyframes 定义规则

| 动画名称 | CSS 变量/Keyframe | Tailwind 类名 | 描述 |
|----------|------------------|---------------|------|
| 宝石浮动 | `@keyframes gem-float` | `animate-gem-float` | Y轴±8px 呼吸浮动 |
| 点呼吸 | `@keyframes dot-breathe` | `animate-dot-breathe` | scale+opacity 循环 |
| 淡入 | `@keyframes fade-in` | `animate-fade-in` | opacity 0→1 |
| 淡出 | `@keyframes fade-out` | `animate-fade-out` | opacity 1→0 |
| 弹入 | `@keyframes scale-spring` | `animate-scale-spring` | scale 0.75→1 带弹性 |

### Duration 类名

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `motion.splash.fade-in.duration` | `--duration-splash-in` | `duration-splash-in` | 400ms |
| `motion.splash.fade-out.duration` | `--duration-splash-out` | `duration-splash-out` | 300ms |
| `motion.gem.scale-in.duration` | `--duration-gem-in` | `duration-gem-in` | 600ms |
| `motion.dots.breathe.duration` | `--duration-dot-breathe` | `duration-dot-breathe` | 1200ms |
| `motion.gem.float.duration` | `--duration-gem-float` | `duration-gem-float` | 3000ms |

### Delay 类名

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `motion.dots.breathe.delay.left` | `--delay-dot-left` | `delay-dot-left` | 0ms |
| `motion.dots.breathe.delay.center` | `--delay-dot-center` | `delay-dot-center` | 200ms |
| `motion.dots.breathe.delay.right` | `--delay-dot-right` | `delay-dot-right` | 400ms |

### Easing 类名

| Design Token | CSS 变量名 | Tailwind 类名 | 值 |
|--------------|-----------|---------------|----|
| `motion.easing.standard` | `--ease-standard` | `ease-standard` | `cubic-bezier(0.4,0,0.2,1)` |
| `motion.easing.decelerate` | `--ease-decelerate` | `ease-decelerate` | `cubic-bezier(0,0,0.2,1)` |
| `motion.easing.accelerate` | `--ease-accelerate` | `ease-accelerate` | `cubic-bezier(0.4,0,1,1)` |
| `motion.easing.spring` | `--ease-spring` | N/A（需 CSS linear() 或 JS）| 弹性效果 |

---

## 渐变工具类映射规则

Tailwind v4 支持通过 `bg-linear-*` 或任意值创建渐变，建议以下映射：

| 渐变名称 | Tailwind 构建方式 | 说明 |
|----------|-------------------|------|
| 天空背景渐变 | `bg-linear-to-b from-[#FCEACB] via-[#F5C0CF] to-[#D9B8E8]` | 三节点简化版 |
| 宝石主渐变 | 使用 `style` 属性或 `@layer` 内联 clip-path | 有机形状需 clip-path |

---

## `@theme` 配置块示例结构（仅结构，不含完整代码）

```
@theme {
  /* Colors */
  --color-brand-cherry-pink: #FFB7C5;
  --color-brand-sky-blue: #A7C7E7;
  --color-brand-lavender: #C8B6FF;
  --color-brand-charcoal: #3A3A4A;
  --color-text-tagline: #5A5A6A;
  --color-indicator-active: #E87A9A;
  --color-indicator-inactive: #F0A0B8;
  --color-glass-surface: rgba(255,255,255,0.55);

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* Blur */
  --blur-cloud: 12px;
  --blur-glow: 48px;
  --blur-backdrop-glass: 12px;

  /* Shadows */
  --shadow-gem: 0 20px 60px rgba(200,160,210,0.35);

  /* Fonts */
  --font-latin: 'SF Pro Rounded', 'Nunito', system-ui, sans-serif;
  --font-chinese: 'PingFang SC', 'HarmonyOS Sans SC', sans-serif;

  /* Type scale */
  --text-display: 2.3125rem;
  --text-subtitle: 1.125rem;

  /* Letter spacing */
  --tracking-wordmark: -0.02em;
  --tracking-tagline: 0.12em;

  /* Animation durations */
  --duration-splash-in: 400ms;
  --duration-splash-out: 300ms;
  --duration-gem-in: 600ms;
  --duration-gem-float: 3000ms;
  --duration-dot-breathe: 1200ms;
}
```

---

## 注意事项

1. **Tailwind v4 与 v3 差异**：v4 中 arbitrary values 写法变为 `[value]`，建议所有 splash 专用 token 均纳入 `@theme` 统一管理，避免散落的任意值。
2. **心形宝石**：复杂的有机曲线形状（heart shape + bubble tail）无法用 Tailwind 类名描述，需配合 `clip-path` CSS 属性或 SVG 图形，Tailwind 仅负责颜色/尺寸/阴影等可用类名的属性。
3. **动画 spring easing**：CSS 原生 `linear()` 函数（CSS Easing Level 2）可模拟 spring，但兼容性较新，建议用 Framer Motion 或 CSS `@keyframes` 结合 `cubic-bezier` 近似替代。
4. **字体加载**：SF Pro Rounded 仅在 Apple 平台可用，Web 端需自行托管或使用 Google Fonts（Nunito）作为备选，通过 `@font-face` 注册后映射到 `--font-latin`。
