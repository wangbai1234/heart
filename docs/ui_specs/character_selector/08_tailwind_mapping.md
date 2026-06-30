# 08 Tailwind Mapping — 角色页 Character Selector

> 本文件仅建立 Design Token 到 Tailwind v4 `@theme` 的映射规则。
> 不包含任何代码实现，不生成 React/HTML/CSS 代码。

---

## Colors（颜色映射）

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `color-primary` | `bg-primary` / `text-primary` / `border-primary` | `#FFB7C5` |
| `color-primary-deep` | `bg-primary-deep` | `#FF8FAB` |
| `color-secondary` | `bg-secondary` / `text-secondary-brand` | `#A7C7E7` |
| `color-accent` | `bg-accent` / `text-accent` | `#C8B6FF` |
| `color-surface` | `bg-surface` | `#FFF8F3` |
| `color-card` | `bg-card` | `#FFFFFF` |
| `color-glass` | `bg-glass` | `rgba(255,255,255,0.55)` |
| `color-glass-border` | `border-glass` | `rgba(255,255,255,0.70)` |
| `color-ink` | `text-ink` | `#3A3A4A` |
| `color-ink-heavy` | `text-ink-heavy` | `#1A1A2E` |
| `color-text-secondary` | `text-secondary` | `rgba(58,58,74,0.65)` |
| `color-text-on-primary` | `text-on-primary` | `#FFFFFF` |
| `color-text-tag` | `text-tag-oji` | `#8B5CF6`（估算值） |
| `color-text-tag-genki` | `text-tag-genki` | `#3B82F6`（估算值） |
| `color-selected` | `bg-selected` | `#FFB7C5` |
| `color-border-unselected` | `border-unselected` | `#FFB7C5` |
| `color-overlay` | `bg-overlay` | `rgba(255,248,243,0.80)` |
| `color-success` | `bg-success` / `text-success` | `#5CC8A4` |
| `color-warning` | `bg-warning` / `text-warning` | `#FFCA7A` |
| `color-danger` | `bg-danger` / `text-danger` | `#FF6B6B` |
| `color-divider` | `border-divider` | `rgba(58,58,74,0.10)` |

---

## Spacing（间距映射）

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `spacing-1` | `p-1` / `m-1` / `gap-1` | 4 pt |
| `spacing-2` | `p-2` / `m-2` / `gap-2` | 8 pt |
| `spacing-3` | `p-3` / `m-3` / `gap-3` | 12 pt |
| `spacing-4` | `p-4` / `m-4` / `gap-4` | 16 pt |
| `spacing-5` | `p-5` / `m-5` / `gap-5` | 20 pt |
| `spacing-6` | `p-6` / `m-6` / `gap-6` | 24 pt |
| `spacing-8` | `p-8` / `m-8` / `gap-8` | 32 pt |
| `spacing-10` | `p-10` / `m-10` | 40 pt |
| `spacing-12` | `p-12` / `m-12` | 48 pt |
| `spacing-16` | `p-16` / `m-16` | 64 pt |

---

## Radius（圆角映射）

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `radius-xs` | `rounded-xs` | 4 pt |
| `radius-sm` | `rounded-sm` | 8 pt |
| `radius-md` | `rounded-md` | 12 pt |
| `radius-lg` | `rounded-lg` | 16 pt |
| `radius-xl` | `rounded-xl` | 20 pt |
| `radius-2xl` | `rounded-2xl` | 24 pt |
| `radius-pill` | `rounded-pill` | 27 pt |
| `radius-full` | `rounded-full` | 9999 pt |

---

## Blur（模糊映射）

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `blur-glass-heart` | `backdrop-blur-glass` | 8 pt（估算值） |
| `blur-none` | `backdrop-blur-none` | 0 |

---

## Shadow（阴影映射）

| Design Token | Tailwind 类名 | 值描述 |
|-------------|-------------|------|
| `shadow-card` | `shadow-card` | rgba(0,0,0,0.06) Blur 12 Y+4 |
| `shadow-cta-button` | `shadow-cta` | rgba(255,143,171,0.35) Blur 16 Y+6 |
| `shadow-avatar-rin` | `shadow-avatar-purple` | rgba(200,182,255,0.5) Blur 8 Spread 4 |
| `shadow-avatar-taolesi` | `shadow-avatar-blue` | rgba(167,199,231,0.5) Blur 8 Spread 4 |
| `shadow-heart-glass` | `shadow-heart` | rgba(255,183,197,0.3) Blur 20 Y+8 |

---

## Font（字体映射）

### Font Family

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `font-family-chinese` | `font-chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` |
| `font-family-latin` | `font-rounded` | `SF Pro Rounded, system-ui, sans-serif` |

### Font Size

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `text-status-bar` | `text-xs-status` | 15 pt |
| `text-header-title` | `text-base-header` | 17 pt |
| `text-character-name` | `text-lg-name` | 18 pt |
| `text-tag` | `text-xs-tag` | 12 pt |
| `text-description` | `text-sm-desc` | 13 pt |
| `text-cta-button` | `text-base-cta` | 17 pt |
| `text-select-button` | `text-sm-select` | 15 pt |

### Font Weight

| 值 | Tailwind 类名 |
|----|-------------|
| 400 Regular | `font-normal` |
| 500 Medium | `font-medium` |
| 600 Semibold | `font-semibold` |
| 700 Bold | `font-bold` |

---

## Animation（动画映射）

| Design Token | Tailwind 类名 | 值 |
|-------------|-------------|---|
| `duration-fast` | `duration-150` | 150 ms |
| `duration-normal` | `duration-250` | 250 ms |
| `duration-slow` | `duration-400` | 400 ms |
| `duration-hero` | `duration-600` | 600 ms |
| `easing-standard` | `ease-standard` | `cubic-bezier(0.4,0.0,0.2,1)` |
| `easing-decelerate` | `ease-decelerate` | `cubic-bezier(0.0,0.0,0.2,1)` |
| `easing-bounce` | `ease-bounce-out` | `cubic-bezier(0.34,1.56,0.64,1)` |

---

## Gradient（渐变映射）

| Design Token | Tailwind 类名 | 说明 |
|-------------|-------------|------|
| `gradient-cta-button` | `bg-gradient-cta` | #FF8FAB → #FFB7C5 水平渐变 |
| `gradient-hero-bottom-fade` | `bg-gradient-hero-fade` | 透明 → #FFF8F3 顶到底 |

---

## 如何用此映射建立 Design System

### 原则
此映射不是直接写样式，而是建立**语义化 Token 层**，让所有组件通过 Token 名称引用颜色/间距/圆角，而非直接写原始值（如 `#FFB7C5`）。

### 层次结构建议

```
Layer 1: Primitive Tokens（原始值）
  - 直接对应 hex/rgba/pt 值
  - 例：color-pink-300 = #FFB7C5

Layer 2: Semantic Tokens（语义化）
  - 引用 Primitive Token，赋予语义意义
  - 例：color-primary = color-pink-300

Layer 3: Component Tokens（组件级）
  - 引用 Semantic Token，描述组件用途
  - 例：button-confirm-bg = color-primary

Layer 4: Tailwind @theme 映射
  - 将 Layer 2/3 Token 映射为 Tailwind 工具类
  - 例：--color-primary: #FFB7C5 → bg-primary
```

### 使用规则
1. 任何颜色不直接写 hex 值，必须通过 Token 名称引用
2. 间距值使用 spacing scale（4pt 基础单位），不使用任意值（arbitrary values）
3. 圆角值使用预定义 radius token，不使用随机数字
4. 渐变通过 `@theme` 定义为具名渐变，不在组件中内联写渐变
5. 阴影通过 shadow token 引用，不内联写 box-shadow 值
6. 字体大小通过 font-size token 引用，保证全局一致性
7. 动画 duration/easing 通过 token 引用，便于全局调整动画速度感
