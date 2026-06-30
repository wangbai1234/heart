# 08 Tailwind v4 映射规则 — Typography Specimen（字样规范）

> 本文档仅建立 Design Token 到 Tailwind v4 CSS 变量的**映射规则**。
> 不包含任何 JSX / HTML / CSS 代码片段。
> Tailwind v4 使用 CSS `@theme` 定义 Design Token，以下为规则说明。

---

## 一、字体家族映射（Font Family）

| Design Token | Tailwind v4 自定义名称 | CSS Font Stack |
|--------------|----------------------|----------------|
| `font.family.zh` | `font-zh` | `"PingFang SC", "HarmonyOS Sans SC", "Noto Sans SC", sans-serif` |
| `font.family.latin` | `font-latin` | `"SF Pro Rounded", "Inter", "Nunito", sans-serif` |
| `font.family.tabular` | `font-tabular` | `"SF Pro Rounded", "Inter", monospace` |

**映射规则说明：**
- `font-zh` 适用于所有中文文本节点（或混合中英文的容器）
- `font-latin` 适用于纯英文按钮标签、品牌字
- `font-tabular` 适用于所有时间戳、计数器、数字指标
- 中英混排时，Tailwind class 设置为 `font-zh`；中文字符命中 PingFang SC，拉丁字符因字体 fallback 命中 SF Pro Rounded（浏览器自动处理）

---

## 二、字号映射（Font Size）

Tailwind v4 以 `--font-size-*` CSS 变量驱动，以下为 6 级阶梯映射：

| Design Token 级别 | Tailwind class 名称 | Font Size | Line Height |
|-------------------|---------------------|-----------|-------------|
| `type.display` | `text-display` | `40px` (2.5rem) | `48px` (3rem) |
| `type.title` | `text-title` | `28px` (1.75rem) | `36px` (2.25rem) |
| `type.headline` | `text-headline` | `22px` (1.375rem) | `30px` (1.875rem) |
| `type.body` | `text-body` | `16px` (1rem) | `24px` (1.5rem) |
| `type.caption` | `text-caption` | `13px` (0.8125rem) | `18px` (1.125rem) |
| `type.tabular` | `text-tabular` | `14px` (0.875rem) | `20px` (1.25rem)（估算值） |

**映射规则说明：**
- 字号和行高成对定义在同一 `@theme` 变量中（Tailwind v4 支持 `[font-size, line-height]` 元组）
- `text-display` 仅用于欢迎语、情感大标题等少数高权重场景
- `text-body` 为聊天气泡正文的默认级别，出现频率最高，应作为基础字号

---

## 三、字重映射（Font Weight）

| Design Token 字重 | Tailwind class | CSS 值 | 适用级别 |
|-------------------|---------------|--------|----------|
| SemiBold | `font-semibold` | `600` | Display |
| Medium | `font-medium` | `500` | Title、Headline |
| Regular | `font-normal` | `400` | Body、Caption、Tabular |

---

## 四、颜色映射（Colors）

### 主调色板

| Design Token | Tailwind class 前缀 | 值 | 用途 |
|--------------|--------------------|----|------|
| `color.primary` | `primary` | `#FFB7C5` | 文字、图标、装饰 |
| `color.secondary` | `secondary` | `#A7C7E7` | 用户气泡背景 |
| `color.accent` | `accent` | `#C8B6FF` | 强调色（保留） |
| `color.surface` | `surface` | `#FFF8F3` | 页面背景、卡片背景 |
| `color.ink` | `ink` | `#3A3A4A` | 主要正文 |

### 文字颜色

| Design Token | Tailwind class | 值 |
|--------------|---------------|----|
| `color.text.primary` | `text-ink` | `#3A3A4A` |
| `color.text.secondary` | `text-ink-secondary` | `#8A8A98` |
| `color.text.label` | `text-primary` | `#FFB7C5` |
| `color.text.annotation` | `text-muted` | `#8A8A98` |

### 深色模式颜色（Dark Mode）

Tailwind v4 原生支持 `.dark` class 或 `prefers-color-scheme` 媒体查询：

| 对应 token | Dark 值（估算值） | 说明 |
|------------|-----------------|------|
| `dark:bg-chat-surface` | `#2A2A38` | 深色聊天背景 |
| `dark:bg-bubble-ai` | `#3A3A50` | 深色 AI 气泡 |
| `dark:bg-bubble-user` | `#4A4A62` | 深色用户气泡 |
| `dark:text-ink` | `#F0F0F8` | 深色正文 |
| `dark:text-muted` | `#9090A0` | 深色辅助文字 |

---

## 五、间距映射（Spacing）

Tailwind v4 默认间距比例（4px基准）已覆盖大部分需求，以下为自定义扩展项：

| Design Token | Tailwind 名称 | 值 |
|--------------|---------------|----|
| `spacing.xs` | `spacing-xs` 或 `p-1` | `4px` |
| `spacing.sm` | `spacing-sm` 或 `p-2` | `8px` |
| `spacing.md` | `spacing-md` 或 `p-3` | `12px` |
| `spacing.lg` | `spacing-lg` 或 `p-4` | `16px` |
| `spacing.xl` | `spacing-xl` 或 `p-6` | `24px` |
| `spacing.2xl` | `spacing-2xl` 或 `p-8` | `32px` |
| `spacing.3xl` | `spacing-3xl` 或 `p-10` | `40px` |
| `spacing.4xl` | `spacing-4xl` 或 `p-12` | `48px` |
| `spacing.5xl` | `spacing-5xl` 或 `p-16` | `64px` |

---

## 六、圆角映射（Border Radius）

| Design Token | Tailwind class | 值（估算值） |
|--------------|---------------|------------|
| `radius.sm` | `rounded-sm`（自定义） | `8px` |
| `radius.md` | `rounded-md`（自定义） | `12px` |
| `radius.lg` | `rounded-lg`（自定义） | `16px` |
| `radius.xl` | `rounded-xl`（自定义） | `20px` |
| `radius.full` | `rounded-full` | `999px` |

**说明：** Tailwind v4 中，`rounded-sm/md/lg/xl` 的默认值与上述不同，需在 `@theme` 中覆盖以匹配设计系统。

---

## 七、阴影映射（Shadow）

| Design Token | Tailwind class | 参数 |
|--------------|---------------|------|
| `shadow.card.light` | `shadow-card-light` | `0 4px 16px rgba(58,58,74,0.06)` |
| `shadow.card.dark` | `shadow-card-dark` | `0 8px 24px rgba(0,0,0,0.20)` |
| `shadow.bubble` | `shadow-bubble` | `0 2px 8px rgba(255,183,197,0.08)` |

---

## 八、模糊映射（Blur / Backdrop Filter）

| Design Token | Tailwind class | 值 |
|--------------|---------------|----|
| `blur.glass.sm` | `backdrop-blur-sm`（自定义） | `blur(8px)` |
| `blur.glass.md` | `backdrop-blur-md`（自定义） | `blur(16px)` |

---

## 九、数字等宽映射（Tabular Nums）

| 需求 | Tailwind v4 映射方式 |
|------|---------------------|
| 等宽数字（时间戳等） | 使用 Tailwind v4 `tabular-nums` utility class（原生支持） |

---

## 十、动画映射（Animation）

| Design Token | Tailwind class | 值 |
|--------------|---------------|----|
| `motion.duration.fast` | `duration-150` | `150ms` |
| `motion.duration.normal` | `duration-250` | `250ms`（需自定义） |
| `motion.duration.slow` | `duration-400` | `400ms`（需自定义） |
| `motion.easing.ease-out` | `ease-out` | `cubic-bezier(0,0,0.2,1)` |

---

## 建立 Design System 的步骤建议

1. **在 `@theme` 块中集中定义所有 CSS 变量**（颜色、字号、圆角、阴影）
2. **中英文字体分别绑定** `--font-zh` 和 `--font-latin`，不依赖 Tailwind 默认 `sans`
3. **6 级字号作为语义 utility class** 而非 raw 数字 class（避免 `text-[40px]` 散落各处）
4. **深色模式通过 `.dark` class 切换**，在 `@theme` 中同时定义 `light` 和 `dark` 两套变量
5. **间距使用语义名称**（如 `gap-bubble-inner`）而非原始数字，方便统一调整
