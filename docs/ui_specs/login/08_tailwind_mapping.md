# 08 Tailwind Mapping — 登录页 Login

本文件建立登录页 Design Token 与 Tailwind v4 `@theme` 映射规则。
不生成组件代码，仅建立命名映射规则，供 Design System 实施参考。

---

## Colors

### Brand Colors
| Design Token | Hex / RGBA | Tailwind @theme 变量名 | 建议工具类名 |
|-------------|-----------|----------------------|------------|
| `color.brand.primary` | `#FFB7C5` | `--color-brand-primary` | `bg-brand-primary` / `text-brand-primary` |
| `color.brand.secondary` | `#A7C7E7` | `--color-brand-secondary` | `bg-brand-secondary` / `text-brand-secondary` |
| `color.brand.accent` | `#C8B6FF` | `--color-brand-accent` | `bg-brand-accent` / `text-brand-accent` |

### Background / Surface Colors
| Design Token | Hex / RGBA | Tailwind @theme 变量名 | 建议工具类名 |
|-------------|-----------|----------------------|------------|
| `color.bg.page` | `#FFF8F3` | `--color-bg-page` | `bg-bg-page` |
| `color.bg.surface` | `rgba(255,255,255,0.75)` | `--color-bg-surface` | `bg-bg-surface` |
| `color.bg.glass` | `rgba(255,255,255,0.55)` | `--color-bg-glass` | `bg-bg-glass` |
| `color.bg.overlay` | `rgba(255,240,245,0.60)` | `--color-bg-overlay` | `bg-bg-overlay` |

### Text Colors
| Design Token | Hex / RGBA | Tailwind @theme 变量名 | 建议工具类名 |
|-------------|-----------|----------------------|------------|
| `color.text.primary` | `#3A3A4A` | `--color-text-primary` | `text-text-primary` |
| `color.text.secondary` | `#8A8898` | `--color-text-secondary` | `text-text-secondary` |
| `color.text.placeholder` | `#B0A8B4` | `--color-text-placeholder` | `text-text-placeholder` |
| `color.text.link` | `#FFB7C5` | `--color-text-link` | `text-text-link` |
| `color.text.on-primary` | `#FFFFFF` | `--color-text-on-primary` | `text-text-on-primary` |

### Divider / Border Colors
| Design Token | Hex / RGBA | Tailwind @theme 变量名 | 建议工具类名 |
|-------------|-----------|----------------------|------------|
| `color.divider` | `rgba(0,0,0,0.06)` | `--color-divider` | `border-divider` / `divide-divider` |
| `color.border.card` | `rgba(255,255,255,0.60)` | `--color-border-card` | `border-border-card` |

### Semantic Colors
| Design Token | Hex | Tailwind @theme 变量名 | 建议工具类名 |
|-------------|-----|----------------------|------------|
| `color.semantic.success` | `#4CAF50` | `--color-semantic-success` | `text-semantic-success` |
| `color.semantic.danger` | `#FF5252` | `--color-semantic-danger` | `text-semantic-danger` / `border-semantic-danger` |
| `color.semantic.warning` | `#FFB74D` | `--color-semantic-warning` | `text-semantic-warning` |
| `color.semantic.info` | `#4FC3F7` | `--color-semantic-info` | `text-semantic-info` |

---

## Gradient

Tailwind v4 支持自定义渐变变量，以下为映射建议：

| 渐变名 | From | To | Tailwind @theme 变量名 |
|--------|------|----|----------------------|
| 页面下半背景渐变 | `#FFDDD8` | `#FFF8F3` | `--gradient-page-bg` |
| 主按钮渐变 | `#FFB7C5` | `#FF8FAB` | `--gradient-primary-btn` |
| 天空插画渐变 | `#9B8EC4` | `#FFDDC1` | `--gradient-sky`（参考值，实际由图片承载） |

工具类命名建议：
- `bg-gradient-page-bg`（从上至下线性渐变）
- `bg-gradient-primary-btn`（从左至右线性渐变）

---

## Spacing

| Design Token | Value | Tailwind @theme 变量名 | 等价 Tailwind 默认类 |
|-------------|-------|----------------------|-------------------|
| `space.1` | `4px` | `--spacing-1` | `p-1` / `m-1` |
| `space.2` | `8px` | `--spacing-2` | `p-2` / `m-2` |
| `space.3` | `12px` | `--spacing-3` | `p-3` / `m-3` |
| `space.4` | `16px` | `--spacing-4` | `p-4` / `m-4` |
| `space.5` | `20px` | `--spacing-5` | `p-5` / `m-5` |
| `space.6` | `24px` | `--spacing-6` | `p-6` / `m-6` |
| `space.8` | `32px` | `--spacing-8` | `p-8` / `m-8` |
| `space.10` | `40px` | `--spacing-10` | `p-10` / `m-10` |
| `space.12` | `48px` | `--spacing-12` | `p-12` / `m-12` |
| `space.16` | `64px` | `--spacing-16` | `p-16` / `m-16` |
| `space.20` | `80px` | `--spacing-20` | `p-20` / `m-20` |
| `space.24` | `96px` | `--spacing-24` | `p-24` / `m-24` |

---

## Radius

| Design Token | Value | Tailwind @theme 变量名 | 等价 Tailwind 工具类 |
|-------------|-------|----------------------|-------------------|
| `radius.xs` | `4px` | `--radius-xs` | `rounded-xs`（自定义）/ `rounded` |
| `radius.sm` | `8px` | `--radius-sm` | `rounded-sm` |
| `radius.md` | `16px` | `--radius-md` | `rounded-2xl`（≈16px） |
| `radius.lg` | `24px` | `--radius-lg` | `rounded-3xl`（≈24px） |
| `radius.xl` | `32px` | `--radius-xl` | `rounded-[32px]` |
| `radius.2xl` | `48px` | `--radius-2xl` | `rounded-[48px]`（FormCard） |
| `radius.pill` | `9999px` | `--radius-pill` | `rounded-full` |
| `radius.circle` | `50%` | `--radius-circle` | `rounded-full`（配合 aspect-square） |

---

## Blur

| Design Token | Value | Tailwind @theme 变量名 | 等价 Tailwind 工具类 |
|-------------|-------|----------------------|-------------------|
| `blur.glass-sm` | `12px` | `--blur-glass-sm` | `backdrop-blur-sm`（≈8px，接近） |
| `blur.glass-md` | `20px` | `--blur-glass-md` | `backdrop-blur-md`（≈12px）/ `backdrop-blur-[20px]` |
| `blur.glass-lg` | `40px` | `--blur-glass-lg` | `backdrop-blur-[40px]` |

说明：Tailwind v4 支持任意值语法，推荐直接使用 `backdrop-blur-[20px]` 精确控制毛玻璃效果。

---

## Shadow

| Design Token | 描述 | Tailwind @theme 变量名 | Tailwind 工具类 |
|-------------|------|----------------------|----------------|
| 表单卡阴影 | `rgba(255,183,197,0.15) 0 8px 40px` | `--shadow-card` | `shadow-card`（自定义） |
| 主按钮阴影 | `rgba(255,143,171,0.35) 0 8px 24px -4px` | `--shadow-btn-primary` | `shadow-btn-primary`（自定义） |
| 心形发光 | `rgba(255,255,255,0.80) 0 0 60px` | `--shadow-glow-white` | `shadow-glow-white`（自定义） |

Tailwind v4 `@theme` 自定义阴影示例：
```
--shadow-card: 0 8px 40px rgba(255,183,197,0.15);
--shadow-btn-primary: 0 8px 24px -4px rgba(255,143,171,0.35);
--shadow-glow-white: 0 0 60px rgba(255,255,255,0.80);
```

---

## Font

### Font Family
| Design Token | Value | Tailwind @theme 变量名 | 工具类 |
|-------------|-------|----------------------|--------|
| `font.family.chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` | `--font-family-chinese` | `font-chinese` |
| `font.family.brand` | `SF Pro Rounded, system-ui, sans-serif` | `--font-family-brand` | `font-brand` |
| `font.family.ui` | `PingFang SC, SF Pro Rounded, sans-serif` | `--font-family-ui` | `font-ui` |

### Font Size（以逻辑像素 390px 设备为基准，估算值）
| Design Token | 逻辑 Size | Tailwind @theme 变量名 | 工具类 |
|-------------|----------|----------------------|--------|
| `font.size.display` | `~36px` | `--font-size-display` | `text-display` |
| `font.size.title-lg` | `~14px` | `--font-size-title-lg` | `text-title-lg` |
| `font.size.body-lg` | `~15px` | `--font-size-body-lg` | `text-body-lg` |
| `font.size.body-md` | `~11px` | `--font-size-body-md` | `text-body-md` |
| `font.size.body-sm` | `~10px` | `--font-size-body-sm` | `text-body-sm` |
| `font.size.caption` | `~11px` | `--font-size-caption` | `text-caption` |

### Font Weight
| Design Token | Value | 工具类 |
|-------------|-------|--------|
| `font.weight.regular` | `400` | `font-normal` |
| `font.weight.medium` | `500` | `font-medium` |
| `font.weight.semibold` | `600` | `font-semibold` |
| `font.weight.bold` | `700` | `font-bold` |

### Line Height
| Design Token | Value | 工具类 |
|-------------|-------|--------|
| `line-height.tight` | `1.2` | `leading-tight`（≈1.25） |
| `line-height.normal` | `1.5` | `leading-normal`（=1.5） |
| `line-height.loose` | `1.6` | `leading-relaxed`（≈1.625） |

---

## Animation

| Design Token | Value | Tailwind @theme 变量名 | 工具类 |
|-------------|-------|----------------------|--------|
| `motion.duration.fast` | `150ms` | `--duration-fast` | `duration-[150ms]` |
| `motion.duration.normal` | `300ms` | `--duration-normal` | `duration-300` |
| `motion.duration.slow` | `500ms` | `--duration-slow` | `duration-500` |
| `motion.easing.ease-out` | `cubic-bezier(0.0,0.0,0.2,1)` | `--ease-out` | `ease-out` |
| `motion.easing.ease-in-out` | `cubic-bezier(0.4,0.0,0.2,1)` | `--ease-in-out` | `ease-in-out` |
| `motion.easing.bounce` | `cubic-bezier(0.34,1.56,0.64,1)` | `--ease-bounce` | `ease-[cubic-bezier(0.34,1.56,0.64,1)]` |

自定义 keyframes 建议（@theme 内定义）：
- `@keyframes float`：translateY(-8px) → translateY(8px)，infinite ease-in-out
- `@keyframes pulse-glow`：blur scale 脉动，infinite ease-in-out
- `@keyframes fade-in-up`：opacity 0→1 + translateY 12px→0，单次 ease-out

---

## 如何用此映射建立 Design System

### 1. 建立唯一事实源（Single Source of Truth）
在 `tailwind.config.ts`（v4：`@import "tailwindcss"` + `@theme { ... }`）中集中声明所有 CSS 变量，对应上表的 `--color-*`、`--spacing-*`、`--radius-*`、`--shadow-*`、`--font-*` 等。

### 2. 语义化分层命名原则
- 第一层：原始值（Primitive）：`--color-pink-300: #FFB7C5`
- 第二层：语义层（Semantic）：`--color-brand-primary: var(--color-pink-300)`
- 第三层：组件层（Component）：`--color-btn-bg: var(--color-brand-primary)`

### 3. 颜色模式扩展
为每个 Token 预留 Light/Dark 双值能力。Tailwind v4 原生支持 `@media (prefers-color-scheme: dark) { @theme { ... } }` 覆盖方式。

### 4. 工具类复合规则
避免在组件中直接使用原子工具类（如 `text-[#FFB7C5]`），始终通过语义 Token 工具类（如 `text-brand-primary`）引用，确保主题切换时一键生效。

### 5. 文档同步规则
每次修改 Design Token（03_design_tokens.md），必须同步更新 @theme 变量，并通过 CI 检查 Token 覆盖率（防止遗漏）。
