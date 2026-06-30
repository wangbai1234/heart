# 08 Tailwind Mapping — 设置页 Settings

以下为 Tailwind v4 `@theme` 映射规则，将 Design Token 与 Tailwind 工具类名称对应。
**注意：本文件不生成任何代码，仅建立映射规则。**

---

## Colors（颜色映射）

### 品牌色
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-primary` | `#FFB7C5` | `bg-brand-primary` / `text-brand-primary` / `border-brand-primary` |
| `color-primary-deep` | `#FF85A1` | `bg-brand-primary-deep` / `text-brand-primary-deep` |
| `color-secondary` | `#A7C7E7` | `bg-brand-secondary` / `text-brand-secondary` |
| `color-accent` | `#C8B6FF` | `bg-brand-accent` / `text-brand-accent` |

### 背景色
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-bg-page-top` | `#FDEEF3` | `bg-page-top` |
| `color-bg-page-mid` | `#F5E8F5` | `bg-page-mid` |
| `color-bg-page-bottom` | `#E8D5F0` | `bg-page-bottom` |
| `color-surface` | `#FFF8F3` | `bg-surface` |

### 卡片 / Glass
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-card-bg` | `rgba(255,255,255,0.88)` | `bg-card` |
| `color-card-profile-bg` | `rgba(255,255,255,0.90)` | `bg-card-profile` |
| `color-glass` | `rgba(255,255,255,0.55)` | `bg-glass` |
| `color-divider` | `rgba(229,224,234,0.8)` | `border-divider` / `divide-divider` |
| `color-border` | `rgba(255,183,197,0.25)` | `border-brand-soft` |

### 文字
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-text-primary` | `#3A3A4A` | `text-ink` |
| `color-text-secondary` | `#8A8A9A` | `text-ink-secondary` |
| `color-text-placeholder` | `#BCBCC8` | `text-placeholder` |
| `color-text-danger` | `#FF85A1` | `text-danger` |
| `color-text-member-badge` | `#FF85A1` | `text-member` |

### 状态色
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-success` | `#7ECBA5` | `text-success` / `bg-success` |
| `color-warning` | `#FFD580` | `text-warning` / `bg-warning` |
| `color-danger` | `#FF85A1` | `text-danger` / `bg-danger` |
| `color-info` | `#A7C7E7` | `text-info` / `bg-info` |

### 控件色
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-toggle-on-track` | 渐变 #FFB7C5→#FF85A1 | `bg-toggle-on`（需 gradient plugin） |
| `color-toggle-thumb` | `#FFFFFF` | `bg-white` |
| `color-toggle-off-track` | `rgba(200,200,210,0.5)` | `bg-toggle-off` |
| `color-slider-track` | `rgba(200,200,210,0.6)` | `bg-slider-track` |
| `color-slider-thumb` | `#FFB7C5` | `bg-slider-thumb` |
| `color-segment-selected-bg` | `#FFFFFF` | `bg-white` |
| `color-segment-container-bg` | `rgba(240,235,245,0.8)` | `bg-segment-container` |
| `color-chevron` | `#C0C0CC` | `text-chevron` |

### Overlay
| Design Token | Hex / RGBA | Tailwind 工具类名称 |
|-------------|-----------|-------------------|
| `color-overlay` | `rgba(30,20,40,0.4)` | `bg-overlay` |

---

## Spacing（间距映射）

| Design Token | 数值 | Tailwind 工具类名称 |
|-------------|------|-------------------|
| `space-1` | 4 pt | `p-1` / `m-1` / `gap-1` |
| `space-2` | 8 pt | `p-2` / `m-2` / `gap-2` |
| `space-3` | 12 pt | `p-3` / `m-3` / `gap-3` |
| `space-4` | 16 pt | `p-4` / `m-4` / `gap-4` |
| `space-5` | 20 pt | `p-5` / `m-5` / `gap-5` |
| `space-6` | 24 pt | `p-6` / `m-6` / `gap-6` |
| `space-8` | 32 pt | `p-8` / `m-8` / `gap-8` |
| `space-10` | 40 pt | `p-10` / `m-10` / `gap-10` |
| `space-12` | 48 pt | `p-12` / `m-12` / `gap-12` |
| `space-16` | 64 pt | `p-16` / `m-16` / `gap-16` |

**页面专用 spacing：**
| 用途 | 数值 | Tailwind 类 |
|------|------|------------|
| 页面水平 margin | 16 pt | `px-4` |
| 卡片内部水平 padding | 16 pt | `px-4` |
| Row 高度 | 54 pt | 自定义：`h-row`（需注册，约 `h-[54px]`） |
| 卡片间 gap | 8–12 pt | `gap-2` 至 `gap-3` |
| Section Label 上间距 | 16 pt | `mt-4` |
| Section Label 下间距 | 6–8 pt | `mb-1.5` 至 `mb-2` |

---

## Radius（圆角映射）

| Design Token | 数值 | Tailwind 工具类名称 |
|-------------|------|-------------------|
| `radius-xs` | 4 pt | `rounded-sm` |
| `radius-sm` | 8 pt | `rounded-md` |
| `radius-md` | 12 pt | `rounded-xl`（Tailwind v4 自定义） |
| `radius-lg` | 16 pt | `rounded-2xl` |
| `radius-xl` | 20 pt | `rounded-[20px]`（需自定义） |
| `radius-2xl` | 24 pt | `rounded-3xl` |
| `radius-full` | 9999 pt | `rounded-full` |
| `radius-badge` | 11 pt | `rounded-[11px]` |

**推荐自定义映射（@theme）：**
- `--radius-card: 20px` → `rounded-card`
- `--radius-badge: 11px` → `rounded-badge`
- `--radius-segment: 10px` → `rounded-segment`

---

## Blur（模糊映射）

| Design Token | 数值 | Tailwind 工具类名称 |
|-------------|------|-------------------|
| `blur-glass-light` | 12 pt | `backdrop-blur-sm`（Tailwind ~8px，需调整） |
| `blur-glass-heavy` | 20 pt | `backdrop-blur-md`（Tailwind ~12px，需自定义）|
| `blur-glow` | 40 pt | `blur-[40px]`（glow 装饰，非 backdrop） |

**推荐自定义映射：**
- `--blur-glass: 12px` → `backdrop-blur-glass`
- `--blur-heavy: 20px` → `backdrop-blur-heavy`

---

## Shadow（阴影映射）

| Design Token | 参数 | Tailwind 工具类名称 |
|-------------|------|-------------------|
| `shadow-card` | rgba(180,160,200,0.12), blur 16, offset(0,4) | `shadow-card`（自定义） |
| `shadow-profile-card` | rgba(180,160,200,0.15), blur 20, offset(0,6) | `shadow-profile`（自定义） |
| `shadow-segment-selected` | rgba(0,0,0,0.08), blur 4, offset(0,1) | `shadow-sm` 或 `shadow-segment`（自定义） |
| `shadow-toggle` | rgba(0,0,0,0.10), blur 6, offset(0,2) | `shadow-toggle`（自定义） |

**推荐 @theme 自定义 shadow：**
```
--shadow-card: 0 4px 16px rgba(180,160,200,0.12)
--shadow-profile: 0 6px 20px rgba(180,160,200,0.15)
--shadow-segment: 0 1px 4px rgba(0,0,0,0.08)
--shadow-toggle: 0 2px 6px rgba(0,0,0,0.10)
```

---

## Font（字体映射）

### font-family
| 类型 | 字体栈 | Tailwind 工具类 |
|------|--------|----------------|
| 中文主字体 | `"PingFang SC", "HarmonyOS Sans SC", sans-serif` | `font-cn` |
| 英文/数字 | `"SF Pro Rounded", "SF Pro Display", system-ui` | `font-latin` |
| 默认 | `font-cn`（中文优先） | `font-sans`（覆盖默认） |

### font-size
| 层级 | 数值 | Tailwind 工具类 |
|------|------|----------------|
| 导航栏标题（T2） | 18 pt | `text-lg` 或 `text-[18px]` |
| 用户名（T3） | 17 pt | `text-[17px]` |
| 设置行 Label（T4） | 15–16 pt | `text-base`（16px）/ `text-[15px]` |
| 副文字（T5） | 13 pt | `text-sm`（14px，接近）/ `text-[13px]` |
| Section Label（T6） | 12 pt | `text-xs` |
| Badge（T7） | 12 pt | `text-xs` |
| Segment（T8） | 13 pt | `text-[13px]` |

### font-weight
| 值 | Tailwind 工具类 |
|----|----------------|
| Regular (400) | `font-normal` |
| Medium (500) | `font-medium` |
| Semibold (600) | `font-semibold` |
| Bold (700) | `font-bold` |

---

## Animation（动效映射）

| Design Token | 值 | Tailwind 工具类 / 说明 |
|-------------|-----|----------------------|
| `duration-fast` | 150 ms | `duration-150` |
| `duration-medium` | 250 ms | `duration-[250ms]` |
| `duration-slow` | 400 ms | `duration-[400ms]` |
| `easing-standard` | cubic-bezier(0.4,0,0.2,1) | `ease-[cubic-bezier(0.4,0,0.2,1)]` |
| `easing-decelerate` | cubic-bezier(0.0,0.0,0.2,1) | `ease-out`（近似） |
| `easing-accelerate` | cubic-bezier(0.4,0.0,1,1) | `ease-in`（近似） |

**推荐自定义 @theme keyframes：**
- `animate-toggle-on`：Toggle 开启动效（thumb slide right + track fade pink）
- `animate-toggle-off`：Toggle 关闭动效（thumb slide left + track fade gray）
- `animate-card-in`：卡片从 y+20 fadeIn（入场）
- `animate-segment-slide`：Segment Picker 选中态平滑滑动

---

## 如何用这套映射建立 Design System

### 步骤说明（不生成代码）

1. **注册 @theme 变量层**
   - 在 Tailwind v4 的 CSS 入口文件中使用 `@theme` 块注册所有自定义 CSS 变量
   - 包括：colors、spacing、radius、blur、shadow、font、animation
   - 变量命名遵循上述 Token 名称（例如 `--color-brand-primary: #FFB7C5`）

2. **建立 Token 到 Class 的单向映射**
   - 每个 Design Token 仅映射到一个 Tailwind 工具类名称
   - 避免在组件中硬编码颜色值，始终使用 Token 工具类

3. **组件级封装规则**
   - `GroupCard` = `bg-card + rounded-card + shadow-card + backdrop-blur-glass`
   - `SectionLabel` = `text-xs + text-ink-secondary + font-normal`
   - `SettingRow` = `flex items-center px-4 h-row`
   - `MemberBadge` = `bg-brand-primary/20 text-member text-xs rounded-badge px-2.5 py-1`

4. **主题切换机制**
   - 浅色/深色/自动主题通过 CSS 变量覆盖实现
   - 暗色模式在 `@theme dark` 块中重定义颜色 Token
   - Tailwind v4 的 `dark:` 前缀自动应用对应 Token

5. **组件库目录建议**
   - `tokens/` — 存放所有 Design Token 定义
   - `components/settings/` — 存放设置页相关组件
   - `primitives/` — 存放 GroupCard、SettingRow 等基础原件
   - 每个组件文件只引用 Token 工具类，不使用 arbitrary values

6. **验证方式**
   - 对比 PNG 设计稿，检查每个工具类是否正确映射到视觉效果
   - 使用 Storybook 或类似工具展示各组件状态
   - 建立视觉回归测试（截图对比）
