# 08 Tailwind v4 映射规则 — Style Tile（视觉总谱）

> 本文件仅建立 Design Token → Tailwind v4 的映射规则，不生成任何代码。
> 目标：工程师根据此规则在 `tailwind.config.ts`（或 v4 的 `@theme` 块）中建立设计系统。

---

## 前置说明

Tailwind CSS v4 使用 CSS 原生变量 + `@theme` 块定义 Design System，
映射路径为：**PNG Token → CSS Custom Property → Tailwind 工具类**。

---

## 1. Colors 颜色映射

### 品牌色

| Tailwind 工具类语义 | CSS Variable 名称 | 值 | 来源 |
|--------------------|--------------------|-----|------|
| `bg-primary` / `text-primary` | `--color-primary` | `#FFB7C5` | 调色板 swt-1 |
| `bg-secondary` / `text-secondary` | `--color-secondary` | `#A7C7E7` | 调色板 swt-2 |
| `bg-accent` / `text-accent` | `--color-accent` | `#C8B6FF` | 调色板 swt-3 |
| `bg-surface` | `--color-surface` | `#FFF8F3` | 调色板 swt-4 |
| `bg-ink` / `text-ink` | `--color-ink` | `#3A3A4A` | 调色板 swt-5 |
| `bg-glass` | `--color-glass` | `rgba(255,255,255,0.55)` | 调色板 swt-6 |

### 扩展色阶

| 语义 | CSS Variable | 值（估算值） |
|------|-------------|-------------|
| `text-ink-secondary` | `--color-ink-secondary` | `#7A7A8A` |
| `text-ink-placeholder` | `--color-ink-placeholder` | `#B0B0C0` |
| `bg-surface-card` | `--color-surface-card` | `rgba(255,255,255,0.80)` |
| `bg-bubble-ai` | `--color-bubble-ai` | `rgba(255,255,255,0.85)` |
| `bg-bubble-user` | `--color-bubble-user` | `rgba(167,199,231,0.80)` |
| `text-link` | `--color-link` | `#C8B6FF` |

### 语义色（占位）

| 语义 | CSS Variable | 推断值 |
|------|-------------|-------|
| `text-error` / `bg-error` | `--color-error` | `#EB5757` |
| `text-success` | `--color-success` | `#6FCF97` |
| `text-warning` | `--color-warning` | `#F2C94C` |

---

## 2. Spacing 间距映射

Tailwind v4 默认间距 scale（1 unit = 4px）可直接复用，补充自定义值：

| Tailwind 工具类 | 值 | 用途 |
|----------------|-----|------|
| `p-1` (4px) | `--spacing-1: 4px` | 标注内边距 |
| `p-2` (8px) | `--spacing-2: 8px` | 椭圆间距、气泡内边距 |
| `p-3` (12px) | `--spacing-3: 12px` | 按钮间距 |
| `p-4` (16px) | `--spacing-4: 16px` | 网格间距 |
| `p-5` (20px) | `--spacing-5: 20px` | 卡片内边距 |
| `p-6` (24px) | `--spacing-6: 24px` | 画布外边距 |
| `p-8` (32px) | `--spacing-8: 32px` | Logo 左边距 |
| `p-10` (40px) | `--spacing-10: 40px` | Logo 顶部距离 |
| `p-16` (64px) | `--spacing-16: 64px` | 区块大间距 |

---

## 3. Border Radius 圆角映射

| Tailwind 工具类 | CSS Variable | 值（估算值） | 用途 |
|----------------|-------------|-------------|------|
| `rounded-none` | — | `0px` | 无圆角 |
| `rounded-xs` | `--radius-xs` | `4px` | 气泡尖角、徽章 |
| `rounded-sm` | `--radius-sm` | `8px` | 等级徽章 |
| `rounded-md` | `--radius-md` | `12px` | 次要按钮、输入框 |
| `rounded-lg` | `--radius-lg` | `16px` | 气泡、卡片内层 |
| `rounded-xl` | `--radius-xl` | `20px` | 主卡片容器 |
| `rounded-2xl` | `--radius-2xl` | `24px` | Primary 按钮 |
| `rounded-full` | — | `9999px` | 头像、颜色椭圆 |

---

## 4. Blur 模糊映射

| Tailwind 工具类 | CSS Variable | 值（估算值） | 用途 |
|----------------|-------------|-------------|------|
| `backdrop-blur-glass` | `--blur-glass` | `12px` | 卡片、气泡毛玻璃 |
| `blur-glow` | `--blur-glow` | `20px` | 按钮 / 头像光晕（box-shadow blur） |

---

## 5. Shadow 阴影映射

| 工具类语义 | CSS Variable | 值（估算值） | 用途 |
|-----------|-------------|-------------|------|
| `shadow-card` | `--shadow-card` | `0 4px 16px rgba(0,0,0,0.06)` | 主卡片 |
| `shadow-btn-primary` | `--shadow-btn-primary` | `0 4px 12px rgba(255,183,197,0.45)` | Primary 按钮 |
| `shadow-btn-secondary` | `--shadow-btn-secondary` | `0 2px 8px rgba(0,0,0,0.05)` | Secondary 按钮 |
| `shadow-bubble` | `--shadow-bubble` | `0 2px 8px rgba(0,0,0,0.04)` | 气泡 |
| `shadow-avatar` | `--shadow-avatar` | `0 4px 12px rgba(255,183,197,0.25)` | 头像光晕 |

---

## 6. Typography 字体映射

### 字体族

| 工具类 | CSS Variable | 值 |
|--------|-------------|-----|
| `font-chinese` | `--font-family-chinese` | `"PingFang SC", "HarmonyOS Sans SC", sans-serif` |
| `font-latin` | `--font-family-latin` | `"SF Pro Rounded", "SF Pro Display", system-ui` |

### 字号（扩展 Tailwind 默认 scale）

| 工具类 | CSS Variable | 值（估算值） | 用途 |
|--------|-------------|-------------|------|
| `text-display` | `--text-display` | `40px / 1.2` | 大标题中文 |
| `text-title-lg` | `--text-title-lg` | `20px / 1.4` | 英文大标题 |
| `text-title-md` | `--text-title-md` | `18px / 1.4` | 角色名 |
| `text-body` | `--text-body` | `16px / 1.5` | 正文 |
| `text-body-sm` | `--text-body-sm` | `14px / 1.5` | 次级说明 |
| `text-caption` | `--text-caption` | `12px / 1.4` | 时间戳、标注 |
| `text-label` | `--text-label` | `11px / 1.3` | 图标标签 |
| `text-hex` | `--text-hex` | `10px / 1.2` | Hex 颜色标注 |

### 字重

| 工具类 | 值 | 用途 |
|--------|-----|------|
| `font-normal` (400) | Regular | 正文、说明 |
| `font-semibold` (600) | SemiBold | 角色名、英文标题 |
| `font-bold` (700) | Bold | 大标题、数字统计 |

---

## 7. Gradient 渐变映射

> Tailwind v4 支持通过 CSS 变量定义渐变，映射规则如下：

| 工具类语义 | CSS Variable | 值（估算值） |
|-----------|-------------|-------------|
| `bg-gradient-page` | `--gradient-background-top` | `linear-gradient(180deg, #FFD6DD 0%, #FFF8F3 40%)` |
| `bg-gradient-btn-primary` | `--gradient-button-primary` | `linear-gradient(135deg, #FFB7C5 0%, #FFAAB8 100%)` |

---

## 8. Animation 动效映射

| 工具类语义 | CSS Variable | 值（估算值） | 用途 |
|-----------|-------------|-------------|------|
| `duration-fast` | `--duration-fast` | `150ms` | 按钮 pressed |
| `duration-normal` | `--duration-normal` | `250ms` | 气泡入场 |
| `duration-slow` | `--duration-slow` | `400ms` | 页面过渡 |
| `duration-extra-slow` | `--duration-extra-slow` | `600ms` | 插画淡入 |
| `ease-standard` | `--ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | 默认缓动 |
| `ease-decelerate` | `--ease-decelerate` | `cubic-bezier(0.0, 0, 0.2, 1)` | 元素进入 |
| `ease-accelerate` | `--ease-accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | 元素离开 |

---

## 9. 建立 Design System 的推荐步骤

1. **定义 CSS 变量层**：在 `global.css` 的 `:root` 中声明所有 `--color-*`、`--radius-*`、`--shadow-*` 变量，以此为 Single Source of Truth。

2. **配置 Tailwind v4 `@theme` 块**：将 CSS 变量引用注册为 Tailwind 工具类（colors、spacing、fontSize、borderRadius、boxShadow、animation）。

3. **建立 `tokens.ts` 类型定义文件**：导出 TypeScript 常量，供 React Native / RN Stylesheet 直接使用（iOS / Android 侧不走 Tailwind）。

4. **Icon 系统**：SVG Icon 集中管理，支持 `color` prop 接收 Token 变量值。

5. **暗色模式（预留）**：在 `@theme dark` 块中覆盖关键颜色变量，当前版本不需要，但命名规范要支持。

6. **Storybook 验证**：每个组件建立 Story，直接渲染 Token 效果，确保视觉与 Style Tile 一致。
