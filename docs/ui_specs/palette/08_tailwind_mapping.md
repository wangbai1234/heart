# 08 Tailwind v4 映射规则（Tailwind Mapping）— 颜色系统色板

> 本文件仅建立**设计 Token → Tailwind v4 工具类命名**的映射规则，不生成任何代码实现。  
> 遵循 Tailwind v4 CSS-first 配置方式（`@theme` 指令）。

---

## 总体映射策略

1. **颜色**：使用 `--color-*` CSS 变量，在 `@theme` 块中定义，与 Tailwind v4 原生颜色系统无缝衔接
2. **间距**：扩展 Tailwind 默认 spacing scale，添加项目特定的间距值
3. **圆角**：扩展 `borderRadius` 配置，定义 yuoyuo 品牌圆角规范
4. **毛玻璃**：通过 `backdrop-blur` 工具类映射，定义 sm/md/lg/xl 档位
5. **阴影**：自定义 `boxShadow` 变量，映射品牌柔和阴影风格
6. **字体**：注册 PingFang SC / SF Pro Rounded 字体族，定义层级工具类
7. **动效**：自定义 `transitionDuration` 和 `transitionTimingFunction`

---

## 1. 颜色映射规则（Colors）

### 映射格式

```
设计 Token → Tailwind 工具类
color-primary-{step} → bg-primary-{step} / text-primary-{step} / border-primary-{step}
```

### 主色系 Primary（樱花粉）

| 设计 Token | HEX 值 | Tailwind 类名 | CSS 变量名 |
|-----------|--------|--------------|----------|
| `color-primary-50` | `#FFF1F3` | `bg-primary-50` | `--color-primary-50` |
| `color-primary-100` | `#FFE0E6` | `bg-primary-100` | `--color-primary-100` |
| `color-primary-200` | `#FFC7D2` | `bg-primary-200` | `--color-primary-200` |
| `color-primary-300` | `#FFADC0` | `bg-primary-300` | `--color-primary-300` |
| `color-primary-400` | `#FFB7C5` | `bg-primary-400` | `--color-primary-400` |
| `color-primary-500` | `#FF95AA` | `bg-primary-500` | `--color-primary-500` |
| `color-primary-600` | `#FF7691` | `bg-primary-600` | `--color-primary-600` |
| `color-primary-700` | `#FF5B7D` | `bg-primary-700` | `--color-primary-700` |
| `color-primary-800` | `#FF4369` | `bg-primary-800` | `--color-primary-800` |
| `color-primary-900` | `#E7335A` | `bg-primary-900` | `--color-primary-900` |

默认基准色映射：`bg-primary` → `#FFB7C5`（primary-400）

---

### 辅色系 Secondary（梦幻天蓝）

| 设计 Token | HEX 值 | Tailwind 类名 | CSS 变量名 |
|-----------|--------|--------------|----------|
| `color-secondary-50` | `#EEF6FF` | `bg-secondary-50` | `--color-secondary-50` |
| `color-secondary-100` | `#DDEBFA` | `bg-secondary-100` | `--color-secondary-100` |
| `color-secondary-200` | `#C7DEF5` | `bg-secondary-200` | `--color-secondary-200` |
| `color-secondary-300` | `#B1D1F0` | `bg-secondary-300` | `--color-secondary-300` |
| `color-secondary-400` | `#A7C7E7` | `bg-secondary-400` | `--color-secondary-400` |
| `color-secondary-500` | `#8EB9E0` | `bg-secondary-500` | `--color-secondary-500` |
| `color-secondary-600` | `#6FA9D8` | `bg-secondary-600` | `--color-secondary-600` |
| `color-secondary-700` | `#5394CF` | `bg-secondary-700` | `--color-secondary-700` |
| `color-secondary-800` | `#3E80C6` | `bg-secondary-800` | `--color-secondary-800` |
| `color-secondary-900` | `#2D6AAC` | `bg-secondary-900` | `--color-secondary-900` |

默认基准色映射：`bg-secondary` → `#A7C7E7`（secondary-400）

---

### 点缀色系 Accent（薰衣草草雾）

| 设计 Token | HEX 值 | Tailwind 类名 | CSS 变量名 |
|-----------|--------|--------------|----------|
| `color-accent-50` | `#F3F0FF` | `bg-accent-50` | `--color-accent-50` |
| `color-accent-100` | `#E8E2FF` | `bg-accent-100` | `--color-accent-100` |
| `color-accent-200` | `#D9D0FF` | `bg-accent-200` | `--color-accent-200` |
| `color-accent-300` | `#CBBEFF` | `bg-accent-300` | `--color-accent-300` |
| `color-accent-400` | `#C8B6FF` | `bg-accent-400` | `--color-accent-400` |
| `color-accent-500` | `#B5A2FF` | `bg-accent-500` | `--color-accent-500` |
| `color-accent-600` | `#9F8BFF` | `bg-accent-600` | `--color-accent-600` |
| `color-accent-700` | `#8772F7` | `bg-accent-700` | `--color-accent-700` |
| `color-accent-800` | `#6F5CE6` | `bg-accent-800` | `--color-accent-800` |
| `color-accent-900` | `#5747C2` | `bg-accent-900` | `--color-accent-900` |

默认基准色映射：`bg-accent` → `#C8B6FF`（accent-400）

---

### 表面 / 中性色系 Surface / Neutral

| 设计 Token | HEX 值 | Tailwind 类名 | CSS 变量名 |
|-----------|--------|--------------|----------|
| `color-surface-50` | `#FFF8F3` | `bg-surface-50` | `--color-surface-50` |
| `color-surface-100` | `#FFF2E8` | `bg-surface-100` | `--color-surface-100` |
| `color-surface-200` | `#FDE8DA` | `bg-surface-200` | `--color-surface-200` |
| `color-surface-300` | `#FADEC8` | `bg-surface-300` | `--color-surface-300` |
| `color-surface-400` | `#F6D5B4` | `bg-surface-400` | `--color-surface-400` |
| `color-surface-500` | `#EED0A0` | `bg-surface-500` | `--color-surface-500` |
| `color-surface-600` | `#D8CAA8` | `bg-surface-600` | `--color-surface-600` |
| `color-surface-700` | `#B6B1A2` | `bg-surface-700` | `--color-surface-700` |
| `color-surface-800` | `#7A7873` | `bg-surface-800` | `--color-surface-800` |
| `color-surface-900` | `#3A3A4A` | `bg-surface-900` | `--color-surface-900` |

---

### 语义色 Semantic

| 设计 Token | HEX 值 | Tailwind 类名 | CSS 变量名 |
|-----------|--------|--------------|----------|
| `color-semantic-success` | `#B6E2C7` | `bg-success` | `--color-success` |
| `color-semantic-warning` | `#FFD3A5` | `bg-warning` | `--color-warning` |
| `color-semantic-error` | `#F4A6A6` | `bg-error` | `--color-error` |
| `color-semantic-info` | `#B6C7F4` | `bg-info` | `--color-info` |

---

### 玻璃叠加色 Glass

| 设计 Token | RGBA 值 | Tailwind 类名 | CSS 变量名 |
|-----------|---------|--------------|----------|
| `color-glass-35` | `rgba(255,255,255,0.35)` | `bg-glass-35` | `--color-glass-35` |
| `color-glass-55` | `rgba(255,255,255,0.55)` | `bg-glass-55` | `--color-glass-55` |
| `color-glass-75` | `rgba(255,255,255,0.75)` | `bg-glass-75` | `--color-glass-75` |
| `color-glass-90` | `rgba(255,255,255,0.90)` | `bg-glass-90` | `--color-glass-90` |

---

### 语义别名映射

| 语义 Token | 映射 Token | Tailwind 类名 | 说明 |
|-----------|-----------|--------------|------|
| `color-bg-page` | `surface-50` | `bg-page` | 全局页面背景 |
| `color-text-primary` | `surface-900` | `text-ink` | 主文字色 |
| `color-text-secondary` | `surface-800` | `text-muted` | 次级文字色 |
| `color-text-placeholder` | `surface-700` | `text-placeholder` | 占位符文字 |
| `color-border` | `surface-400` | `border-soft` | 边框色 |
| `color-divider` | `surface-300` | `divide-soft` | 分割线 |

---

## 2. 间距映射规则（Spacing）

| 设计 Token | 值 | Tailwind 类名 | 说明 |
|-----------|---|--------------|------|
| `space-1` | 4 px | `p-1` / `m-1` / `gap-1` | 最小间隔（Tailwind 原生） |
| `space-2` | 8 px | `p-2` / `m-2` / `gap-2` | 图标文字间距（Tailwind 原生） |
| `space-3` | 12 px | `p-3` / `gap-3` | 卡片内间距（Tailwind 原生） |
| `space-4` | 16 px | `p-4` / `gap-4` | 色阶行间距（Tailwind 原生） |
| `space-5` | 20 px | `p-5` / `gap-5` | 标题 margin（Tailwind 原生） |
| `space-6` | 24 px | `p-6` / `gap-6` | 内容区 padding（Tailwind 原生） |
| `space-8` | 32 px | `p-8` / `gap-8` | 玻璃卡片间距（Tailwind 原生） |
| `space-10` | 40 px | `p-10` / `gap-10` | 色柱列间距（Tailwind 原生） |
| `space-12` | 48 px | `p-12` / `gap-12` | 节区间距（Tailwind 原生） |
| `space-15` | 60 px | `px-15` | 画布横向内边距（自定义） |

自定义间距需在 `@theme` 中扩展：`--spacing-15: 60px`

---

## 3. 圆角映射规则（Border Radius）

| 设计 Token | 值 | Tailwind 类名 | CSS 变量 |
|-----------|---|--------------|---------|
| `radius-sm` | 8 px | `rounded-sm` | 扩展原生 sm |
| `radius-md` | 12 px | `rounded-md` | 扩展原生 md |
| `radius-lg` | 16 px | `rounded-lg` | 扩展原生 lg |
| `radius-xl` | 20–24 px | `rounded-xl` | 扩展原生 xl |
| `radius-2xl` | 24 px | `rounded-2xl` | 扩展原生 2xl |
| `radius-pill` | 9999 px | `rounded-full` | Tailwind 原生 full |

建议在 `@theme` 中覆盖原生值以匹配设计规范。

---

## 4. 毛玻璃模糊映射规则（Backdrop Blur）

| 设计 Token | 值 | Tailwind 类名 |
|-----------|---|--------------|
| `blur-glass-sm` | 8 px | `backdrop-blur-sm` |
| `blur-glass-md` | 16 px | `backdrop-blur-md` |
| `blur-glass-lg` | 24 px | `backdrop-blur-lg` |
| `blur-glass-xl` | 32 px | `backdrop-blur-xl` |

Tailwind v4 的 `backdrop-blur-{size}` 需在 `@theme` 中定义具体像素值，确认与品牌规范一致。

---

## 5. 阴影映射规则（Box Shadow）

| 设计 Token | 映射 Tailwind 类名 | 说明 |
|-----------|-----------------|------|
| `shadow-card-soft` | `shadow-card` | 语义色卡片柔和粉色投影 |
| `shadow-glass` | `shadow-glass` | 玻璃卡片紫色柔和投影 |
| `shadow-none` | `shadow-none` | 无阴影（色阶色块） |

自定义阴影需在 `@theme` 中使用 `--shadow-card` / `--shadow-glass` 变量定义。

---

## 6. 字体映射规则（Font）

| 设计 Token | 字体族 | Tailwind 类名 |
|-----------|--------|--------------|
| `font-sans-zh` | PingFang SC, HarmonyOS Sans SC | `font-sans` (中文扩展) |
| `font-sans-en` | SF Pro Rounded | `font-rounded` (自定义) |
| `font-mono` | SF Pro Mono | `font-mono` |

字体大小映射（估算值）：

| 语义层级 | 字号 | Tailwind 类名 |
|---------|------|--------------|
| Display | 38 px | `text-4xl`（或自定义 `text-display`） |
| Section Title | 20 px | `text-xl` |
| Body Label | 16 px | `text-base` |
| Caption / HEX | 13–14 px | `text-sm` |
| Micro | 12 px | `text-xs` |

---

## 7. 动效映射规则（Animation）

| 设计 Token | 值 | Tailwind 类名 |
|-----------|---|--------------|
| `motion-duration-fast` | 150 ms | `duration-150` |
| `motion-duration-normal` | 250 ms | `duration-250`（自定义） |
| `motion-duration-slow` | 400 ms | `duration-400`（自定义） |
| `motion-easing-ease-out` | `cubic-bezier(0.0, 0, 0.2, 1)` | `ease-out`（覆盖默认） |

自定义 duration 需在 `@theme` 中扩展：
- `--animate-duration-250: 250ms`
- `--animate-duration-400: 400ms`

---

## 8. 建立 Design System 的方法论

### 步骤一：定义 CSS 变量层（Variable Layer）
在项目 CSS 入口文件（`globals.css` / `base.css`）的 `@theme` 块中注册所有颜色、间距、圆角变量。

### 步骤二：建立语义别名层（Semantic Alias Layer）
在变量层之上，将设计语义（`bg-page` / `text-ink` / `bg-glass`）映射为对应原始变量，使组件只引用语义别名而非具体色值。

### 步骤三：工具类约束（Utility Constraint）
通过 Tailwind v4 的 `@layer utilities` 仅保留项目实际使用的工具类，删除未使用的颜色避免包体积膨胀。

### 步骤四：组件规范文件（Component Spec）
为每个可复用组件（GlassCard / SemanticCard / ColorScaleRow）定义标准工具类组合，形成组件级别的设计规范表格。

### 步骤五：暗色模式扩展（Dark Mode）
为每个 Token 提供暗色模式变体，通过 CSS media query 或 `.dark` 类切换，确保品牌色在暗色模式下的可读性与情感一致性。

---

## 命名规范约定

- 所有自定义 CSS 变量前缀：`--color-`（颜色）/ `--spacing-`（间距）/ `--radius-`（圆角）/ `--shadow-`（阴影）
- Tailwind 工具类命名遵循 Tailwind 原生风格，不使用下划线，使用连字符
- 语义别名直接使用语义词汇（`ink` / `muted` / `glass`），不使用颜色名（避免 `pink-button` 类命名）
