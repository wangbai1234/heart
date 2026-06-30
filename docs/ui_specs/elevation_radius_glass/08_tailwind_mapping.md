# 08 Tailwind v4 映射规则 — Shadow / Radius / Glass Sample

> 本文件仅建立 Design Token → Tailwind v4 映射规则，不生成任何实现代码。
> Tailwind v4 使用 CSS Custom Properties（`@theme`）机制，与 v3 的 `tailwind.config.js` 不同。

---

## 0. Tailwind v4 主题机制说明

Tailwind v4 通过 `@theme` 指令在 CSS 文件中定义设计 Token，格式为：

```
@theme {
  --color-*: ...;
  --radius-*: ...;
  --shadow-*: ...;
  --blur-*: ...;
  --font-*: ...;
}
```

以下映射表格说明：左列为设计 Token 名称，右列为 Tailwind v4 CSS 变量名建议。

---

## 1. 颜色（Colors）

### 品牌色映射

| Design Token | Tailwind CSS 变量名 | 色值 | 使用场景 |
|-------------|-------------------|------|---------|
| `color.primary` | `--color-primary` | `#FFB7C5` | 品牌粉，标题圆点、♥ 图标 |
| `color.secondary` | `--color-secondary` | `#A7C7E7` | 天空蓝，插画/信息色 |
| `color.accent` | `--color-accent` | `#C8B6FF` | 薰衣草紫，备用强调色 |
| `color.surface` | `--color-surface` | `#FFF8F3` | 奶油白，页面底色 |
| `color.ink` | `--color-ink` | `#3A3A4A` | 炭黑，正文文字 |

### 文字色映射

| Design Token | Tailwind CSS 变量名 | 色值 |
|-------------|-------------------|------|
| `color.text.primary` | `--color-text-primary` | `#3A3A4A` |
| `color.text.secondary` | `--color-text-secondary` | `rgba(58,58,74,0.60)` |
| `color.text.brand` | `--color-text-brand` | `#FFB7C5` |

### 玻璃色映射

| Design Token | Tailwind CSS 变量名 | 色值 |
|-------------|-------------------|------|
| `color.glass.35` | `--color-glass-35` | `rgba(255,255,255,0.35)` |
| `color.glass.55` | `--color-glass-55` | `rgba(255,255,255,0.55)` |
| `color.glass.75` | `--color-glass-75` | `rgba(255,255,255,0.75)` |

### 背景色映射

| Design Token | Tailwind CSS 变量名 | 色值 |
|-------------|-------------------|------|
| `color.background.page` | `--color-bg-page` | `#FFF8F3` |
| `color.surface.card` | `--color-surface-card` | `rgba(255,255,255,0.95)` |
| `color.border.subtle` | `--color-border-subtle` | `rgba(0,0,0,0.04)` |

---

## 2. 间距（Spacing）

| Design Token | Tailwind CSS 变量名 | 值 | 对应 Tailwind 工具类前缀 |
|-------------|-------------------|----|----------------------|
| `spacing.1` | `--spacing-1` | `4px` | `p-1`, `m-1`, `gap-1` |
| `spacing.2` | `--spacing-2` | `8px` | `p-2`, `m-2`, `gap-2` |
| `spacing.3` | `--spacing-3` | `12px` | `p-3`, `m-3`, `gap-3` |
| `spacing.4` | `--spacing-4` | `16px` | `p-4`, `m-4`, `gap-4` |
| `spacing.6` | `--spacing-6` | `24px` | `p-6`, `m-6`, `gap-6` |
| `spacing.8` | `--spacing-8` | `32px` | `p-8`, `m-8`, `gap-8` |
| `spacing.10` | `--spacing-10` | `40px` | `p-10`, `m-10`, `gap-10` |
| `spacing.12` | `--spacing-12` | `48px` | `p-12`, `m-12`, `gap-12` |

> 注：Tailwind v4 默认 spacing 单位为 0.25rem（4px），上述映射与默认体系对齐，无需自定义。

---

## 3. 圆角半径（Border Radius）

| Design Token | Tailwind CSS 变量名 | 值 | 对应 Tailwind 工具类 |
|-------------|-------------------|----|-------------------|
| `radius.xs` | `--radius-xs` | `4px` | `rounded-xs` |
| `radius.sm` | `--radius-sm` | `8px` | `rounded-sm` |
| `radius.md` | `--radius-md` | `16px` | `rounded-md` |
| `radius.lg` | `--radius-lg` | `24px` | `rounded-lg` |
| `radius.xl` | `--radius-xl` | `32px` | `rounded-xl` |
| `radius.full` | `--radius-full` | `9999px` | `rounded-full` |

> 注：Tailwind v4 的 `rounded-md` 默认值为 `6px`，需要通过 `@theme` 覆盖为 `16px` 以匹配本设计系统。

---

## 4. 模糊（Blur）

| Design Token | Tailwind CSS 变量名 | 值 | 对应 Tailwind 工具类 |
|-------------|-------------------|----|-------------------|
| `blur.glass` | `--blur-glass` | `16px` | `backdrop-blur-glass` 或 `blur-glass` |
| `blur.glow` | `--blur-glow` | `约60px`（估算值） | `blur-glow` |

> 注：`backdrop-filter: blur()` 在 Tailwind v4 通过 `backdrop-blur-{size}` 工具类使用，需自定义 Token。

---

## 5. 阴影（Shadow）

| Design Token | Tailwind CSS 变量名 | 值 | 对应 Tailwind 工具类 |
|-------------|-------------------|----|-------------------|
| `shadow.none` | `--shadow-none` | `none` | `shadow-none` |
| `shadow.soft` | `--shadow-soft` | `0 2px 6px rgba(0,0,0,0.04)` | `shadow-soft` |
| `shadow.card` | `--shadow-card` | `0 4px 12px rgba(0,0,0,0.06)` | `shadow-card` |
| `shadow.sheet` | `--shadow-sheet` | `0 8px 24px rgba(0,0,0,0.08)` | `shadow-sheet` |
| `shadow.modal` | `--shadow-modal` | `0 12px 40px rgba(0,0,0,0.10)` | `shadow-modal` |

> 注：Tailwind v4 支持通过 `--shadow-{name}` 自定义，所有阴影值需在 `@theme` 中显式定义。

---

## 6. 字体（Font）

### 字体族

| Design Token | Tailwind CSS 变量名 | 值 |
|-------------|-------------------|----|
| `font.family.chinese` | `--font-chinese` | `"PingFang SC", "HarmonyOS Sans SC", sans-serif` |
| `font.family.latin` | `--font-latin` | `"SF Pro Rounded", sans-serif` |

对应 Tailwind 工具类：`font-chinese`, `font-latin`

### 字号（与 Tailwind 默认 rem 体系对齐）

| Design Token | 值 | 对应 Tailwind 工具类（参考） |
|-------------|----|-----------------------------|
| `font.size.pageTitle` | 约 `28–32px` | `text-3xl`（30px）/ 自定义 `text-page-title` |
| `font.size.sectionTitle` | 约 `18–20px` | `text-lg`（18px）/ `text-xl`（20px） |
| `font.size.label.primary` | 约 `14px` | `text-sm`（14px） |
| `font.size.label.secondary` | 约 `12px` | `text-xs`（12px） |
| `font.size.footer` | 约 `13–14px` | `text-sm` |

### 字重

| Design Token | 值 | 对应 Tailwind 工具类 |
|-------------|----|--------------------|
| `font.weight.semibold` | `600` | `font-semibold` |
| `font.weight.medium` | `500` | `font-medium` |
| `font.weight.regular` | `400` | `font-normal` |

---

## 7. 动画（Animation）

> N/A for this asset type — 本资产为静态参考图，无动效 Token 定义。
>
> 动画 Token 将在交互规范资产中定义，映射建议：
>
> | Token | Tailwind CSS 变量名 | 建议值 |
> |-------|-------------------|--------|
> | `motion.duration.fast` | `--duration-fast` | `150ms` |
> | `motion.duration.normal` | `--duration-normal` | `300ms` |
> | `motion.duration.slow` | `--duration-slow` | `500ms` |
> | `motion.easing.out` | `--ease-out` | `cubic-bezier(0,0,0.2,1)` |
> | `motion.easing.in` | `--ease-in` | `cubic-bezier(0.4,0,1,1)` |

---

## 8. 映射规则汇总表

| Token 类别 | CSS 变量前缀 | Tailwind 工具类前缀 |
|-----------|------------|-------------------|
| 颜色 | `--color-` | `bg-`、`text-`、`border-` |
| 间距 | `--spacing-` | `p-`、`m-`、`gap-` |
| 圆角 | `--radius-` | `rounded-` |
| 模糊 | `--blur-` | `blur-`、`backdrop-blur-` |
| 阴影 | `--shadow-` | `shadow-` |
| 字体族 | `--font-` | `font-` |
| 字号 | `--text-` | `text-` |
| 动画时长 | `--duration-` | `duration-` |
| 动画缓动 | `--ease-` | `ease-` |

---

## 9. 建立 Design System 的推荐步骤

1. 在项目根 CSS 文件（如 `app/globals.css`）添加 `@theme {}` 块，将上述所有 Token 注册为 CSS 变量
2. Tailwind v4 自动将 `--color-primary` 映射为 `bg-primary`、`text-primary`、`border-primary`
3. Tailwind v4 自动将 `--radius-md` 映射为 `rounded-md`（注意覆盖默认值）
4. 自定义阴影（`--shadow-*`）和模糊（`--blur-*`）需要显式在 `@theme` 中声明对应工具类规则
5. 所有 Token 名称使用 kebab-case，与 CSS 变量命名规范保持一致
6. 严禁在组件中直接使用硬编码色值，所有颜色必须引用 Token
