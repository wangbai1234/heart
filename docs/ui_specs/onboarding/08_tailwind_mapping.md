# 08 Tailwind Mapping — 首次引导 FirstVisitGuide

## 说明

本文档建立 Design Token（来自 `03_design_tokens.md`）与 Tailwind CSS v4 `@theme` 自定义工具类的映射规则。

**本文档仅建立映射规则，不生成任何实现代码。**

---

## Colors（颜色映射）

### Brand 品牌色

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-primary` | `bg-primary` / `text-primary` / `border-primary` | `#FFB7C5` |
| `color-primary-deep` | `bg-primary-deep` / `text-primary-deep` | `#FF9EB5` |
| `color-secondary` | `bg-secondary` / `text-secondary-brand` | `#A7C7E7` |
| `color-accent` | `bg-accent` / `text-accent` | `#C8B6FF` |

### Background 背景色

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-bg-canvas` | `bg-canvas` | `#FEF0F0` |
| `color-bg-page` | `bg-page` | `#FDE8D8` |
| `color-bg-gradient-top` | `from-bg-top` | `#E8D8F5` |
| `color-bg-gradient-center` | `via-bg-center` | `#F9D0E0` |
| `color-bg-gradient-bottom` | `to-bg-bottom` | `#FDE8C8` |

### Surface 表面色

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-surface` | `bg-surface` | `#FFF8F3` |
| `color-surface-glass` | `bg-glass` | `rgba(255,255,255,0.55)` |
| `color-surface-button-ghost` | `bg-ghost` | `rgba(255,255,255,0.70)` |

### Glass 玻璃态

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-glass-fill` | `bg-glass-fill` | `rgba(255,255,255,0.55)` |
| `color-glass-border` | `border-glass` | `rgba(255,183,197,0.40)` |
| `color-glass-shadow` | `shadow-glass` | `rgba(255,183,197,0.20)` |

### Border / Divider 边框

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-border-default` | `border-brand` | `#FFB7C5` |
| `color-border-light` | `border-light` | `rgba(255,183,197,0.40)` |
| `color-divider` | `divide-brand` | `rgba(255,183,197,0.20)` |

### Text 文字色

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-text-primary` | `text-ink` | `#3A3A4A` |
| `color-text-secondary` | `text-ink-secondary` | `#7A7A8A` |
| `color-text-brand` | `text-primary` | `#FFB7C5` |
| `color-text-on-primary` | `text-white` | `#FFFFFF` |
| `color-text-placeholder` | `text-placeholder` | `rgba(58,58,74,0.35)` |
| `color-text-label` | `text-label-muted` | `#8A8A9A` |

### State 状态色

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-overlay` | `bg-overlay` | `rgba(0,0,0,0.30)` |
| `color-success` | `bg-success` / `text-success` | `#A8D8B0` |
| `color-warning` | `bg-warning` / `text-warning` | `#FFD6A0` |
| `color-danger` | `bg-danger` / `text-danger` | `#FF8FAB` |
| `color-info` | `bg-info` / `text-info` | `#A7C7E7` |

### Pagination Dot 分页点

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `color-dot-active` | `bg-dot-active` | `#FFB7C5` |
| `color-dot-inactive` | `bg-dot-inactive` | `rgba(255,183,197,0.30)` |

---

## Spacing（间距映射）

Tailwind v4 使用 `--spacing-*` 自定义变量，以 4px 为基准：

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `spacing-1` | `p-1` / `m-1` / `gap-1` | 4 px |
| `spacing-2` | `p-2` / `m-2` / `gap-2` | 8 px |
| `spacing-3` | `p-3` / `m-3` / `gap-3` | 12 px |
| `spacing-4` | `p-4` / `m-4` / `gap-4` | 16 px |
| `spacing-5` | `p-5` / `m-5` / `gap-5` | 20 px |
| `spacing-6` | `p-6` / `m-6` / `gap-6` | 24 px |
| `spacing-8` | `p-8` / `m-8` / `gap-8` | 32 px |
| `spacing-10` | `p-10` / `m-10` / `gap-10` | 40 px |
| `spacing-12` | `p-12` / `m-12` | 48 px |
| `spacing-16` | `p-16` / `m-16` | 64 px |
| `spacing-safe-bottom` | `pb-safe` | 34 px（自定义） |
| `spacing-safe-top` | `pt-safe` | 47 px（自定义） |

---

## Radius（圆角映射）

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `radius-xs` | `rounded-xs` | 4 px |
| `radius-sm` | `rounded-sm` | 8 px |
| `radius-md` | `rounded-md` | 12 px |
| `radius-lg` | `rounded-lg` | 16 px |
| `radius-xl` | `rounded-xl` | 20 px |
| `radius-2xl` | `rounded-2xl` | 24 px |
| `radius-pill` | `rounded-full` | 9999 px（Tailwind 内置） |
| `radius-phone-frame` | `rounded-phone` | 40 px（自定义） |

---

## Blur（模糊映射）

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `blur-glass-light` | `backdrop-blur-light` | `blur(8px)` |
| `blur-glass-medium` | `backdrop-blur-md` | `blur(16px)` |
| `blur-glass-heavy` | `backdrop-blur-lg` | `blur(24px)` |
| `blur-bg-bokeh` | `blur-bokeh` | `blur(40px)`（自定义） |

---

## Shadow（阴影映射）

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `shadow-illustration` | `shadow-illust` | `0 8px 40px rgba(255,183,197,0.25)` |
| `shadow-btn-ghost` | `shadow-ghost` | `0 4px 12px rgba(255,183,197,0.15)` |
| `shadow-btn-primary` | `shadow-cta` | `0 8px 20px rgba(255,158,181,0.30)` |
| `shadow-phone-frame` | `shadow-phone` | `0 8px 24px rgba(0,0,0,0.12)` |

---

## Font（字体映射）

### Font Family

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `font-family-chinese` | `font-chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` |
| `font-family-latin` | `font-rounded` | `SF Pro Rounded, system-ui, sans-serif` |
| `font-family-fallback` | `font-sans` | `system-ui, sans-serif` |

### Font Size

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `text-title` | `text-2xl` / `text-title` | 22–24 px（自定义22px） |
| `text-headline` | `text-lg` / `text-headline` | 18 px |
| `text-body` | `text-sm` / `text-body` | 14 px |
| `text-button` | `text-base` | 16 px |
| `text-caption` | `text-xs` / `text-caption` | 12–13 px |
| `text-link` | `text-sm` | 14 px |
| `text-status` | `text-status` | 15 px（自定义） |

### Font Weight

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| Regular (400) | `font-normal` | 400 |
| Medium (500) | `font-medium` | 500 |
| SemiBold (600) | `font-semibold` | 600 |
| Bold (700) | `font-bold` | 700 |

### Line Height

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| 1.35 | `leading-tight` / `leading-[1.35]` | 1.35 |
| 1.4 | `leading-snug` | 1.4 |
| 1.5 | `leading-normal` / `leading-[1.5]` | 1.5 |
| 1.6 | `leading-relaxed` | 1.6 |

---

## Animation（动效映射）

### Duration

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `motion-duration-fast` | `duration-150` | 150 ms |
| `motion-duration-normal` | `duration-300` | 300 ms |
| `motion-duration-slow` | `duration-500` | 500 ms |
| `motion-duration-enter` | `duration-400` / `duration-[400ms]` | 400 ms（自定义） |

### Easing

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `motion-easing-standard` | `ease-in-out` | `cubic-bezier(0.4,0.0,0.2,1)` |
| `motion-easing-decelerate` | `ease-out` | `cubic-bezier(0.0,0.0,0.2,1)` |
| `motion-easing-accelerate` | `ease-in` | `cubic-bezier(0.4,0.0,1.0,1)` |
| `motion-easing-spring` | `ease-spring` | `cubic-bezier(0.34,1.56,0.64,1.0)`（自定义） |

### Delay

| Design Token | Tailwind 工具类名 | 值 |
|--------------|------------------|----|
| `motion-delay-stagger` | `delay-[80ms]` | 80 ms（自定义） |

---

## 如何用这套映射建立 Design System

### 映射建立原则

1. **单一数据源**：所有 Token 值定义在 `03_design_tokens.md`，Tailwind `@theme` 仅引用，不重复定义值。

2. **层次化命名**：
   - 语义层（`text-primary`）→ 引用基础层（`#FFB7C5`）
   - 避免工具类直接使用裸值（如 `text-[#FFB7C5]`），只使用语义类名

3. **@theme 自定义规则**（规则，非代码）：
   - 在 Tailwind v4 配置的 `@theme` 块内，将所有自定义 Token 注册为 CSS 变量
   - 颜色、间距、圆角、模糊、阴影、字体、动效 全部在 `@theme` 内声明

4. **Token 分组**：
   - `--color-*`：颜色 token
   - `--radius-*`：圆角 token
   - `--shadow-*`：阴影 token
   - `--blur-*`：模糊 token
   - `--font-*`：字体 token
   - `--duration-*`：动效时长 token
   - `--ease-*`：缓动函数 token
   - `--spacing-*`：间距 token（若覆盖默认scale）

5. **工具类生成规则**：
   - 颜色类通过 `@theme colors` 自动生成 `bg-*`、`text-*`、`border-*`
   - 间距类通过 `@theme spacing` 自动生成 `p-*`、`m-*`、`gap-*`
   - 自定义类（如 `shadow-cta`、`blur-bokeh`、`rounded-phone`）通过 `@theme` 对应字典注册

6. **Dark Mode 预留**：
   - 所有颜色 token 预留 `dark:` 变体映射位置（本屏以浅色为主）
   - 深色模式下背景反转为深紫/深灰系，品牌粉色适当调整亮度

7. **组件级 token 应用优先级**：
   - `PrimaryButton` 优先使用：`bg-gradient-to-r from-primary to-primary-deep text-white rounded-full shadow-cta`
   - `GhostButton` 优先使用：`bg-ghost border border-brand text-primary rounded-full backdrop-blur-light shadow-ghost`
   - `TitleText` 优先使用：`text-title font-bold text-ink leading-tight`

8. **不允许的模式**：
   - 禁止内联 `style` 覆盖 token 颜色（除动态计算值外）
   - 禁止工具类中使用任意值 `[#FFB7C5]` 替代语义类 `text-primary`
   - 禁止在组件内重复声明与 token 等价的硬编码颜色
