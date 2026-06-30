# 03 Design Tokens — 颜色系统色板

> 所有 Token 均直接从 PNG 设计稿读取，HEX 值为精确值，尺寸/间距标注估算值时注明"（估算值）"。

---

## 1. 颜色 Tokens（Color）

### 1.1 主色系 Primary — 樱花粉（Cherry Blossom Pink）

品牌主色：`#FFB7C5`（400级）

| Token 名称 | 色阶 | HEX 值 |
|------------|------|--------|
| `color-primary-50` | 50 | `#FFF1F3` |
| `color-primary-100` | 100 | `#FFE0E6` |
| `color-primary-200` | 200 | `#FFC7D2` |
| `color-primary-300` | 300 | `#FFADC0` |
| `color-primary-400` | 400 ★BASE | `#FFB7C5` |
| `color-primary-500` | 500 | `#FF95AA` |
| `color-primary-600` | 600 | `#FF7691` |
| `color-primary-700` | 700 | `#FF5B7D` |
| `color-primary-800` | 800 | `#FF4369` |
| `color-primary-900` | 900 | `#E7335A` |

---

### 1.2 辅色系 Secondary — 梦幻天蓝（Sky Blue）

品牌辅色：`#A7C7E7`（400级）

| Token 名称 | 色阶 | HEX 值 |
|------------|------|--------|
| `color-secondary-50` | 50 | `#EEF6FF` |
| `color-secondary-100` | 100 | `#DDEBFA` |
| `color-secondary-200` | 200 | `#C7DEF5` |
| `color-secondary-300` | 300 | `#B1D1F0` |
| `color-secondary-400` | 400 ★BASE | `#A7C7E7` |
| `color-secondary-500` | 500 | `#8EB9E0` |
| `color-secondary-600` | 600 | `#6FA9D8` |
| `color-secondary-700` | 700 | `#5394CF` |
| `color-secondary-800` | 800 | `#3E80C6` |
| `color-secondary-900` | 900 | `#2D6AAC` |

---

### 1.3 点缀色系 Accent — 薰衣草草雾（Lavender Mist）

品牌点缀色：`#C8B6FF`（400级）

| Token 名称 | 色阶 | HEX 值 |
|------------|------|--------|
| `color-accent-50` | 50 | `#F3F0FF` |
| `color-accent-100` | 100 | `#E8E2FF` |
| `color-accent-200` | 200 | `#D9D0FF` |
| `color-accent-300` | 300 | `#CBBEFF` |
| `color-accent-400` | 400 ★BASE | `#C8B6FF` |
| `color-accent-500` | 500 | `#B5A2FF` |
| `color-accent-600` | 600 | `#9F8BFF` |
| `color-accent-700` | 700 | `#8772F7` |
| `color-accent-800` | 800 | `#6F5CE6` |
| `color-accent-900` | 900 | `#5747C2` |

---

### 1.4 表面 / 中性色系 Surface / Neutral — 暖奶油 → 炭灰

| Token 名称 | 色阶 | HEX 值 | 语义描述 |
|------------|------|--------|---------|
| `color-surface-50` | 50 | `#FFF8F3` | 页面背景色，画布底色 |
| `color-surface-100` | 100 | `#FFF2E8` | 浅底色 |
| `color-surface-200` | 200 | `#FDE8DA` | 卡片底色 |
| `color-surface-300` | 300 | `#FADEC8` | 分割线浅色 |
| `color-surface-400` | 400 | `#F6D5B4` | 边框色 |
| `color-surface-500` | 500 | `#EED0A0` | 中性暖黄 |
| `color-surface-600` | 600 | `#D8CAA8` | 中性棕灰 |
| `color-surface-700` | 700 | `#B6B1A2` | 副文字色 |
| `color-surface-800` | 800 | `#7A7873` | 次级文字色 |
| `color-surface-900` | 900 | `#3A3A4A` | 主文字色（炭灰） |

---

### 1.5 语义色系 Semantic — 状态提示

| Token 名称 | HEX 值 | 语义 | 配套图标 |
|------------|--------|------|---------|
| `color-semantic-success` | `#B6E2C7` | 成功 / Success | 绿色圆形勾选图标 |
| `color-semantic-warning` | `#FFD3A5` | 警告 / Warning | 橙色圆形感叹号图标 |
| `color-semantic-error` | `#F4A6A6` | 错误 / Error | 红色圆形叉号图标 |
| `color-semantic-info` | `#B6C7F4` | 信息 / Info | 蓝色圆形 i 图标 |

---

### 1.6 玻璃叠加色 Glass Overlay

用于磨砂玻璃（Frosted Glass）表面，叠加在任意底层渐变或背景色上方。

| Token 名称 | RGBA 值 | 透明度 | 使用场景 |
|------------|---------|--------|---------|
| `color-glass-35` | `rgba(255,255,255,0.35)` | 35% | 最透明，底层色彩高度透出 |
| `color-glass-55` | `rgba(255,255,255,0.55)` | 55% | 半透明，平衡可读性与美感（推荐常用） |
| `color-glass-75` | `rgba(255,255,255,0.75)` | 75% | 偏不透明，较强可读性 |
| `color-glass-90` | `rgba(255,255,255,0.90)` | 90% | 接近纯白，最强遮挡 |

---

### 1.7 背景 / 基础颜色 Background / Base

| Token 名称 | 值 | 说明 |
|------------|---|------|
| `color-bg-page` | `#FFF8F3` | 全局页面背景（暖奶油） |
| `color-bg-card` | `rgba(255,255,255,0.55)` | 玻璃卡片背景（标准） |
| `color-text-primary` | `#3A3A4A` | 主文字色（炭灰）= `surface-900` |
| `color-text-secondary` | `#7A7873` | 次级文字色 = `surface-800` |
| `color-text-placeholder` | `#B6B1A2` | 占位符文字 = `surface-700` |
| `color-border` | `#F6D5B4` | 边框色 = `surface-400` |
| `color-divider` | `#FADEC8` | 分割线 = `surface-300` |

---

## 2. 渐变 Tokens（Gradient）

> 画布背景及玻璃卡片底层均使用渐变色。以下基于视觉分析估算。

| Token 名称 | 起点色 | 终点色 | 方向 | 使用场景 |
|------------|--------|--------|------|---------|
| `gradient-bg-warm` | `#FFF8F3` | `#FFE8EA`（估算值） | 135° 对角 | 页面整体背景 |
| `gradient-glass-card` | `#FFE4EC`（估算值） | `#FFF0F5`（估算值） | 90°（上→下） | 玻璃卡片底层装饰渐变 |
| `gradient-primary-soft` | `#FFF1F3`（primary-50） | `#FFB7C5`（primary-400） | 180° | 主色渐变展示 |

---

## 3. 圆角 Tokens（Border Radius）

| Token 名称 | 值 | 使用场景 |
|------------|---|---------|
| `radius-sm` | 8 px（估算值） | 小标签、徽标 |
| `radius-md` | 12–14 px（估算值） | 色阶色块 pill |
| `radius-lg` | 16 px（估算值） | 语义色卡片 |
| `radius-xl` | 20–24 px（估算值） | 玻璃叠加卡片 |
| `radius-pill` | 999 px | 全圆角 pill（400徽标） |

---

## 4. 阴影 Tokens（Shadow）

> 设计稿中阴影较轻微，玻璃卡片可见柔和投影，以下为估算值。

| Token 名称 | 颜色 | 透明度 | Blur | Offset X | Offset Y | Spread | 场景 |
|------------|------|--------|------|----------|----------|--------|------|
| `shadow-card-soft` | `#FFB7C5`（估算值） | 15%（估算值） | 16 px（估算值） | 0 | 4 px（估算值） | 0 | 语义色卡片 |
| `shadow-glass` | `#C8B6FF`（估算值） | 10%（估算值） | 24 px（估算值） | 0 | 8 px（估算值） | -4 px（估算值） | 玻璃叠加卡片 |
| `shadow-none` | — | 0% | — | — | — | — | 色阶色块（无阴影） |

---

## 5. 模糊 Tokens（Blur — 毛玻璃）

| Token 名称 | 值 | 使用场景 |
|------------|---|---------|
| `blur-glass-sm` | 8 px（估算值） | 轻度磨砂（35%叠加卡片） |
| `blur-glass-md` | 16 px（估算值） | 标准磨砂（55%叠加卡片，推荐） |
| `blur-glass-lg` | 24 px（估算值） | 强磨砂（75%叠加卡片） |
| `blur-glass-xl` | 32 px（估算值） | 极强磨砂（90%叠加卡片） |

注：`backdrop-filter: blur()` 应用于玻璃卡片元素本身。

---

## 6. 透明度 Tokens（Opacity）

| Token 名称 | 值 | 使用场景 |
|------------|---|---------|
| `opacity-glass-35` | 0.35 | Glass Overlay 最透明档 |
| `opacity-glass-55` | 0.55 | Glass Overlay 标准档 |
| `opacity-glass-75` | 0.75 | Glass Overlay 较不透明档 |
| `opacity-glass-90` | 0.90 | Glass Overlay 最不透明档 |
| `opacity-disabled` | 0.40（估算值） | 禁用状态元素 |
| `opacity-placeholder` | 0.60（估算值） | 占位符文字 |

---

## 7. 字体排版 Tokens（Typography）

> 画布中可见的字体层级分析，尺寸为估算值。

| Token 名称 | 字体 | 字号 | 字重 | 行高 | 字距 | 颜色 | 层级 |
|------------|------|------|------|------|------|------|------|
| `text-display` | PingFang SC / SF Pro Rounded | 36–40 px（估算值） | SemiBold(600) | 1.2（估算值） | -0.5 px（估算值） | `#3A3A4A` | 页面主标题（yuoyuo · 颜色系统） |
| `text-section-title` | PingFang SC | 18–20 px（估算值） | Medium(500) | 1.4（估算值） | 0（估算值） | `#3A3A4A` | 色柱列标题 |
| `text-label` | SF Pro / PingFang SC | 14–16 px（估算值） | Regular(400) | 1.4（估算值） | 0（估算值） | `#3A3A4A` | 色阶数字标签（50/100...） |
| `text-hex` | SF Pro Mono / Monospace | 13–15 px（估算值） | Regular(400) | 1.3（估算值） | 0.2 px（估算值） | `#3A3A4A` / `#7A7873` | HEX 色值显示 |
| `text-semantic-name` | PingFang SC | 14–16 px（估算值） | Medium(500) | 1.3（估算值） | 0（估算值） | `#3A3A4A` | 语义色名称（成功/警告等） |
| `text-semantic-hex` | SF Pro Mono | 12–13 px（估算值） | Regular(400) | 1.3（估算值） | 0（估算值） | `#7A7873` | 语义色 HEX 值 |
| `text-glass-label` | PingFang SC | 14–16 px（估算值） | Regular(400) | 1.4（估算值） | 0（估算值） | `#7A7873` | 玻璃叠加卡片说明文字 |
| `text-footer` | SF Pro Rounded | 16–18 px（估算值） | Medium(500) | 1.2（估算值） | 0（估算值） | `#3A3A4A` | 页脚品牌文字 |

---

## 8. 间距 Scale Tokens（Spacing）

| Token 名称 | 值 | 说明 |
|------------|---|------|
| `space-1` | 4 px | 最小间隔 |
| `space-2` | 8 px | 图标与文字间距、页脚图标文字 gap |
| `space-3` | 12 px | 语义卡片间距 |
| `space-4` | 16 px | 色阶行间距、卡片内 padding |
| `space-5` | 20 px | 标题 margin |
| `space-6` | 24 px | 内容区 padding |
| `space-8` | 32 px | 玻璃卡片间距 |
| `space-10` | 40 px | 色柱列间距 |
| `space-12` | 48 px | 节区间距 |
| `space-15` | 60 px | 画布横向内边距（估算值） |

---

## 9. 动效 Tokens（Motion）

> 该资产为静态规范画布，动效由应用层定义，以下为 yuoyuo 通用推荐值。

| Token 名称 | 值 | 说明 |
|------------|---|------|
| `motion-duration-fast` | 150 ms | 状态切换（Hover/Press） |
| `motion-duration-normal` | 250 ms | 组件进入/退出 |
| `motion-duration-slow` | 400 ms | 页面过渡 |
| `motion-easing-ease-out` | `cubic-bezier(0.0, 0, 0.2, 1)` | 元素弹入（推荐） |
| `motion-easing-spring` | `spring(1, 100, 10, 0)` | 弹性动画（玻璃卡片浮入） |
| `motion-delay-stagger` | 30–50 ms per item | 色阶行顺序出现延迟 |

注：以上动效值为 yuoyuo 品牌级规范推荐，并非本画布中可见内容，设计稿未定义。
