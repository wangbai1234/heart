# 08 Tailwind v4 映射规则 — 加载 / 空状态

> 注意：以下映射基于 Tailwind CSS v4 语法（CSS-first config，使用 `@theme` / `@layer`）。
> 自定义值通过 CSS 变量（`--color-*`, `--spacing-*` 等）在 `@theme` 中声明。
> 仅为设计规范映射，不包含任何框架代码实现。

---

## Colors

### 自定义颜色声明（@theme）

```css
/* 在 @theme 块中声明，映射设计 Token */
@theme {
  --color-brand-cherry: #FFB7C5;
  --color-brand-sky: #A7C7E7;
  --color-brand-lavender: #C8B6FF;
  --color-brand-cream: #FFF8F3;

  --color-bg-page: #FDF0EE;
  --color-bg-skeleton: #F2D0D8;
  --color-bg-skeleton-avatar: #F2C8D0;

  --color-text-primary: #3A3A4A;
  --color-text-secondary: #A07888;
  --color-text-placeholder: #C8B6C8;

  --color-icon-default: #8A8A9A;
  --color-icon-pink: #FFB7C5;
  --color-icon-gold: #E8C84A;
}
```

### 使用映射表

| 设计 Token | Tailwind Class | 用途 |
|-----------|--------------|------|
| `color.bg.page` | `bg-[--color-bg-page]` 或 `bg-(--color-bg-page)` | 页面背景 |
| `color.bg.skeleton` | `bg-[--color-bg-skeleton]` | 骨架矩形 |
| `color.bg.skeleton-avatar` | `bg-[--color-bg-skeleton-avatar]` | 骨架头像圆 |
| `color.brand.cherry-pink` | `bg-[--color-brand-cherry]` / `text-[--color-brand-cherry]` | Pill 图标、Mic 按钮 |
| `color.text.primary` | `text-[--color-text-primary]` | 角色名、引导文字 |
| `color.text.secondary` | `text-[--color-text-secondary]` | 副标题、状态文字 |
| `color.text.placeholder` | `placeholder-[--color-text-placeholder]` | 输入框占位 |
| `color.icon.default` | `text-[--color-icon-default]` | Header 图标 |
| Pill 背景 | `bg-white/80` | 约 rgba(255,255,255,0.80) |
| Pill 描边 | `border border-[#FFB7C5]/40` 或 `ring-1 ring-[#FFB7C5]/40` | Pill 边框 |

---

## Spacing

### 自定义间距声明

```css
@theme {
  --spacing-page-h: 1.25rem;   /* ~20pt */
  --spacing-header-v: 0.75rem; /* ~12pt */
  --spacing-pill-h: 1.5rem;    /* ~24pt */
  --spacing-skeleton-gap: 2rem; /* ~32pt */
}
```

### 使用映射表

| 用途 | Tailwind Class | 值 |
|------|-------------|-----|
| 页面水平 Padding | `px-5` 或 `px-(--spacing-page-h)` | ~20pt |
| Header 垂直 Padding | `py-3` | ~12pt |
| Pill 水平 Padding | `px-6` | ~24pt |
| Pill 行 Gap | `gap-4` | ~16pt |
| 骨架气泡间 Gap | `gap-8` | ~32pt |
| 骨架多行 Gap | `gap-3` | ~12pt |
| 图标与文字间距 | `gap-2` | ~8pt |
| 头像与名字组间距 | `gap-4` | ~16pt |

---

## Border Radius

### 映射表

| 设计用途 | Tailwind Class | 值 |
|---------|-------------|-----|
| 完整圆形（头像、图标按钮）| `rounded-full` | 50% |
| Pill 胶囊 | `rounded-full` | 50% 或 `rounded-3xl`（~24px，自适应高度）|
| 骨架矩形 | `rounded-2xl` | ~16px |
| 气泡圆角（正常） | `rounded-2xl` 或 `rounded-[20px]` | ~20px |
| 输入栏容器 | `rounded-full` | |

---

## Blur / Filter

### 映射表

| 设计用途 | Tailwind Class | 值 |
|---------|-------------|-----|
| 云朵光晕柔化 | `blur-2xl` | ~24px（接近） |
| Glassmorphism（如需）| `backdrop-blur-md` | ~12px |

---

## Shadow

### 自定义阴影声明

```css
@theme {
  --shadow-avatar: 0 2px 8px rgba(0, 0, 0, 0.10);
  --shadow-pill: 0 2px 8px rgba(255, 183, 197, 0.25);
  --shadow-gem: 0 8px 32px rgba(200, 182, 255, 0.50);
}
```

### 使用映射表

| 设计用途 | Tailwind Class | 备注 |
|---------|-------------|------|
| 角色头像 | `shadow-sm` 或 `shadow-[--shadow-avatar]` | 0 2px 8px rgba(0,0,0,0.10) |
| 建议 Pill | `shadow-[--shadow-pill]` | 粉色调阴影 |
| 心形宝石光晕 | `shadow-[--shadow-gem]` | 紫色调光晕 |
| 骨架矩形 | `shadow-none` | 无阴影 |

---

## Typography / Font

### 字体族声明

```css
@theme {
  --font-cn: 'PingFang SC', 'HarmonyOS Sans SC', sans-serif;
  --font-latin: 'SF Pro Rounded', system-ui, sans-serif;
}
```

### 字号映射表

| 设计用途 | Tailwind Class | pt 值 |
|---------|-------------|------|
| 状态栏时间 | `text-base` 或 `text-[16pt]` | ~16pt |
| 角色名 | `text-lg` 或 `text-[17pt]` | ~17pt |
| 副标题/状态 | `text-xs` 或 `text-[12pt]` | ~12pt |
| 引导文字 | `text-xl` 或 `text-[18pt]` | ~18pt |
| Pill 标签 | `text-sm` 或 `text-[14pt]` | ~14pt |
| 输入占位 | `text-sm` 或 `text-[15pt]` | ~15pt |

### 字重映射

| 设计 Token | Tailwind Class |
|-----------|-------------|
| Regular (400) | `font-normal` |
| Medium (500) | `font-medium` |
| Semibold (600) | `font-semibold` |

---

## Animation / Keyframes

### 自定义动画声明

```css
@theme {
  --animate-shimmer: shimmer 1400ms linear infinite;
  --animate-pulse-float: pulse-float 2000ms ease-in-out infinite;
  --animate-dot-typing: dot-typing 900ms ease-in-out infinite;
}

/* 定义 keyframes（在 @layer base 或 @keyframes 中）*/
@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}

@keyframes pulse-float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-8px); }
}

@keyframes dot-typing {
  0%   { opacity: 0.3; }
  33%  { opacity: 1.0; }
  66%  { opacity: 0.3; }
  100% { opacity: 0.3; }
}
```

### 动画使用映射表

| 元素 | Tailwind Class | 说明 |
|------|-------------|------|
| GemHeart 浮动 | `animate-[--animate-pulse-float]` | Y 轴浮动 |
| 骨架矩形/圆 Shimmer | `animate-[--animate-shimmer]` | 扫光效果（作用于 overflow-hidden 伪元素）|
| Header 打点 | `animate-[--animate-dot-typing]` | 三个点错开 animation-delay |
| Pill 进入 | `animate-fade-in` + `delay-[400ms]` 等 | 依次出现 |

---

## Layout Utilities

| 用途 | Tailwind Class |
|------|-------------|
| Flex Row 水平布局 | `flex flex-row items-center` |
| Flex Column 垂直布局 | `flex flex-col` |
| 两端对齐 | `justify-between` |
| 居中 | `justify-center items-center` |
| 左对齐 | `justify-start` |
| 右对齐 | `justify-end` |
| Flex 占满剩余 | `flex-1` |
| 溢出隐藏（Shimmer 剪切）| `overflow-hidden relative` |
| 绝对定位（云朵/插画叠加）| `absolute inset-0` |
| 圆形裁切 | `rounded-full overflow-hidden` |
| Safe Area 底部 | `pb-[env(safe-area-inset-bottom)]` 或 `pb-8` |

---

## 完整 Pill 组件 Token 映射速查

| Token | Tailwind |
|-------|---------|
| 背景 | `bg-white/80` |
| 圆角 | `rounded-full` |
| 边框 | `border border-[#FFB7C5]/40` |
| 阴影 | `shadow-[0_2px_8px_rgba(255,183,197,0.25)]` |
| 内边距 | `px-6 py-0` （高度由 `h-16` 控制）|
| 高度 | `h-16` (~64px) |
| 图标尺寸 | `w-4 h-4` (~16px) 或 `size-5` |
| 图标文字间距 | `gap-2` |
| 文字颜色 | `text-[--color-text-primary]` |
| Pressed 缩放 | `active:scale-95` |
| 过渡 | `transition-transform duration-100` |
