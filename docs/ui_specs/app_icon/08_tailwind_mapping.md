# 08 Tailwind v4 映射规则 — App Icon（多色版 + 单色版）

## 说明

本文件建立 App Icon 设计 Token 与 Tailwind CSS v4 的映射规则。

**重要说明**：
- 本文件仅建立映射规则，不生成任何 CSS/HTML/React 代码
- App Icon 本身作为 PNG/SVG 资源交付，无法直接用 Tailwind 类渲染
- 映射规则的目的是：将图标的设计 token 纳入全局 Design System，供 App 其他 UI 组件复用
- Tailwind v4 使用 CSS 自定义属性（`@theme` 指令）而非 `tailwind.config.js`

---

## 颜色 Token 映射

### 品牌色（与图标渐变保持一致）

| Design Token | CSS 变量名 | Tailwind 工具类 | 值 |
|-------------|-----------|----------------|-----|
| `color.icon.full.gradient.start` | `--color-cherry-pink` | `bg-cherry-pink` / `text-cherry-pink` | `#FFB7C5` |
| `color.icon.full.gradient.mid` | `--color-lavender` | `bg-lavender` / `text-lavender` | `#C8B6FF` |
| `color.icon.full.gradient.end` | `--color-sky-blue` | `bg-sky-blue` / `text-sky-blue` | `#A7C7E7` |
| `color.canvas.background` | `--color-canvas-warm` | `bg-canvas-warm` | `#FAE8D8` |

### 单色版色系

| Design Token | CSS 变量名 | Tailwind 工具类 | 值（估算值）|
|-------------|-----------|----------------|------------|
| `color.icon.mono.base` | `--color-warm-gray-purple` | `bg-warm-gray-purple` | `#D6CDD4` |
| `color.icon.mono.highlight` | `--color-warm-gray-light` | `bg-warm-gray-light` | `#F0EBF0` |
| `color.icon.mono.shadow` | `--color-warm-gray-deep` | `bg-warm-gray-deep` | `#B8AEB8` |

### 玻璃效果色

| Design Token | CSS 变量名 | 值（估算值）|
|-------------|-----------|------------|
| `color.icon.full.edge.highlight` | `--color-glass-highlight` | `rgba(255,255,255,0.75)` |
| `color.icon.full.inner.cloud` | `--color-cloud-white` | `rgba(255,255,255,0.60)` |
| `color.icon.full.sparkle` | `--color-sparkle` | `rgba(255,255,255,0.85)` |
| `color.icon.full.glow` | `--color-glow-pink` | `rgba(255,183,197,0.40)` |
| `color.icon.mono.drop.shadow` | `--color-shadow-warm` | `rgba(180,160,160,0.25)` |

---

## 渐变 Token 映射

| Design Token | CSS 变量名 | 说明 |
|-------------|-----------|------|
| `gradient.icon.full.body` | `--gradient-icon-full` | 135° 三色渐变：粉→紫→蓝 |
| `gradient.icon.mono.body` | `--gradient-icon-mono` | 135° 双色渐变：浅米紫→暖灰紫 |
| `gradient.icon.full.specular` | `--gradient-specular` | 径向渐变，白色中心→透明 |
| `gradient.icon.full.outer.glow` | `--gradient-ambient-glow` | 椭圆径向，粉紫混合 |

### Tailwind v4 自定义渐变映射规则

在 `@theme` 块中注册为 `--gradient-*` 变量，通过 `bg-[var(--gradient-icon-full)]` 引用。

对于多色停止（color stop）渐变，建议在 `@layer utilities` 中创建具名工具类，而非使用任意值语法，以确保设计系统一致性。

---

## 圆角 Token 映射

| Design Token | CSS 变量名 | Tailwind 工具类 | 值（估算值）|
|-------------|-----------|----------------|------------|
| `radius.icon.tail.tip` | `--radius-tail` | `rounded-[var(--radius-tail)]` | `12px` |
| `radius.icon.top.valley` | `--radius-valley` | `rounded-[var(--radius-valley)]` | `20px` |
| `radius.icon.peak` | `--radius-peak` | — | `40px` |
| — | `--radius-sm` | `rounded-sm` | `4px`（系统） |
| — | `--radius-md` | `rounded-md` | `8px`（系统） |
| — | `--radius-lg` | `rounded-lg` | `16px`（系统） |
| — | `--radius-xl` | `rounded-xl` | `24px`（系统） |
| — | `--radius-full` | `rounded-full` | `9999px`（系统） |

注意：图标主体使用自由曲线（贝塞尔路径），无法用 `border-radius` 表达。上表 radius token 仅适用于图标内子元素或其他 UI 组件。

---

## 阴影 Token 映射

| Design Token | CSS 变量名 | Tailwind 工具类 | 值（估算值）|
|-------------|-----------|----------------|------------|
| `shadow.icon.full.glow` | `--shadow-icon-glow` | `shadow-[var(--shadow-icon-glow)]` | `0 30px 80px rgba(200,182,255,0.45)` |
| `shadow.icon.mono.drop` | `--shadow-icon-drop` | `shadow-[var(--shadow-icon-drop)]` | `0 20px 30px rgba(180,160,160,0.25)` |
| `shadow.icon.inner.edge` | `--shadow-inner-edge` | `shadow-inner` + 自定义 | `inset 0 0 8px rgba(255,255,255,0.55)` |

### 全局阴影 Token 体系（供其他组件复用）

| 层级 | CSS 变量名 | 适用场景 |
|------|-----------|---------|
| 微阴影 | `--shadow-xs` | 按钮、标签 |
| 小阴影 | `--shadow-sm` | 卡片、输入框 |
| 中阴影 | `--shadow-md` | 浮层、Toast |
| 大阴影 | `--shadow-lg` | 模态框、抽屉 |
| 发光效果 | `--shadow-glow` | 焦点元素、图标 |

---

## 模糊 Token 映射

| Design Token | CSS 变量名 | Tailwind 工具类 | 值（估算值）|
|-------------|-----------|----------------|------------|
| `blur.icon.cloud.soft` | `--blur-soft` | `blur-[12px]` | `12px` |
| `blur.icon.glow.ambient` | `--blur-glow` | `blur-[80px]` | `80px` |
| `blur.icon.shadow` | `--blur-shadow` | `blur-[30px]` | `30px` |

Tailwind v4 内置模糊类（供参考）：`blur-sm`(4px)、`blur`(8px)、`blur-md`(12px)、`blur-lg`(16px)、`blur-xl`(24px)、`blur-2xl`(40px)、`blur-3xl`(64px)

---

## 字体 Token 映射

N/A for this asset type（图标无文字，字体 token 属于全局 Design System，在此仅列出品牌规范）

| 用途 | CSS 变量名 | 值 |
|------|-----------|-----|
| 中文主字体 | `--font-sans-cn` | `'PingFang SC', 'HarmonyOS Sans SC', system-ui` |
| 拉丁/数字字体 | `--font-sans-latin` | `'SF Pro Rounded', system-ui` |

---

## 透明度 Token 映射

| Design Token | CSS 变量名 | Tailwind 工具类 | 值（估算值）|
|-------------|-----------|----------------|------------|
| `opacity.icon.cloud` | `--opacity-cloud` | `opacity-60` | `0.60` |
| `opacity.icon.cloud.mono` | `--opacity-cloud-mono` | `opacity-[0.45]` | `0.45` |
| `opacity.icon.sparkle` | `--opacity-sparkle` | `opacity-85` | `0.85` |
| `opacity.icon.specular` | `--opacity-specular` | `opacity-75` | `0.75` |
| `opacity.icon.glow` | `--opacity-glow` | `opacity-40` | `0.40` |

---

## 动效 Token 映射

| Design Token | CSS 变量名 | Tailwind 工具类 | 值（估算值）|
|-------------|-----------|----------------|------------|
| `motion.icon.press.duration` | `--duration-press` | `duration-[120ms]` | `120ms` |
| `motion.icon.bounce.duration` | `--duration-bounce` | `duration-[400ms]` | `400ms` |
| `motion.icon.glow.pulse.duration` | `--duration-pulse` | `duration-[2500ms]` | `2500ms` |
| `motion.icon.press.easing` | `--ease-press` | `ease-out` | `cubic-bezier(0,0,0.58,1)` |
| `motion.icon.bounce.easing` | `--ease-spring` | 自定义 | `cubic-bezier(0.34,1.56,0.64,1)`（估算值） |

---

## Tailwind v4 `@theme` 注册规则建议

在项目根 CSS 文件（如 `app/globals.css`）中，通过 `@theme` 指令统一注册以上所有 token，建立 Design System 单一配置源。

命名规范：
- 颜色：`--color-{semantic-name}`（如 `--color-cherry-pink`）
- 渐变：`--gradient-{component-variant}`
- 阴影：`--shadow-{level}`
- 间距：`--spacing-{scale}`
- 动效：`--duration-{purpose}` / `--ease-{purpose}`

命名应优先使用语义名（`cherry-pink`）而非原子值（`pink-300`），以便在品牌色更新时只需修改 token 而无需批量替换工具类。

---

## 图标资源引入规则

图标作为静态资源（PNG/SVG）引入，不通过 Tailwind 类渲染形状。

| 场景 | 引入方式 | Tailwind 处理部分 |
|------|---------|-----------------|
| `<img>` 标签 | `src="/icons/icon_full_180.png"` | `w-[180px] h-[180px] rounded-[22%]`（iOS squircle 近似） |
| CSS background | `background-image: url(...)` | `bg-contain bg-no-repeat bg-center` |
| Splash Screen | 作为 `<img>` 居中 | `mx-auto` + 尺寸 token |
| 图标展示页 | `<img>` + 阴影 | `shadow-[var(--shadow-icon-glow)]`（全色版） |
