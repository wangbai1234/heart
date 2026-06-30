# 08 Tailwind v4 Mapping — 离线降级状态页

> 注意：本文件为 Design Token → Tailwind v4 CSS Variable 映射规则，供工程实现参考。
> 设计规范以 PNG 和 Design Tokens（03_design_tokens.md）为准。
> 无法直接用 Tailwind class 表达的值，提供 CSS Variable 或 arbitrary value。

---

## Colors

### `@theme` CSS 变量定义（在 globals.css 中声明）

```css
/* 添加到 @theme {} 或 :root {} */

/* Brand */
--color-primary: #FFB7C5;
--color-secondary: #A7C7E7;
--color-accent: #C8B6FF;
--color-surface: #FFF8F3;
--color-ink: #3A3A4A;

/* Backgrounds */
--color-bg-page-top: #FFF0F0;
--color-bg-page-bottom: #FFF8F3;
--color-bg-banner: rgba(255, 255, 255, 0.85);
--color-bg-bubble-ai: rgba(255, 255, 255, 0.90);
--color-bg-bubble-user-from: #FFE4EC;
--color-bg-bubble-user-to: #FFDDE8;
--color-bg-composer: rgba(255, 255, 255, 0.80);
--color-bg-input: rgba(255, 255, 255, 0.60);
--color-bg-clock-btn: #FFB7C5;

/* Text */
--color-text-primary: #3A3A4A;
--color-text-secondary: #A0A0B0;
--color-text-muted: #ACACAC;
--color-text-staged: #C0A0A0;
--color-text-placeholder: #C0C0C8;
--color-text-retry: #FFB7C5;

/* Borders */
--color-border-retry: #FFB7C5;
--color-border-add-btn: #D0D0D0;
--color-border-composer: rgba(0, 0, 0, 0.08);
```

### Tailwind Class 对照表

| Token | Tailwind Class | Arbitrary Value |
|-------|---------------|-----------------|
| `color.primary` | `bg-primary` / `text-primary` / `border-primary` | `bg-[#FFB7C5]` |
| `color.secondary` | `bg-secondary` / `text-secondary` | `bg-[#A7C7E7]` |
| `color.ink` | `text-ink` | `text-[#3A3A4A]` |
| `color.text.muted` | `text-muted` | `text-[#ACACAC]` |
| `color.text.staged` | `text-staged` | `text-[#C0A0A0]` |
| `color.text.placeholder` | — | `placeholder:text-[#C0C0C8]` |
| `color.bg.banner` | — | `bg-[rgba(255,255,255,0.85)]` |
| `color.bg.bubble.ai` | — | `bg-[rgba(255,255,255,0.90)]` |
| `color.bg.composer` | — | `bg-[rgba(255,255,255,0.80)]` |
| `color.bg.input` | — | `bg-[rgba(255,255,255,0.60)]` |
| `color.border.composer-top` | — | `border-[rgba(0,0,0,0.08)]` |

---

## Gradients

| 用途 | Tailwind / CSS |
|------|---------------|
| 页面背景 | `bg-gradient-to-b from-[#FFF0F0] to-[#FFF8F3]` |
| 用户气泡 | `bg-gradient-to-br from-[#FFE4EC] to-[#FFDDE8]` |

---

## Spacing

| Token | 值 | Tailwind Class |
|-------|-----|---------------|
| `spacing.page-h` | 16 pt | `px-4` |
| `spacing.banner-pad-h` | 16 pt | `px-4` |
| `spacing.banner-pad-v` | 12 pt | `py-3` |
| `spacing.bubble-pad-h` | 12 pt | `px-3` |
| `spacing.bubble-pad-v` | 10 pt | `py-2.5` |
| `spacing.composer-pad-h` | 16 pt | `px-4` |
| `spacing.composer-pad-v` | 8 pt | `py-2` |
| `spacing.avatar-bubble-gap` | 8 pt | `gap-2` |
| `spacing.banner-icon-gap` | 10 pt | `gap-2.5` |
| `spacing.staged-div-v` | 4 pt | `gap-1` |
| `spacing.input-gap` | 8 pt | `gap-2` |
| `spacing.bubble-gap-v` | 8 pt | `gap-2` |
| `spacing.group-gap-v` | 16 pt | `gap-4` |

---

## Border Radius

| Token | 值 | Tailwind Class |
|-------|-----|---------------|
| `radius.banner` | 16 pt | `rounded-2xl` |
| `radius.retry-btn` | 16 pt (pill) | `rounded-full` |
| `radius.avatar` | 50% | `rounded-full` |
| `radius.clock-btn` | 50% | `rounded-full` |
| `radius.add-btn` | 50% | `rounded-full` |
| `radius.input` | 18 pt (pill) | `rounded-full` |
| AI 气泡（不等角） | TL:4 TR:16 BR:16 BL:16 | `rounded-[4px_16px_16px_16px]` |
| 用户气泡（不等角） | TL:16 TR:4 BR:16 BL:16 | `rounded-[16px_4px_16px_16px]` |

---

## Blur / Backdrop Filter

| 用途 | Tailwind Class |
|------|---------------|
| 横幅毛玻璃 | `backdrop-blur-sm` （≈ blur(8px)，可用 `backdrop-blur-[8px]`） |
| Composer 毛玻璃 | `backdrop-blur-sm` 或 `backdrop-blur-[8px]` |

---

## Shadow

| Token | Tailwind / CSS |
|-------|---------------|
| `shadow.banner` | `shadow-[0_2px_8px_rgba(0,0,0,0.06)]` |
| `shadow.bubble.ai` | `shadow-[0_1px_4px_rgba(0,0,0,0.05)]` |
| `shadow.clock-btn` | `shadow-[0_2px_6px_rgba(255,183,197,0.40)]` |

---

## Opacity

| Token | 值 | Tailwind Class |
|-------|-----|---------------|
| `opacity.history-dimmed` | 0.92 | `opacity-[0.92]` |
| `opacity.banner-bg` | 0.85 | （嵌入 bg color 的 alpha 通道，无独立 class） |
| `opacity.retry-btn-loading` | 0.6 | `opacity-60` |

---

## Typography

| Token | 字号/字重 | Tailwind Class |
|-------|---------|---------------|
| `type.nav-title` | 17pt / SemiBold | `text-[17px] font-semibold` |
| `type.nav-subtitle` | 12pt / Regular | `text-xs font-normal` |
| `type.banner-text` | 14pt / Regular | `text-sm font-normal` |
| `type.retry-btn` | 13pt / Medium | `text-[13px] font-medium` |
| `type.timestamp` | 12pt / Regular | `text-xs font-normal` |
| `type.bubble-text` | 15pt / Regular | `text-[15px] font-normal` |
| `type.staged-label` | 13pt / Regular | `text-[13px] font-normal` |
| `type.staged-sub` | 12pt / Regular | `text-xs font-normal` |
| `type.placeholder` | 15pt / Regular | `text-[15px] font-normal` |

### 字体家族 CSS（`@layer base` 中）
```css
/* 中文 */
.font-chinese {
  font-family: 'PingFang SC', 'HarmonyOS Sans SC', sans-serif;
}
/* 英数 */
.font-latin {
  font-family: 'SF Pro Rounded', system-ui, sans-serif;
}
```

---

## Animation / Transition

| 用途 | Tailwind / CSS |
|------|---------------|
| 历史区暗淡过渡 | `transition-opacity duration-[400ms] ease-out` |
| 横幅入场 | 自定义 `@keyframes` + Tailwind `animate-[banner-enter_300ms_cubic-bezier(0.34,1.56,0.64,1)_forwards]` |
| 横幅离场 | `animate-[banner-exit_200ms_ease-in_forwards]` |
| 副标题文字切换 | `transition-opacity duration-150` |
| 时钟按钮弹入 | `animate-[scale-in_200ms_cubic-bezier(0.34,1.56,0.64,1)_100ms_forwards]` |
| 暂存分割线淡入 | `animate-[fade-in_250ms_ease-out_150ms_forwards]` |
| 重试图标旋转 | `animate-spin` （Tailwind 内置） |
| 按钮按压缩放 | `active:scale-[0.96] transition-transform duration-100` |

### 自定义 @keyframes（globals.css）
```css
@keyframes banner-enter {
  from { opacity: 0; transform: translateY(-20px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes banner-exit {
  from { opacity: 1; transform: translateY(0); }
  to   { opacity: 0; transform: translateY(-20px); }
}

@keyframes scale-in {
  from { opacity: 0; transform: scale(0.5); }
  to   { opacity: 1; transform: scale(1.0); }
}

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
```

---

## Tailwind v4 Config 扩展片段（供参考，非实现代码）

```
在 @theme {} 中扩展自定义 token，参照 03_design_tokens.md 中的 CSS 变量名。
颜色命名遵循：--color-<category>-<name>
间距命名遵循：--spacing-<name>
```
