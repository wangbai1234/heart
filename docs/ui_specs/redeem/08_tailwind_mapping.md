# 08 Tailwind v4 Mapping — Redeem 兑换页

> 本文件仅建立 Design Token → Tailwind v4 `@theme` 工具类的映射规则。
> 不生成任何组件代码，仅提供命名约定与映射关系，供工程师在实现时参照。

---

## Colors

### @theme 颜色变量映射

| Design Token | @theme 变量名 | 工具类示例 | 色值 |
|---|---|---|---|
| `color.primary` | `--color-primary` | `bg-primary` / `text-primary` / `border-primary` | `#FFB7C5` |
| `color.primary.light` | `--color-primary-light` | `bg-primary-light` | `#FFC8D4` |
| `color.primary.soft` | `--color-primary-soft` | `bg-primary-soft` | `rgba(255,183,197,0.20)` |
| `color.secondary` | `--color-secondary` | `bg-secondary` / `text-secondary-brand` | `#A7C7E7` |
| `color.accent` | `--color-accent` | `bg-accent` / `text-accent` | `#C8B6FF` |
| `color.surface` | `--color-surface` | `bg-surface` | `#FFF8F3` |
| `color.surface.card` | `--color-surface-card` | `bg-surface-card` | `rgba(255,248,243,0.92)` |
| `color.glass` | `--color-glass` | `bg-glass` | `rgba(255,255,255,0.55)` |
| `color.glass.light` | `--color-glass-light` | `bg-glass-light` | `rgba(255,255,255,0.88)` |
| `color.text.primary` | `--color-ink` | `text-ink` | `#3A3A4A` |
| `color.text.secondary` | `--color-ink-secondary` | `text-ink-secondary` | `#6B6B7A` |
| `color.text.placeholder` | `--color-ink-placeholder` | `text-ink-placeholder` | `rgba(58,58,74,0.35)` |
| `color.text.brand` | `--color-brand-link` | `text-brand-link` | `#FF8FAB` |
| `color.text.disclaimer` | `--color-ink-disclaimer` | `text-ink-disclaimer` | `rgba(58,58,74,0.50)` |
| `color.border` | `--color-border` | `border-border` | `rgba(255,183,197,0.35)` |
| `color.border.focused` | `--color-border-focused` | `border-border-focused` | `#FFB7C5` |
| `color.border.error` | `--color-border-error` | `border-border-error` | `#FF6B6B` |
| `color.success` | `--color-success` | `bg-success` / `text-success` | `#6BCB77` |
| `color.danger` | `--color-danger` | `bg-danger` / `text-danger` | `#FF6B6B` |
| `color.step.badge` | `--color-badge-bg` | `bg-badge` | `rgba(255,183,197,0.30)` |
| `color.step.badge.text` | `--color-badge-text` | `text-badge` | `#FF8FAB` |
| `color.background.top` | `--color-bg-top` | — | `#E8C8F0` |
| `color.background.mid` | `--color-bg-mid` | — | `#F0B8D0` |
| `color.background.bottom` | `--color-bg-bottom` | — | `#FFD8E0` |

---

## Gradient

| Design Token | @theme 变量名 | 说明 |
|---|---|---|
| `gradient.background` | `--gradient-bg` | `background: linear-gradient(180deg, #E8C8F0, #F0B8D0, #FFD8E0)` |
| `gradient.button.primary` | `--gradient-btn-primary` | `background: linear-gradient(90deg, #FFB7C5, #FF9EAF)` |
| `gradient.card` | `--gradient-card` | `background: linear-gradient(180deg, rgba(255,248,243,0.95), rgba(255,245,240,0.90))` |

Tailwind v4 中渐变使用方式（@theme 扩展，非代码，仅映射规则）：
- `bg-gradient-to-b from-bg-top via-bg-mid to-bg-bottom` → 全屏背景
- `bg-gradient-to-r from-primary to-primary-light` → 主按钮背景

---

## Spacing

| Design Token | @theme 变量名 | 工具类示例 | 值（逻辑pt） |
|---|---|---|---|
| `spacing.1` | `--spacing-1` | `p-1` / `m-1` / `gap-1` | 3pt |
| `spacing.2` | `--spacing-2` | `p-2` / `gap-2` | 6pt |
| `spacing.3` | `--spacing-3` | `p-3` / `gap-3` | 9pt |
| `spacing.4` | `--spacing-4` | `p-4` / `gap-4` | 12pt |
| `spacing.5` | `--spacing-5` | `p-5` / `gap-5` | 15pt |
| `spacing.6` | `--spacing-6` | `p-6` / `gap-6` | 18pt |
| `spacing.8` | `--spacing-8` | `p-8` / `gap-8` | 24pt |
| `spacing.10` | `--spacing-10` | `p-10` / `gap-10` | 30pt |
| `spacing.12` | `--spacing-12` | `p-12` | 36pt |

> Tailwind v4 默认 spacing 单位为 `rem`（1rem = 16px），本项目以 `pt` 为逻辑单位，建议在 `@theme` 中用 `px` 值覆盖默认 scale，或使用 `--spacing-*: <value>px`。

---

## Radius

| Design Token | @theme 变量名 | 工具类示例 | 值 |
|---|---|---|---|
| `radius.xs` | `--radius-xs` | `rounded-xs` | 3pt |
| `radius.sm` | `--radius-sm` | `rounded-sm` | 6pt |
| `radius.md` | `--radius-md` | `rounded-md` | 9pt |
| `radius.lg` | `--radius-lg` | `rounded-lg` | 12pt |
| `radius.xl` | `--radius-xl` | `rounded-xl` | 15pt |
| `radius.pill` | `--radius-pill` | `rounded-full` | 9999pt |
| `radius.badge` | — | `rounded-full` | 9999pt（使用内置） |

---

## Blur

| Design Token | @theme 变量名 | 工具类示例 | 值 |
|---|---|---|---|
| `blur.glass.sm` | `--blur-glass-sm` | `backdrop-blur-glass-sm` | 8px |
| `blur.glass.md` | `--blur-glass-md` | `backdrop-blur-glass-md` | 16px |
| `blur.glass.lg` | `--blur-glass-lg` | `backdrop-blur-glass-lg` | 24px |

---

## Shadow

| Design Token | @theme 变量名 | 工具类示例 | 值 |
|---|---|---|---|
| `shadow.card` | `--shadow-card` | `shadow-card` | `0 8px 40px rgba(255,183,197,0.15)` |
| `shadow.button.primary` | `--shadow-btn-primary` | `shadow-btn-primary` | `0 8px 24px rgba(255,143,171,0.40)` |
| `shadow.faq.card` | `--shadow-faq` | `shadow-faq` | `0 4px 16px rgba(0,0,0,0.06)` |
| `shadow.paste.button` | `--shadow-paste` | `shadow-paste` | `0 4px 12px rgba(255,183,197,0.20)` |

---

## Font

### 字体族

| Design Token | @theme 变量名 | 工具类示例 |
|---|---|---|
| PingFang SC / HarmonyOS Sans SC | `--font-sans-cn` | `font-sans-cn` |
| SF Pro Rounded | `--font-rounded` | `font-rounded` |

### 字号

| Design Token | @theme 变量名 | 工具类示例 | 值（逻辑pt） |
|---|---|---|---|
| `type.disclaimer` | `--text-xs` | `text-xs` | 11pt |
| `type.step.badge` | — | `text-xs` | 11pt |
| `type.card.subtitle` / `type.paste.button` | `--text-sm` | `text-sm` | 12~13pt |
| `type.faq.step` / `type.link.brand` | `--text-base` | `text-base` | 14pt |
| `type.faq.header` / `type.input.char` / `type.button.primary` / `type.navigation.title` | `--text-lg` | `text-lg` | 15~17pt |
| `type.card.title` | `--text-xl` | `text-xl` | 20pt |

### 字重

| 值 | 工具类 |
|---|---|
| Regular (400) | `font-normal` |
| Medium (500) | `font-medium` |
| SemiBold (600) | `font-semibold` |
| Bold (700) | `font-bold` |

---

## Animation

| Design Token | @theme 变量名 | 工具类示例 | 值 |
|---|---|---|---|
| `motion.duration.fast` | `--duration-fast` | `duration-fast` | 150ms |
| `motion.duration.normal` | `--duration-normal` | `duration-normal` | 250ms |
| `motion.duration.slow` | `--duration-slow` | `duration-slow` | 400ms |
| `motion.duration.spring` | `--duration-spring` | `duration-spring` | 500ms |
| `motion.easing.ease-out` | `--ease-out-custom` | `ease-out-custom` | `cubic-bezier(0, 0, 0.2, 1)` |
| `motion.easing.ease-in-out` | `--ease-in-out-custom` | `ease-in-out-custom` | `cubic-bezier(0.4, 0, 0.2, 1)` |
| `motion.easing.spring` | `--ease-spring` | `ease-spring` | `cubic-bezier(0.175, 0.885, 0.32, 1.275)` |

---

## 如何用这套映射建立 Design System

### 原则
1. **单一数据源**：所有 Design Token 在 `@theme` 中声明一次，组件层不允许使用魔法值（hardcoded hex/px）
2. **语义化命名**：工具类名称反映用途（`bg-surface-card`）而非色值（`bg-white/92`），方便主题切换
3. **分层映射**：
   - 第 1 层：原始值（`#FFB7C5`）→ `@theme` 全局变量（`--color-primary`）
   - 第 2 层：语义变量（`--color-btn-bg`）→ 引用第 1 层变量
   - 第 3 层：组件工具类（`btn-primary`）→ 组合第 2 层变量
4. **暗色模式准备**：在 `@theme` 中使用 CSS 变量引用而非硬编码，未来只需覆盖第 1 层变量即可切换主题

### 建立步骤（规则描述，非代码）
1. 在项目 `tailwind.config` 或 `@theme` 入口文件中，按上表注册所有颜色、间距、圆角、阴影、字体变量
2. 建立组件级 token（如 `--color-btn-primary-bg`）引用基础 token（`--color-primary`），隔离组件与全局 token 的耦合
3. 所有 Spacing 统一使用 `spacing.*` token，禁止在组件中使用任意 `px` 值
4. 渐变背景和阴影通过 `@theme` 注册为命名值，在组件中使用 `bg-gradient-btn-primary` 等语义工具类
5. 动效 token 注册到 `transitionDuration` / `transitionTimingFunction`，在组件中统一引用（如 `transition-all duration-normal ease-out-custom`）
6. 字体族通过 `fontFamily` 注册，在 body 或根组件设置 `font-sans-cn` 为全局默认，`font-rounded` 用于数字/英文场景
