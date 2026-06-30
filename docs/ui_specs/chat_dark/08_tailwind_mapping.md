# 08 Tailwind Mapping — 聊天页 Chat（深色模式）

> 本文件仅建立 Design Token 与 Tailwind v4 @theme 的映射规则，不生成任何代码实现。
> 基于 Tailwind CSS v4 的 @theme 语法（CSS 自定义属性系统）建立映射。

---

## Colors 颜色映射

### 主色 Primary

| Design Token | Hex/RGBA | Tailwind @theme 变量名 | 工具类名称 |
|-------------|----------|-----------------------|-----------|
| `color-primary` | `#FFB7C5` | `--color-primary` | `bg-primary` / `text-primary` / `border-primary` |
| `color-primary-dark` | `#E8A0B0` | `--color-primary-dark` | `bg-primary-dark` |
| `color-secondary` | `#A7C7E7` | `--color-secondary` | `bg-secondary` / `text-secondary` |
| `color-accent` | `#C8B6FF` | `--color-accent` | `bg-accent` / `text-accent` |
| `color-accent-deep` | `#9B8EC4` | `--color-accent-deep` | `bg-accent-deep` |

### 背景色 Background

| Design Token | Hex/RGBA | Tailwind @theme 变量名 | 工具类名称 |
|-------------|----------|-----------------------|-----------|
| `color-bg-page` | `#1B1923` | `--color-bg-page` | `bg-page` |
| `color-bg-nebula` | `#221B32` | `--color-bg-nebula` | `bg-nebula` |
| `color-surface-dark` | `rgba(30,27,40,0.85)` | `--color-surface-dark` | `bg-surface-dark` |
| `color-surface-bubble-ai` | `rgba(45,40,65,0.90)` | `--color-surface-bubble-ai` | `bg-bubble-ai` |
| `color-surface-input` | `rgba(255,255,255,0.08)` | `--color-surface-input` | `bg-input` |
| `color-surface-plus-btn` | `rgba(255,255,255,0.12)` | `--color-surface-plus` | `bg-plus-btn` |

### 玻璃效果 Glass

| Design Token | RGBA | Tailwind @theme 变量名 | 工具类名称 |
|-------------|------|----------------------|-----------|
| `color-glass-header` | `rgba(30,27,40,0.75)` | `--color-glass-header` | `bg-glass-header` |
| `color-glass-input-bar` | `rgba(30,27,40,0.80)` | `--color-glass-input` | `bg-glass-input` |
| `color-glass-border` | `rgba(255,255,255,0.10)` | `--color-glass-border` | `border-glass` |

### 文字色 Text

| Design Token | Hex/RGBA | Tailwind @theme 变量名 | 工具类名称 |
|-------------|----------|-----------------------|-----------|
| `color-text-primary` | `#FFFFFF` | `--color-text-primary` | `text-t-primary` |
| `color-text-secondary` | `rgba(255,255,255,0.70)` | `--color-text-secondary` | `text-t-secondary` |
| `color-text-caption` | `rgba(255,255,255,0.45)` | `--color-text-caption` | `text-caption` |
| `color-text-placeholder` | `rgba(255,255,255,0.40)` | `--color-text-placeholder` | `text-placeholder` |
| `color-text-ai-bubble` | `#F0EEFF` | `--color-text-ai-bubble` | `text-ai-bubble` |

### 特殊功能色

| Design Token | Hex/RGBA | Tailwind @theme 变量名 | 工具类名称 |
|-------------|----------|-----------------------|-----------|
| `color-online-dot` | `#7EB8F7` | `--color-online` | `bg-online` |
| `color-send-btn` | `#FFB7C5` | 同 `--color-primary` | `bg-primary` |
| `color-play-btn-bg` | `rgba(255,183,197,0.25)` | `--color-play-bg` | `bg-play-btn` |

### 系统状态色

| Design Token | Hex | Tailwind @theme 变量名 | 工具类名称 |
|-------------|-----|----------------------|-----------|
| `color-success` | `#7BE89E` | `--color-success` | `bg-success` / `text-success` |
| `color-warning` | `#FFD580` | `--color-warning` | `bg-warning` / `text-warning` |
| `color-danger` | `#FF7A7A` | `--color-danger` | `bg-danger` / `text-danger` |
| `color-info` | `#7EB8F7` | `--color-info` | `bg-info` / `text-info` |

---

## Spacing 间距映射

> 基于 4px 倍数体系，映射到 Tailwind 默认 spacing scale（1 unit = 4px）

| Design Token | 值 | Tailwind 工具类（间距） |
|-------------|---|----------------------|
| `space-1` | 4 px | `p-1` / `m-1` / `gap-1` |
| `space-2` | 8 px | `p-2` / `m-2` / `gap-2` |
| `space-3` | 12 px | `p-3` / `m-3` / `gap-3` |
| `space-4` | 16 px | `p-4` / `m-4` / `gap-4` |
| `space-5` | 20 px | `p-5` / `m-5` / `gap-5` |
| `space-6` | 24 px | `p-6` / `m-6` / `gap-6` |
| `space-8` | 32 px | `p-8` / `m-8` / `gap-8` |
| `space-10` | 40 px | `p-10` / `m-10` |
| `space-12` | 48 px | `p-12` / `m-12` |
| `space-16` | 64 px | `p-16` / `m-16` |

---

## Radius 圆角映射

| Design Token | 值 | Tailwind @theme 变量名 | 工具类名称 |
|-------------|---|----------------------|-----------|
| `radius-xs` | 8 px | `--radius-xs` | `rounded-xs` |
| `radius-sm` | 12 px | `--radius-sm` | `rounded-sm` |
| `radius-md` | 16 px | `--radius-md` | `rounded-md` |
| `radius-lg` | 24 px | `--radius-lg` | `rounded-lg` |
| `radius-xl` | 32 px | `--radius-xl` | `rounded-xl` |
| `radius-2xl` | 40 px | `--radius-2xl` | `rounded-2xl` |
| `radius-full` | 9999 px | `--radius-full` | `rounded-full` |

---

## Blur 模糊映射

| Design Token | 值 | Tailwind @theme 变量名 | 工具类名称 |
|-------------|---|----------------------|-----------|
| `blur-glass-sm` | 12 px | `--blur-glass-sm` | `backdrop-blur-glass-sm` |
| `blur-glass-md` | 20 px | `--blur-glass-md` | `backdrop-blur-glass-md` |
| `blur-glass-lg` | 32 px | `--blur-glass-lg` | `backdrop-blur-glass-lg` |
| `blur-bg-decoration` | 40 px | `--blur-bg` | `blur-bg` |

> Tailwind v4 backdrop-blur 映射：`backdrop-blur-[20px]` 或注册自定义工具类

---

## Shadow 阴影映射

| Design Token | 参数 | Tailwind @theme 变量名 | 工具类名称 |
|-------------|------|----------------------|-----------|
| `shadow-bubble-ai` | `0 0 20px rgba(255,183,197,0.25)` | `--shadow-bubble-ai` | `shadow-bubble-ai` |
| `shadow-send-btn` | `0 4px 16px rgba(255,183,197,0.40)` | `--shadow-send` | `shadow-send` |
| `shadow-header` | `0 4px 12px rgba(0,0,0,0.20)` | `--shadow-header` | `shadow-header` |
| `shadow-voice-bubble` | `0 0 24px rgba(255,183,197,0.20)` | `--shadow-voice` | `shadow-voice` |

---

## Font 字体映射

### 字体族

| Design Token | 字体 | Tailwind @theme 变量名 | 工具类名称 |
|-------------|------|----------------------|-----------|
| Chinese | PingFang SC / HarmonyOS Sans SC | `--font-chinese` | `font-chinese` |
| Latin/Numbers | SF Pro Rounded | `--font-latin` | `font-latin` |

### 字号

| Design Token | 值（估算）| Tailwind @theme 变量名 | 工具类名称 |
|-------------|----------|----------------------|-----------|
| `type-caption` | ~22 px | `--text-caption` | `text-caption` |
| `type-status` | ~22 px | `--text-status` | `text-status` |
| `type-body-md` | ~28 px | `--text-body-md` | `text-body-md` |
| `type-body-lg` | ~28 px | `--text-body-lg` | `text-body-lg` |
| `type-title-lg` | ~32 px | `--text-title-lg` | `text-title-lg` |

### 字重

| 值 | Tailwind 工具类 |
|----|---------------|
| Regular / 400 | `font-normal` |
| Medium / 500 | `font-medium` |
| SemiBold / 600 | `font-semibold` |

---

## Animation 动效映射

| Design Token | 值 | Tailwind @theme 变量名 | 工具类名称 |
|-------------|---|----------------------|-----------|
| `duration-fast` | 150ms | `--duration-fast` | `duration-fast` |
| `duration-normal` | 250ms | `--duration-normal` | `duration-normal` |
| `duration-slow` | 400ms | `--duration-slow` | `duration-slow` |
| `easing-standard` | `cubic-bezier(0.4,0,0.2,1)` | `--ease-standard` | `ease-standard` |
| `easing-decelerate` | `cubic-bezier(0.0,0.0,0.2,1)` | `--ease-decelerate` | `ease-decelerate` |
| `easing-accelerate` | `cubic-bezier(0.4,0,1,1)` | `--ease-accelerate` | `ease-accelerate` |

---

## 如何用这套映射建立 Design System

### 1. 建立 @theme 层（全局 CSS 变量）
将所有 Design Token 在 Tailwind v4 的 `@theme` 块中注册为 CSS 自定义属性。这使得所有工具类（如 `bg-primary`、`text-caption`）在编译时直接引用设计系统变量，而非硬编码颜色值。

### 2. Token 分层原则
- **Primitive Tokens**（基础色板）：`#FFB7C5`、`#1B1923` 等原始值
- **Semantic Tokens**（语义色）：`color-bg-page`、`color-text-primary` 等，引用 Primitive
- **Component Tokens**（组件专用）：`color-surface-bubble-ai`、`shadow-bubble-ai` 等，引用 Semantic

### 3. 深色模式实现策略
所有颜色 Token 在 `@theme` 中定义深色版本，通过 `@media (prefers-color-scheme: dark)` 或 `[data-theme="dark"]` 切换。本页（chat_dark）即为深色模式的 token 状态。

### 4. 组件样式约束
- 禁止在组件中硬编码颜色、间距、圆角值
- 所有样式值必须通过工具类引用对应 Token 变量
- 气泡类组件（AITextBubble、UserTextBubble）共享基础 token，通过 variant 区分

### 5. 维护规则
- Design Token 变更只需更新 `@theme` 块，全局生效
- 新增颜色或组件 token 遵循现有命名规范（kebab-case，前缀明确）
- 每次设计稿更新后，Token 文件（03_design_tokens.md）与 `@theme` 映射同步更新
