# 08 Tailwind v4 映射规则（Tailwind Mapping）

## 说明

本文件建立 yuoyuo Motion Storyboard 中所有 Design Token 到 Tailwind CSS v4 的映射规则。
**仅定义映射关系，不生成任何组件代码。**

---

## Tailwind v4 配置方式说明

Tailwind v4 使用 `@theme` CSS 层（CSS-first 配置）替代 `tailwind.config.js`。在 `app.css` 或 `globals.css` 中通过 CSS 变量定义 Design System。

---

## 颜色（Colors）映射

### 品牌主色

| Design Token | CSS 变量 | Tailwind 类名 | 色值 |
|-------------|---------|---------------|------|
| `color.primary` | `--color-primary` | `bg-primary` / `text-primary` | `#FFB7C5` |
| `color.secondary` | `--color-secondary` | `bg-secondary` / `text-secondary` | `#A7C7E7` |
| `color.accent` | `--color-accent` | `bg-accent` / `text-accent` | `#C8B6FF` |

### 背景 / 表面

| Design Token | CSS 变量 | Tailwind 类名 | 色值 |
|-------------|---------|---------------|------|
| `color.surface` | `--color-surface` | `bg-surface` | `#FFF8F3` |
| `color.glass` | `--color-glass` | `bg-glass` | `rgba(255,255,255,0.55)` |
| `color.bubble.ai.bg` | `--color-bubble-ai` | `bg-bubble-ai` | `rgba(255,255,255,0.90)` |
| `color.bubble.user.bg` | `--color-bubble-user` | `bg-bubble-user` | `#FFD6DF` |

### 文字颜色

| Design Token | CSS 变量 | Tailwind 类名 | 色值 |
|-------------|---------|---------------|------|
| `color.text.primary` | `--color-ink` | `text-ink` | `#3A3A4A` |
| `color.text.secondary` | `--color-ink-secondary` | `text-ink-secondary` | `#6B6B7A` |
| `color.text.timestamp` | `--color-timestamp` | `text-timestamp` | `#AAAAAA` |
| `color.text.placeholder` | `--color-placeholder` | `text-placeholder` / `placeholder-placeholder` | `#BBBBCC` |
| `color.text.online` | `--color-online` | `text-online` | `#7DCE7D` |

### 新增语义色（Tailwind 扩展）

| Design Token | CSS 变量 | Tailwind 类名 | 色值 |
|-------------|---------|---------------|------|
| `color.bubble.new.glow` | `--color-bubble-glow` | `bg-bubble-glow` | `rgba(255,183,197,0.35)` |
| `color.divider` | `--color-divider` | `border-divider` / `divide-divider` | `rgba(0,0,0,0.06)` |

---

## 间距（Spacing）映射

Tailwind v4 默认间距刻度已满足大部分需求，以下为扩展项：

| Design Token | CSS 变量 | Tailwind 类名 | 值 |
|-------------|---------|---------------|----|
| `spacing.1` | `--spacing-1` | `p-1` / `m-1` / `gap-1` | `4px` |
| `spacing.2` | `--spacing-2` | `p-2` / `m-2` / `gap-2` | `8px` |
| `spacing.3` | `--spacing-3` | `p-3` / `m-3` | `12px` |
| `spacing.4` | `--spacing-4` | `p-4` / `m-4` | `16px` |
| `spacing.5` | `--spacing-5` | `p-5` / `m-5` | `20px` |
| `spacing.6` | `--spacing-6` | `p-6` / `m-6` | `24px` |
| `spacing.8` | `--spacing-8` | `p-8` / `m-8` | `32px` |
| `spacing.10` | `--spacing-10` | `p-10` / `m-10` | `40px` |

> Tailwind v4 默认 1 unit = 4px，标准刻度与 Design Token 完全对齐，无需自定义。

---

## 圆角（Border Radius）映射

| Design Token | CSS 变量 | Tailwind 类名 | 值 |
|-------------|---------|---------------|----|
| `radius.xs` | `--radius-xs` | `rounded-xs` | `8px` |
| `radius.sm` | `--radius-sm` | `rounded-sm` | `12px` |
| `radius.md` | `--radius-md` | `rounded-md` | `16px`（估算值） |
| `radius.lg` | `--radius-lg` | `rounded-lg` | `20px`（估算值） |
| `radius.xl` | `--radius-xl` | `rounded-xl` | `24px`（估算值） |
| `radius.full` | — | `rounded-full` | `9999px`（Tailwind 原生） |

> Tailwind v4 中通过 `@theme` 覆盖 `--radius-*` 变量以重映射圆角刻度。

---

## 毛玻璃 / 模糊（Blur）映射

| Design Token | CSS 变量 | Tailwind 类名 | 值 |
|-------------|---------|---------------|----|
| `blur.glass.sm` | `--blur-glass-sm` | `backdrop-blur-glass-sm` | `8px` |
| `blur.glass.md` | `--blur-glass-md` | `backdrop-blur-glass-md` | `16px`（估算值） |
| `blur.glass.lg` | `--blur-glass-lg` | `backdrop-blur-glass-lg` | `24px`（估算值） |

> Tailwind v4 通过 `backdrop-blur-*` 工具类实现毛玻璃效果，需搭配 `bg-glass`（半透明背景）使用。

---

## 阴影（Shadow）映射

| Design Token | CSS 变量 | Tailwind 类名 | 值 |
|-------------|---------|---------------|----|
| `shadow.bubble.ai` | `--shadow-bubble-ai` | `shadow-bubble-ai` | `0 2px 8px rgba(0,0,0,0.05)` |
| `shadow.bubble.user` | `--shadow-bubble-user` | `shadow-bubble-user` | `0 2px 12px rgba(255,183,197,0.20)` |
| `shadow.orb` | `--shadow-orb` | `shadow-orb` | `0 0 20px rgba(200,182,255,0.35)` |
| `shadow.button.plus` | `--shadow-btn-plus` | `shadow-btn-plus` | `0 2px 8px rgba(255,183,197,0.40)` |

> 在 `@theme` 中扩展 `--shadow-*` 变量，Tailwind v4 的 `shadow-{name}` 工具类可直接引用。

---

## 字体（Font）映射

### 字体家族

| Design Token | CSS 变量 | Tailwind 类名 |
|-------------|---------|---------------|
| PingFang SC / HarmonyOS Sans SC | `--font-sans` | `font-sans` |
| SF Pro Rounded（拉丁/数字） | `--font-rounded` | `font-rounded` |

```css
/* @theme 配置示例（规则，非代码） */
--font-sans: "PingFang SC", "HarmonyOS Sans SC", -apple-system, sans-serif;
--font-rounded: "SF Pro Rounded", -apple-system, sans-serif;
```

### 字号

| Design Token | Tailwind 类名 | 值 |
|-------------|---------------|----|
| `type.display` | `text-3xl`（约 28px） | 28px |
| `type.section.title` | `text-base`（16px） | 16px |
| `type.body` | `text-sm`（14px） | 14px |
| `type.body.sm` | `text-[13px]` | 13px（自定义） |
| `type.caption` | `text-xs`（11px→12px，closest） | 11px |

### 字重

| 字重 | Tailwind 类名 |
|------|---------------|
| Regular (400) | `font-normal` |
| Medium (500) | `font-medium` |
| Semibold (600) | `font-semibold` |

---

## 动效 / 动画（Animation）映射

Tailwind v4 支持在 `@theme` 中定义自定义关键帧和动画：

### 持续时间

| Design Token | CSS 变量 | Tailwind 类名 |
|-------------|---------|---------------|
| `motion.duration.bubble.bloom` | `--duration-bubble-bloom` | `duration-[300ms]` |
| `motion.duration.orb.pulse` | `--duration-orb-pulse` | `duration-[1200ms]` |
| `motion.duration.page.transition` | `--duration-page-transition` | `duration-[400ms]` |

### 缓动曲线

| Design Token | CSS 变量 | Tailwind 类名 |
|-------------|---------|---------------|
| ease-out（气泡绽放） | `--ease-bubble` | `ease-out` |
| ease-in-out（情绪球） | `--ease-orb` | `ease-in-out` |

### 自定义动画关键帧（映射规则）

| 动画名 | CSS 关键帧名 | Tailwind animate 类名 |
|--------|-------------|----------------------|
| 气泡绽放 | `@keyframes bubbleBloom` | `animate-bubble-bloom` |
| 情绪球脉冲 | `@keyframes orbPulse` | `animate-orb-pulse` |
| 语音波跳动 | `@keyframes voiceWave` | `animate-voice-wave` |
| 页面过渡入 | `@keyframes sheetSlideIn` | `animate-sheet-slide-in` |

> 在 `@theme` 中通过 `--animate-*` 变量注册，然后以 `animate-{name}` 类名调用。

---

## 透明度（Opacity）映射

| Design Token | Tailwind 类名 |
|-------------|---------------|
| `opacity.page.behind` (0.92) | `opacity-[0.92]` 或自定义 `opacity-behind` |
| `opacity.glass.surface` (0.55) | `opacity-[0.55]` |

---

## Design System 建立流程

1. **单一来源**：所有 Token 定义在 `src/styles/tokens.css` 的 `@theme` 块中
2. **CSS 变量优先**：每个 Token 先定义为 CSS 变量（`--color-primary: #FFB7C5`），Tailwind 自动生成对应工具类
3. **语义命名**：类名使用语义名（`bg-primary`）而非具体色值（`bg-[#FFB7C5]`），便于主题切换
4. **动效单独文件**：将 `@keyframes` 定义在 `src/styles/animations.css`，在 `@theme` 中引用
5. **组件级覆盖**：通过 CSS 变量允许组件内部局部覆盖 Token，而不污染全局
