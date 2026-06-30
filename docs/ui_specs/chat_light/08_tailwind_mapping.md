# 08 Tailwind Mapping — 聊天页 Chat（浅色模式）

> 本文件建立 Design Token → Tailwind v4 @theme 映射规则。
> 不生成实现代码，只定义命名规范和映射关系。

---

## Colors（颜色映射）

### @theme 自定义颜色工具类映射

| Design Token | Hex / RGBA | Tailwind @theme 变量名 | 工具类用法示例 |
|-------------|-----------|----------------------|--------------|
| `color-primary` | `#FFB7C5` | `--color-primary` | `bg-primary`，`text-primary`，`border-primary` |
| `color-secondary` | `#A7C7E7` | `--color-secondary` | `bg-secondary`，`text-secondary` |
| `color-accent` | `#C8B6FF` | `--color-accent` | `bg-accent`，`text-accent` |
| `color-surface` | `#FFF8F3` | `--color-surface` | `bg-surface` |
| `color-glass` | `rgba(255,255,255,0.55)` | `--color-glass` | `bg-glass`（需配合 backdrop-blur） |
| `color-glass-light` | `rgba(255,255,255,0.75)` | `--color-glass-light` | `bg-glass-light` |
| `color-glass-composer` | `rgba(255,255,255,0.65)` | `--color-glass-composer` | `bg-glass-composer` |
| `color-bg-top` | `#FFF0EC` | `--color-bg-top` | `from-bg-top`（用于 gradient） |
| `color-bg-bottom` | `#E8D5F5` | `--color-bg-bottom` | `to-bg-bottom` |
| `color-text-primary` | `#3A3A4A` | `--color-ink` | `text-ink` |
| `color-text-secondary` | `#888888` | `--color-ink-muted` | `text-ink-muted` |
| `color-text-caption` | `#AAAAAA` | `--color-ink-faint` | `text-ink-faint` |
| `color-text-placeholder` | `#BBBBBB` | `--color-ink-placeholder` | `text-ink-placeholder`，`placeholder:text-ink-placeholder` |
| `color-text-date` | `#999999` | `--color-ink-date` | `text-ink-date` |
| `color-text-on-primary` | `#FFFFFF` | `--color-white` | `text-white` |
| `color-online` | `#5FC8E8` | `--color-online` | `bg-online` |
| `color-border` | `rgba(255,255,255,0.60)` | `--color-border-glass` | `border-border-glass` |
| `color-success` | `#6DD5A0` | `--color-success` | `text-success`，`bg-success` |
| `color-warning` | `#FFD580` | `--color-warning` | `text-warning`，`bg-warning` |
| `color-danger` | `#FF6B6B` | `--color-danger` | `text-danger`，`bg-danger` |
| `color-overlay` | `rgba(0,0,0,0.40)` | `--color-overlay` | `bg-overlay` |

---

## Spacing（间距映射）

Tailwind v4 默认使用 0.25rem 为基础单位（1 = 4px = 4pt on screen）。

| Design Token | 值 | Tailwind 工具类（默认 scale） | 说明 |
|-------------|---|-----------------------------|------|
| `spacing-1` | 4 pt | `p-1`，`m-1`，`gap-1` | 1 × 4pt |
| `spacing-2` | 8 pt | `p-2`，`m-2`，`gap-2` | 2 × 4pt |
| `spacing-3` | 12 pt | `p-3`，`m-3`，`gap-3` | 3 × 4pt |
| `spacing-4` | 16 pt | `p-4`，`m-4`，`gap-4` | 4 × 4pt（基础间距） |
| `spacing-5` | 20 pt | `p-5`，`m-5`，`gap-5` | 5 × 4pt |
| `spacing-6` | 24 pt | `p-6`，`m-6`，`gap-6` | 6 × 4pt |
| `spacing-8` | 32 pt | `p-8`，`m-8`，`gap-8` | 8 × 4pt |
| `spacing-10` | 40 pt | `p-10`，`m-10`，`gap-10` | 10 × 4pt |
| `spacing-12` | 48 pt | `p-12`，`m-12`，`gap-12` | 12 × 4pt |
| `spacing-16` | 64 pt | `p-16`，`m-16`，`gap-16` | 16 × 4pt |

---

## Radius（圆角映射）

| Design Token | 值 | Tailwind @theme 变量名 | 工具类用法 |
|-------------|---|-----------------------|----------|
| `radius-xs` | 4 pt | `--radius-xs` | `rounded-xs` |
| `radius-sm` | 6 pt | `--radius-sm` | `rounded-sm` |
| `radius-md` | 12 pt | `--radius-md` | `rounded-md` |
| `radius-lg` | 20 pt | `--radius-lg` | `rounded-lg`（AI/User Bubble 主圆角） |
| `radius-xl` | 24 pt | `--radius-xl` | `rounded-xl`（Header 底圆角） |
| `radius-2xl` | 32 pt | `--radius-2xl` | `rounded-2xl`（Composer 胶囊形） |
| `radius-full` | 9999 pt | `--radius-full` | `rounded-full`（圆形按钮/头像/圆点） |

### Bubble 非对称圆角说明

Tailwind 默认工具类提供四角统一圆角。Bubble 的非对称圆角需自定义：
- AI Bubble 尾部：`rounded-bl-sm`（左下角小圆角 6pt）+ `rounded-t-lg rounded-br-lg`
- User Bubble 尾部：`rounded-tr-sm`（右上角小圆角 6pt）+ `rounded-b-lg rounded-tl-lg`
- 对应 @theme 变量：`--radius-bubble-tail: 6pt`

---

## Blur（模糊映射）

| Design Token | 值 | Tailwind @theme 变量名 | 工具类用法 |
|-------------|---|-----------------------|----------|
| `blur-glass-sm` | 10 pt | `--blur-glass-sm` | `backdrop-blur-glass-sm` |
| `blur-glass-md` | 20 pt | `--blur-glass-md` | `backdrop-blur-glass-md`（Header） |
| `blur-glass-lg` | 24 pt | `--blur-glass-lg` | `backdrop-blur-glass-lg`（Composer） |
| `blur-bg-glow` | 40 pt | `--blur-bg-glow` | `blur-bg-glow`（背景光晕） |

---

## Shadow（阴影映射）

| Design Token | 规格 | Tailwind @theme 变量名 | 工具类用法 |
|-------------|-----|-----------------------|----------|
| `shadow-header` | rgba(0,0,0,0.06) blur 12pt offset-y 2pt | `--shadow-header` | `shadow-header` |
| `shadow-composer` | rgba(0,0,0,0.08) blur 16pt offset-y -4pt | `--shadow-composer` | `shadow-composer` |
| `shadow-bubble` | rgba(255,183,197,0.1) blur 8pt offset-y 2pt | `--shadow-bubble` | `shadow-bubble` |
| `shadow-send-btn` | rgba(255,183,197,0.3) blur 12pt offset-y 4pt | `--shadow-send-btn` | `shadow-send-btn` |

---

## Font（字体映射）

### Font Family

| Design Token | 字体族 | Tailwind @theme 变量名 | 工具类用法 |
|-------------|-------|----------------------|----------|
| 中文主字体 | PingFang SC, HarmonyOS Sans SC, Noto Sans SC, system-ui | `--font-sans-cn` | `font-sans-cn` |
| 拉丁/数字字体 | SF Pro Rounded, -apple-system, BlinkMacSystemFont | `--font-sans-en` | `font-sans-en` |

### Font Size

| Design Token | 字号 | Tailwind @theme 变量名 | 工具类用法 |
|-------------|-----|----------------------|----------|
| `text-headline` | 17 pt | `--text-headline` | `text-headline` |
| `text-body-lg` | 16 pt | `--text-body-lg` | `text-body-lg`（Bubble 正文） |
| `text-body-md` | 15 pt | `--text-body-md` | `text-body-md`（Composer） |
| `text-caption` | 13 pt | `--text-caption` | `text-caption` |
| `text-overline` | 12 pt | `--text-overline` | `text-overline` |

### Font Weight

| 值 | Tailwind 工具类 |
|---|----------------|
| 400（Regular） | `font-normal` |
| 600（SemiBold） | `font-semibold` |
| 700（Bold） | `font-bold` |

### Line Height

| 值 | Tailwind 工具类 |
|----|----------------|
| 1.4 | `leading-snug` |
| 1.6 | `leading-relaxed` |

---

## Animation（动画映射）

| Design Token | 值 | Tailwind @theme 变量名 | 工具类用法 |
|-------------|---|----------------------|----------|
| `duration-instant` | 100 ms | `--duration-instant` | `duration-instant` |
| `duration-fast` | 200 ms | `--duration-fast` | `duration-fast` |
| `duration-normal` | 300 ms | `--duration-normal` | `duration-normal` |
| `duration-slow` | 500 ms | `--duration-slow` | `duration-slow` |
| `easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | `--ease-standard` | `ease-standard` |
| `easing-decelerate` | `cubic-bezier(0, 0, 0.2, 1)` | `--ease-decelerate` | `ease-decelerate` |
| `easing-accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | `--ease-accelerate` | `ease-accelerate` |

### 自定义动画工具类

| 用途 | @theme 变量名 | 工具类 |
|------|-------------|--------|
| Typing 圆点呼吸 | `--animate-typing-dot` | `animate-typing-dot` |
| Bubble 弹入 | `--animate-bubble-in` | `animate-bubble-in` |
| 发送按钮按压 | `--animate-press` | `animate-press` |

---

## 如何用此映射建立 Design System

### 建立步骤说明（无代码，仅规则）

**Step 1：定义 @theme 变量层**
在项目的全局 CSS 文件中，使用 Tailwind v4 的 `@theme` 指令块，将所有上述 Design Token 注册为 CSS 自定义属性（Custom Properties）。变量命名遵循本文件中的 `--变量名` 规范。

**Step 2：映射颜色系统**
颜色分为三层：
- 品牌层（Primary/Secondary/Accent）— 对应 yuoyuo 视觉标识
- 语义层（success/warning/danger/online）— 对应功能状态
- 中性层（ink/ink-muted/ink-faint/placeholder）— 对应文字层级

**Step 3：建立组件变体**
利用 Tailwind 的 `@layer components`（v4 中为 plugin/variant 方式）定义常用组件的组合工具类：
- `.bubble-ai`：AI Bubble 的所有 token 组合
- `.bubble-user`：User Bubble 的所有 token 组合
- `.composer`：Composer 的所有 token 组合
- `.glass-card`：通用毛玻璃卡片组合

**Step 4：建立响应式 Safe Area 映射**
将 iOS Safe Area（`env(safe-area-inset-top/bottom)`）映射为 Tailwind spacing token，确保 Header 和 Composer 的定位正确适配不同 iPhone 机型。

**Step 5：验证颜色对比度**
使用 WCAG AA 标准检查所有 text + background 颜色组合，确保对比度 ≥ 4.5:1（正文）、≥ 3:1（大字体/UI 组件）。详见 09_accessibility.md。

**Step 6：建立 Dark Mode 变体（当前规范范围外）**
使用 `@media (prefers-color-scheme: dark)` 或 `.dark` class，为每个颜色 token 定义深色模式对应值。
