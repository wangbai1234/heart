# 08 Tailwind Mapping — 首页 Home

> 本文件为 Design Token → Tailwind v4 `@theme` 映射规则说明。
> 不包含任何可执行代码，仅建立命名映射关系供工程师参考。

---

## Colors（颜色映射）

### 基础调色板映射
| Design Token | Hex / RGBA | Tailwind @theme 变量名 | Tailwind 工具类 |
|-------------|-----------|----------------------|---------------|
| `color-primary` | `#FFB7C5` | `--color-primary` | `bg-primary` / `text-primary` / `border-primary` |
| `color-secondary` | `#A7C7E7` | `--color-secondary` | `bg-secondary` / `text-secondary` |
| `color-accent` | `#C8B6FF` | `--color-accent` | `bg-accent` / `text-accent` |
| `color-background` | `#FFF0F3` | `--color-background` | `bg-background` |
| `color-surface` | `#FFF8F3` | `--color-surface` | `bg-surface` |
| `color-glass` | `rgba(255,255,255,0.55)` | `--color-glass` | `bg-glass` |
| `color-border` | `rgba(255,183,197,0.25)` | `--color-border` | `border-border` |
| `color-divider` | `rgba(58,58,74,0.08)` | `--color-divider` | `divide-divider` |
| `color-text-primary` | `#3A3A4A` | `--color-text-primary` | `text-text-primary` |
| `color-text-secondary` | `#8E8E9A` | `--color-text-secondary` | `text-text-secondary` |
| `color-text-placeholder` | `#BDBDC8` | `--color-text-placeholder` | `text-text-placeholder` / `placeholder-text-placeholder` |
| `color-overlay` | `rgba(0,0,0,0.20)` | `--color-overlay` | `bg-overlay` |
| `color-tab-inactive` | `#ADADB8` | `--color-tab-inactive` | `text-tab-inactive` |
| `color-tab-active` | `#FFB7C5` | `--color-tab-active` | `text-tab-active` |
| `color-unread-badge` | `#FFB7C5` | `--color-unread-badge` | `bg-unread-badge` |
| `color-cta-text` | `#FF7A9A` | `--color-cta-text` | `text-cta-text` |
| `color-surface-card` | `rgba(255,255,255,0.60)` | `--color-surface-card` | `bg-surface-card` |

### 渐变映射（Gradient）
| Design Token | 映射说明 | Tailwind 变量名 |
|-------------|---------|---------------|
| `gradient-hero-sky` | bg-gradient-to-t from-[#F5D89C] to-[#D0A8D8] | `--gradient-hero-sky` |
| `gradient-orb-body` | bg-gradient-to-br from-[#FFB7C5] to-[#A89FD8] | `--gradient-orb-body` |
| `gradient-orb-shine` | 白色→透明，45° | `--gradient-orb-shine` |
| `gradient-tab-bar-blur` | from-[rgba(255,248,243,0.90)] to-[rgba(255,248,243,1.0)] | `--gradient-tab-bar` |

---

## Spacing（间距映射）

| Design Token | 值 | Tailwind 变量名 | 工具类示例 |
|-------------|---|---------------|----------|
| `space-1` | 4 pt | `--spacing-1` (=`spacing.1`) | `p-1` `m-1` `gap-1` |
| `space-2` | 8 pt | `--spacing-2` | `p-2` `m-2` `gap-2` |
| `space-3` | 12 pt | `--spacing-3` | `p-3` `gap-3` |
| `space-4` | 16 pt | `--spacing-4` | `px-4` `mx-4` |
| `space-5` | 20 pt | `--spacing-5` | `px-5` `mx-5` |
| `space-6` | 24 pt | `--spacing-6` | `p-6` `rounded-2xl`（如圆角=spacing） |
| `space-8` | 32 pt | `--spacing-8` | `p-8` |
| `space-10` | 40 pt | `--spacing-10` | `pt-10` |
| `space-12` | 48 pt | `--spacing-12` | `pb-12` |
| `space-16` | 64 pt | `--spacing-16` | `mb-16` |

> Tailwind v4 的 spacing 默认单位为 rem（1rem = 16px），需要在 `@theme` 中将 1pt ≈ 1px 对应调整，或直接使用 px 值覆写。

---

## Radius（圆角映射）

| Design Token | 值 | Tailwind 变量名 | 工具类 |
|-------------|---|---------------|-------|
| `radius-xs` | 4 pt | `--radius-xs` | `rounded-xs` → `rounded-sm`（标准 Tailwind 4px） |
| `radius-sm` | 8 pt | `--radius-sm` | `rounded-sm` → 需自定义 |
| `radius-md` | 12 pt | `--radius-md` | `rounded-md` → 需自定义 |
| `radius-lg` | 16 pt | `--radius-lg` | `rounded-lg` → 需自定义 (Tailwind 默认 8px，需覆盖) |
| `radius-xl` | 20 pt | `--radius-xl` | `rounded-xl` → 需自定义 |
| `radius-2xl` | 24 pt | `--radius-2xl` | `rounded-2xl` → 需自定义 |
| `radius-full` | 9999 pt | `--radius-full` | `rounded-full` (Tailwind 标准，无需自定义) |

> 建议在 `@theme` 中将 `--radius-*` 系列全部覆写为实际 px 值，避免与 Tailwind 默认值冲突。

---

## Blur（模糊映射）

| Design Token | 值 | Tailwind 变量名 | 工具类 |
|-------------|---|---------------|-------|
| `blur-glass-card` | 16 pt | `--blur-glass-card` | `backdrop-blur-glass-card` |
| `blur-glass-tile` | 8 pt | `--blur-glass-tile` | `backdrop-blur-glass-tile` |
| `blur-tab-bar` | 20 pt | `--blur-tab-bar` | `backdrop-blur-tab-bar` |
| `blur-orb-glow` | 40 pt | `--blur-orb-glow` | `blur-orb-glow`（用于 glow 滤镜） |

> Tailwind v4 `backdrop-blur` 默认 `blur-sm`=4px, `blur-md`=12px, `blur-lg`=16px。建议自定义 `@theme` 中对应值。

---

## Shadow（阴影映射）

| Design Token | 值 | Tailwind 变量名 | 工具类 |
|-------------|---|---------------|-------|
| `shadow-card` | 粉色 15%，blur 20pt，y+4pt | `--shadow-card` | `shadow-card` |
| `shadow-tile` | 深炭 6%，blur 8pt，y+2pt | `--shadow-tile` | `shadow-tile` |
| `shadow-orb-glow` | 紫色 50%，blur 40pt | `--shadow-orb-glow` | `shadow-orb-glow` |
| `shadow-avatar` | 深炭 10%，blur 6pt，y+2pt | `--shadow-avatar` | `shadow-avatar` |
| `shadow-tab-bar` | 深炭 8%，blur 12pt，y-2pt | `--shadow-tab-bar` | `shadow-tab-bar` |

> Tailwind v4 shadow 使用 CSS `box-shadow`，需在 `@theme` 中覆写完整 shadow 字符串。

---

## Font（字体映射）

### 字体族
| Design Token | 字体栈 | Tailwind 变量名 | 工具类 |
|-------------|-------|---------------|-------|
| `font-family-chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` | `--font-family-chinese` | `font-chinese` |
| `font-family-latin` | `SF Pro Rounded, -apple-system, sans-serif` | `--font-family-latin` | `font-latin` |

### 字号
| Design Token | 值 | Tailwind 变量名 | 工具类 |
|-------------|---|---------------|-------|
| `type-app-name` | 26 pt | `--text-app-name` | `text-app-name` |
| `type-title-lg` | 22 pt | `--text-title-lg` | `text-title-lg` |
| `type-headline` | 16 pt | `--text-headline` | `text-headline` (Tailwind默认`text-base`=16px 可复用) |
| `type-section-label` | 16 pt | `--text-section-label` | `text-section-label` |
| `type-body` | 14 pt | `--text-body` | `text-body` (Tailwind默认`text-sm`=14px 可复用) |
| `type-caption` | 13 pt | `--text-caption` | `text-caption` |
| `type-tab-label` | 10 pt | `--text-tab-label` | `text-tab-label` |
| `type-cta` | 15 pt | `--text-cta` | `text-cta` |

### 字重
| 字重值 | Tailwind 工具类 |
|--------|---------------|
| Regular (400) | `font-normal` |
| Medium (500) | `font-medium` |
| SemiBold (600) | `font-semibold` |
| Bold (700) | `font-bold` |

---

## Animation（动画映射）

| Design Token | 值 | Tailwind 变量名 | 工具类 |
|-------------|---|---------------|-------|
| `duration-fast` | 150 ms | `--duration-fast` | `duration-fast` |
| `duration-normal` | 250 ms | `--duration-normal` | `duration-normal` |
| `duration-slow` | 400 ms | `--duration-slow` | `duration-slow` |
| `duration-orb-pulse` | 2000 ms | `--duration-orb-pulse` | `duration-orb-pulse` |
| `easing-standard` | `cubic-bezier(0.4,0,0.2,1)` | `--ease-standard` | `ease-standard` |
| `easing-decelerate` | `cubic-bezier(0,0,0.2,1)` | `--ease-decelerate` | `ease-decelerate` |
| `easing-accelerate` | `cubic-bezier(0.4,0,1,1)` | `--ease-accelerate` | `ease-accelerate` |

> Tailwind v4 的 `transition-*` 和 `animation-*` 工具类需在 `@theme` 中自定义对应 `--transition-*` / `--animation-*` 变量。

---

## 如何用这套映射建立 Design System

### 步骤一：建立 @theme 变量层
在项目的全局 CSS 入口（如 `globals.css`）中，使用 Tailwind v4 的 `@theme` 指令声明所有上述变量：
- 将每个 Design Token 映射为对应的 CSS 自定义属性（`--color-primary: #FFB7C5;` 等）
- 覆盖 Tailwind 默认值，确保项目 Token 优先

### 步骤二：建立语义化工具类层
通过 Tailwind v4 的 `@utility` 或直接引用 `@theme` 变量，将语义化工具类（如 `bg-primary`, `text-text-secondary`）与 Token 变量绑定

### 步骤三：建立组件类层（可选）
如使用 CSS Modules 或 `@apply`，可将常见组件样式组合（如 `glass-card`, `action-tile`）封装为复合工具类，引用上述 Token 变量

### 步骤四：建立 Storybook / Component Preview
每个 Token 对应一个预览块，确保视觉与设计稿 Token 一致性可被 QA 验证

### 步骤五：Token 同步机制
当设计师更新 Figma 变量时，通过 Figma Tokens Plugin 或手动对比更新此映射文件和 `@theme` 声明，保持 Single Source of Truth

### 命名约定
| 层级 | 格式 | 示例 |
|------|------|------|
| 原始 Token（CSS 变量） | `--color-{name}` | `--color-primary` |
| Tailwind 工具类 | `{property}-{name}` | `bg-primary`, `text-text-secondary` |
| 复合组件类 | `{component}-{variant}` | `card-glass`, `tile-action` |
