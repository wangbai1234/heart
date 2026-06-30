# 08 Tailwind v4 映射规则 — 反馈组件三联

> 说明：本文件仅为设计 Token → Tailwind v4 工具类的映射参考，供开发人员快速查阅。
> 不包含任何组件实现代码。

---

## Colors 映射

### 品牌色

| Design Token | Tailwind v4 工具类 / CSS Variable | Hex 值 |
|--------------|----------------------------------|--------|
| `color.brand.primary` | `bg-[#FFB7C5]` / `text-[#FFB7C5]` / `border-[#FFB7C5]` | `#FFB7C5` |
| `color.brand.secondary` | `bg-[#A7C7E7]` | `#A7C7E7` |
| `color.brand.accent` | `bg-[#C8B6FF]` | `#C8B6FF` |

### 表面色

| Design Token | Tailwind v4 工具类 | Hex 值 |
|--------------|-------------------|--------|
| `color.surface.canvas` | `bg-[#FFF0F3]` | `#FFF0F3` |
| `color.surface.cream` | `bg-[#FFF8F3]` | `#FFF8F3` |
| `color.surface.white` | `bg-white` | `#FFFFFF` |
| `color.surface.input` | `bg-[#F5F5F5]` | `#F5F5F5` |

### 文字色

| Design Token | Tailwind v4 工具类 | Hex 值 |
|--------------|-------------------|--------|
| `color.ink.primary` | `text-[#3A3A4A]` | `#3A3A4A` |
| `color.ink.secondary` | `text-[#888888]` | `#888888` |
| `color.ink.placeholder` | `placeholder:text-[#BBBBBB]` | `#BBBBBB` |
| `color.ink.white` | `text-white` | `#FFFFFF` |

### 遮罩色

| Design Token | Tailwind v4 工具类 |
|--------------|-------------------|
| `color.scrim.modal` | `bg-black/45` |
| `color.scrim.sheet` | `bg-black/25` |

### 边框色

| Design Token | Tailwind v4 工具类 | Hex 值 |
|--------------|-------------------|--------|
| `color.border.subtle` | `border-black/8` | `rgba(0,0,0,0.08)` |
| `color.border.radio` | `border-[#CCCCCC]` | `#CCCCCC` |
| `color.border.radio.active` | `border-[#FFB7C5]` | `#FFB7C5` |
| `color.border.cancel-btn` | `border-[#E8E8E8]` | `#E8E8E8` |

---

## Gradient 映射

| Token | Tailwind v4 映射 |
|-------|----------------|
| `gradient.button.primary` | `bg-gradient-to-br from-[#FFB7C5] to-[#FF8FA3]` |
| `gradient.background.chat` | `bg-gradient-to-b from-[#FFD6E4] via-white to-[#E8E0FF]` |

---

## Spacing 映射

| Design Token | Tailwind v4 | px 值 |
|--------------|-------------|-------|
| `spacing.4` | `h-1` / `gap-1` | 4px |
| `spacing.8` | `p-2` / `gap-2` | 8px |
| `spacing.12` | `gap-3` | 12px |
| `spacing.16` | `p-4` / `gap-4` / `mt-4` | 16px |
| `spacing.20` | `px-5` | 20px |
| `spacing.24` | `p-6` | 24px |
| `spacing.32` | `p-8` | 32px |
| `spacing.36` | `w-9 h-9` | 36px |
| `spacing.44` | `h-11` / `min-h-11` | 44px |
| `spacing.48` | `h-12` | 48px |
| `spacing.64` | `gap-16` | 64px |

---

## Border Radius 映射

| Design Token | Tailwind v4 | px 值 |
|--------------|-------------|-------|
| `radius.toast` | `rounded-[22px]` | 22px |
| `radius.modal` | `rounded-[20px]` | 20px |
| `radius.sheet.top` | `rounded-t-[20px]` | 20px top-only |
| `radius.button.primary` | `rounded-[24px]` | 24px |
| `radius.button.secondary` | `rounded-[24px]` | 24px |
| `radius.avatar` | `rounded-full` | 50% |
| `radius.radio` | `rounded-full` | 50% |
| `radius.badge` | `rounded-full` | 50% |
| `radius.phone` | `rounded-[40px]` | 40px |

---

## Shadow 映射

| Design Token | Tailwind v4 映射 |
|--------------|----------------|
| `shadow.toast` | `shadow-[0_4px_16px_rgba(0,0,0,0.10)]` |
| `shadow.modal` | `shadow-[0_8px_32px_rgba(0,0,0,0.18)]` |
| `shadow.sheet` | `shadow-[0_-4px_20px_rgba(0,0,0,0.10)]` |
| `shadow.button` | `shadow-[0_2px_8px_rgba(255,143,163,0.35)]` |

---

## Typography 映射

### 字体族

| Design Token | Tailwind v4 映射 |
|--------------|----------------|
| `font.family.cn` | `font-['PingFang_SC',_'HarmonyOS_Sans_SC',_sans-serif]` |
| `font.family.en` | `font-['SF_Pro_Rounded',_sans-serif]` |

### 字号

| Design Token | Tailwind v4 | px 值 |
|--------------|-------------|-------|
| `text.modal.title` | `text-[20px] font-semibold` | 20px / 600 |
| `text.modal.body` | `text-[13px] leading-relaxed` | 13px / 400 |
| `text.sheet.title` | `text-[17px] font-semibold` | 17px / 600 |
| `text.sheet.option` | `text-base` | 16px / 400 |
| `text.button.primary` | `text-base font-semibold` | 16px / 600 |
| `text.button.secondary` | `text-base` | 16px / 400 |
| `text.toast` | `text-sm` | 14px / 400 |
| `text.nav.title` | `text-base font-semibold` | 16px / 600 |
| `text.status.time` | `text-[15px] font-semibold` | 15px / 600 |
| `text.badge` | `text-sm font-bold` | 14px / 700 |

---

## Animation 映射

### Tailwind v4 自定义动画（需在 CSS 层定义 @keyframes）

| Token | Tailwind v4 工具类 | 说明 |
|-------|-----------------|------|
| Toast 进入 | `animate-[toast-in_300ms_cubic-bezier(0.34,1.56,0.64,1)_both]` | 下滑+渐显 |
| Toast 退出 | `animate-[toast-out_200ms_ease-out_both]` | 上滑+渐隐 |
| Modal 进入 | `animate-[modal-in_250ms_cubic-bezier(0.34,1.56,0.64,1)_both]` | 弹性缩放+渐显 |
| Modal 退出 | `animate-[modal-out_200ms_ease-out_both]` | 缩小+渐隐 |
| Sheet 进入 | `animate-[sheet-in_350ms_cubic-bezier(0.32,0.72,0,1)_both]` | 底部滑入 |
| Sheet 退出 | `animate-[sheet-out_300ms_ease-out_both]` | 底部滑出 |
| Scrim 进入 | `animate-[fade-in_200ms_linear_both]` | 渐显 |
| Scrim 退出 | `animate-[fade-out_200ms_linear_both]` | 渐隐 |
| Radio 选中 | `animate-[radio-check_150ms_cubic-bezier(0.34,1.56,0.64,1)_both]` | 内圆弹出 |
| 按钮 Pressed | `active:scale-[0.98] active:brightness-90 transition-all duration-100` | 按压效果 |

### 参考 @keyframes 定义说明（仅 Token 级）

```
@keyframes toast-in:
  from: translateY(-100%) opacity(0)
  to:   translateY(0)    opacity(1)

@keyframes toast-out:
  from: translateY(0)    opacity(1)
  to:   translateY(-100%) opacity(0)

@keyframes modal-in:
  from: scale(0.85) opacity(0)
  to:   scale(1.0)  opacity(1)

@keyframes modal-out:
  from: scale(1.0)  opacity(1)
  to:   scale(0.85) opacity(0)

@keyframes sheet-in:
  from: translateY(100%)
  to:   translateY(0)

@keyframes sheet-out:
  from: translateY(0)
  to:   translateY(100%)

@keyframes radio-check:
  from: scale(0)
  to:   scale(1)
```

---

## Blur 映射

| Design Token | Tailwind v4 |
|--------------|-------------|
| `blur.glass` | `backdrop-blur-[12px]` |
| `blur.none` | `backdrop-blur-0` |

---

## z-index 映射

| 元素 | Tailwind v4 | 值 |
|------|-------------|-----|
| 聊天内容 | `z-0` | 0 |
| InputBar | `z-10` | 10 |
| Scrim | `z-[100]` | 100 |
| Modal / Sheet | `z-[200]` | 200 |
| Toast | `z-[300]` | 300 |
