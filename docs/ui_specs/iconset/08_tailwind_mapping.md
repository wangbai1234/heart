# 08 Tailwind v4 映射规则 — Icon Set（24×24 系统图标）

## 说明

本文档仅建立 Design Token 到 Tailwind v4 的映射规则体系，不生成任何可执行代码。
Tailwind v4 使用 CSS 自定义属性（CSS Custom Properties）配合 `@theme` 指令定义设计系统。

---

## 图标颜色映射

### Token → Tailwind 映射表

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `icon.default` | #4A4A6A | `--color-icon-default` | `text-icon-default` / `stroke-icon-default` |
| `icon.primary` | #FFB7C5 | `--color-icon-primary` | `text-icon-primary` |
| `icon.secondary` | #A7C7E7 | `--color-icon-secondary` | `text-icon-secondary` |
| `icon.accent` | #C8B6FF | `--color-icon-accent` | `text-icon-accent` |
| `icon.disabled` | rgba(74,74,106,0.30) | `--color-icon-disabled` | `text-icon-disabled` |
| `icon.on-primary` | #FFFFFF | `--color-icon-on-primary` | `text-white` |
| `color.primary` | #FFB7C5 | `--color-primary` | `text-primary` / `bg-primary` |
| `color.secondary` | #A7C7E7 | `--color-secondary` | `text-secondary` / `bg-secondary` |
| `color.accent` | #C8B6FF | `--color-accent` | `text-accent` / `bg-accent` |
| `color.ink` | #3A3A4A | `--color-ink` | `text-ink` |
| `surface.canvas` | #FAF0EC | `--color-surface-canvas` | `bg-surface-canvas` |
| `surface.card` | #FFFFFF | `--color-surface-card` | `bg-white` |
| `surface.default` | #FFF8F3 | `--color-surface` | `bg-surface` |

### 语义色映射

| Design Token | 值 | Tailwind 变量名 |
|-------------|-----|----------------|
| `semantic.success` | #68D391 | `--color-success` |
| `semantic.warning` | #F6AD55 | `--color-warning` |
| `semantic.error` | #FC8181 | `--color-error` |
| `semantic.info` | #76E4F7 | `--color-info` |

---

## 图标尺寸映射

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `spacing.icon.size-sm` | 16px | `--size-icon-sm` | `size-4`（Tailwind 4 = 16px） |
| `spacing.icon.size-md` | 24px | `--size-icon-md` | `size-6`（Tailwind 6 = 24px） |
| `spacing.icon.size-lg` | 32px | `--size-icon-lg` | `size-8`（Tailwind 8 = 32px） |
| `spacing.icon.touch-target` | 44px | `--size-touch-target` | `size-11`（Tailwind 11 = 44px） |

---

## Spacing Scale 映射

| Design Token | 值 | Tailwind 变量名 | 对应 Tailwind 类 |
|-------------|-----|----------------|----------------|
| `spacing.icon.padding-inner` | 10px | `--spacing-icon-inner` | `p-2.5` |
| `spacing.icon.grid-gap` | 38px（估算） | `--spacing-icon-gap` | 自定义（约 `gap-[38px]`） |
| `spacing.icon.canvas-padding` | 60px（估算） | `--spacing-canvas-padding` | 自定义（约 `p-[60px]`） |

### 标准 Spacing Scale

| 值 | Tailwind 单位 | Tailwind 类示例 |
|----|-------------|----------------|
| 4px | 1 | `p-1`, `m-1`, `gap-1` |
| 8px | 2 | `p-2`, `gap-2` |
| 10px | 2.5 | `p-2.5` |
| 12px | 3 | `p-3`, `rounded-3` |
| 16px | 4 | `p-4`, `size-4` |
| 20px | 5 | `rounded-5`（圆角） |
| 24px | 6 | `size-6`（图标标准尺寸） |
| 32px | 8 | `size-8` |
| 44px | 11 | `size-11`（触控目标） |

---

## Radius 映射

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `radius.icon-container` | 20px | `--radius-card` | `rounded-[20px]` 或 `rounded-2xl`（16px接近值） |
| `radius.icon-bg` | 12px | `--radius-icon-bg` | `rounded-xl`（Tailwind xl = 12px，精确匹配） |
| `radius.icon-none` | 0 | — | `rounded-none` |

### Tailwind v4 Radius 参考

| Tailwind 类 | 值 |
|------------|-----|
| `rounded-sm` | 4px |
| `rounded-md` | 8px（估算） |
| `rounded-lg` | 8px |
| `rounded-xl` | 12px |
| `rounded-2xl` | 16px |
| `rounded-3xl` | 24px |
| `rounded-full` | 9999px |

---

## Blur 映射

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `blur.glass.toolbar` | 20px | `--blur-glass-toolbar` | `backdrop-blur-[20px]` |
| `blur.glass.nav` | 16px | `--blur-glass-nav` | `backdrop-blur-[16px]` 或 `backdrop-blur-xl`（Tailwind xl=24px，需自定义） |

### Tailwind v4 Blur 参考

| Tailwind 类 | 值 |
|------------|-----|
| `backdrop-blur-sm` | 8px |
| `backdrop-blur-md` | 12px |
| `backdrop-blur-lg` | 16px |
| `backdrop-blur-xl` | 24px |
| `backdrop-blur-2xl` | 40px |

---

## Shadow / Glow 映射

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `shadow.icon.glow-pink` | 0 0 12px rgba(255,183,197,0.60) | `--shadow-glow-pink` | `shadow-[0_0_12px_rgba(255,183,197,0.60)]` |
| `shadow.icon.glow-purple` | 0 0 12px rgba(200,182,255,0.60) | `--shadow-glow-purple` | `shadow-[0_0_12px_rgba(200,182,255,0.60)]` |
| `shadow.icon.glow-blue` | 0 0 12px rgba(167,199,231,0.60) | `--shadow-glow-blue` | `shadow-[0_0_12px_rgba(167,199,231,0.60)]` |

---

## Font / Typography 映射

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `type.icon-label` | PingFang SC / 10px / Regular | `--font-chinese` | `font-chinese text-[10px] font-normal` |
| `type.icon-label-active` | PingFang SC / 10px / Medium | — | `font-chinese text-[10px] font-medium` |

### Font Family 映射

| Token | 字体栈 | Tailwind 变量 |
|-------|--------|--------------|
| 中文字体 | PingFang SC, HarmonyOS Sans SC, system-ui | `--font-chinese` |
| 英文/数字 | SF Pro Rounded, system-ui | `--font-latin` |

---

## Animation / Motion 映射

| Design Token | 值 | Tailwind 变量名 | 使用方式 |
|-------------|-----|----------------|---------|
| `motion.icon.tap-duration` | 100ms | `--duration-tap` | `duration-100` |
| `motion.icon.hover-duration` | 150ms | `--duration-hover` | `duration-150` |
| `motion.icon.select-duration` | 200ms | `--duration-select` | `duration-200` |
| `motion.icon.glow-duration` | 300ms | `--duration-glow` | `duration-300` |
| `motion.icon.tap-easing` | ease-out | `--ease-tap` | `ease-out` |
| `motion.icon.hover-easing` | ease-in-out | `--ease-hover` | `ease-in-out` |
| `motion.icon.select-easing` | cubic-bezier(0.34,1.56,0.64,1) | `--ease-spring` | `ease-[cubic-bezier(0.34,1.56,0.64,1)]` |
| `motion.icon.tap-scale` | 0.88 | `--scale-pressed` | `scale-[0.88]` |

---

## Opacity 映射

| Design Token | 值 | Tailwind 使用方式 |
|-------------|-----|-----------------|
| `opacity.icon.default` | 100% | `opacity-100` |
| `opacity.icon.disabled` | 30% | `opacity-30` |
| `opacity.icon.pressed` | 70% | `opacity-70` |
| `opacity.icon.ghost` | 50% | `opacity-50` |

---

## Design System 建立规则总结

### Tailwind v4 @theme 配置层次

```
Layer 1: 基础 Token 注册（@theme 块）
  └── Colors / Radius / Spacing / Font / Shadow / Animation

Layer 2: 组件级变量（@layer components）
  └── .icon-default / .icon-active / .icon-disabled

Layer 3: 复合状态类
  └── .icon-glow-pink / .icon-nav-active
```

### currentColor 机制建议

所有 SVG 图标使用 `stroke="currentColor"` + `fill="none"`，
通过父元素的 `text-{color}` 类控制图标颜色，无需修改 SVG 内部属性。

```
映射链：
text-icon-primary (Tailwind)
  → color: var(--color-icon-primary) (CSS)
    → currentColor (SVG stroke)
      → 图标渲染色 #FFB7C5
```

### 图标尺寸 Tailwind 映射原则

- 图标容器使用 `size-{n}`（Tailwind v4 新增 `size` 工具类，等同于 `w-{n} h-{n}`）
- 触控区域使用 `size-11`（44px）包裹实际 `size-6`（24px）图标
- 内边距通过 `p-2.5` 实现 10px 四周间距
