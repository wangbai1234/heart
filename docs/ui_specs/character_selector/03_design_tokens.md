# 03 Design Tokens — 角色页 Character Selector

## Color

### 品牌色

| Token | Hex / RGBA | 用途 |
|-------|------------|------|
| `color-primary` | `#FFB7C5` | 主品牌色，选择按钮渐变终点、标签底色 |
| `color-primary-deep` | `#FF8FAB` | 确认按钮渐变起点，按压态 |
| `color-secondary` | `#A7C7E7` | 辅助色（桃乐丝角色头像光晕蓝色） |
| `color-accent` | `#C8B6FF` | 强调色（神无月凛头像光晕紫色） |
| `color-surface` | `#FFF8F3` | 页面背景，奶油白 |
| `color-card` | `#FFFFFF` | 角色卡片背景纯白 |
| `color-glass` | `rgba(255,255,255,0.55)` | 玻璃效果基础色 |
| `color-glass-border` | `rgba(255,255,255,0.70)` | 玻璃组件描边 |

### 文字色

| Token | Hex / RGBA | 用途 |
|-------|------------|------|
| `color-ink` | `#3A3A4A` | 主文字色（角色描述，卡片内容） |
| `color-ink-heavy` | `#1A1A2E` | 重要标题（角色名称，估算值） |
| `color-text-secondary` | `rgba(58,58,74,0.65)` | 次要文字（描述段落） |
| `color-text-on-primary` | `#FFFFFF` | 主色背景上的文字（确认按钮，选中按钮勾） |
| `color-text-tag` | `#B06CA0` | 御姐型标签文字（粉紫色，估算值） |
| `color-text-tag-genki` | `#6B8CC8` | 元气型标签文字（蓝色，估算值） |

### 状态色

| Token | Hex / RGBA | 用途 |
|-------|------------|------|
| `color-selected` | `#FFB7C5` | 已选中状态填充 |
| `color-border-unselected` | `#FFB7C5` | 未选中"选择"按钮描边 |
| `color-overlay` | `rgba(255,248,243,0.80)` | 英雄区底部渐变叠加 |
| `color-success` | `#5CC8A4` | 成功状态（设计稿未直接出现，备用） |
| `color-warning` | `#FFCA7A` | 警告状态（设计稿未直接出现，备用） |
| `color-danger` | `#FF6B6B` | 危险状态（设计稿未直接出现，备用） |
| `color-info` | `#A7C7E7` | 信息状态（同 secondary） |
| `color-divider` | `rgba(58,58,74,0.10)` | 分割线（设计稿未出现，备用） |

---

## Gradient

| Token | 起点 | 终点 | 方向 | 用途 |
|-------|------|------|------|------|
| `gradient-cta-button` | `#FF8FAB` | `#FFB7C5` | → 水平 Left to Right | 确认选择按钮 |
| `gradient-hero-bottom-fade` | `rgba(255,248,243,0)` | `rgba(255,248,243,1)` | ↓ Top to Bottom | 英雄区底部渐变至页面背景 |
| `gradient-hero-sky` | `#D8AEED`（紫）→ `#FBCFE8`（粉）→ `#FDE4CE`（暖橙） | — | 径向渐变 / 多色 | 天空背景动漫插画（插画内置渐变） |
| `gradient-avatar-glow-rin` | `rgba(192,132,252,0.6)` → `rgba(109,40,217,0.3)` | 径向向外 | 神无月凛头像光晕（紫色） |
| `gradient-avatar-glow-taolesi` | `rgba(96,165,250,0.6)` → `rgba(37,99,235,0.3)` | 径向向外 | 桃乐丝头像光晕（蓝色） |
| `gradient-glass-heart` | `rgba(255,255,255,0.8)` → `rgba(255,182,193,0.4)` | ↗ 135° | 玻璃心形图标内部 |

---

## Radius

| Token | 值 | 使用场景 |
|-------|----|---------|
| `radius-xs` | 4 pt | 微小标签内圆角（估算值） |
| `radius-sm` | 8 pt | 小型元素 |
| `radius-md` | 12 pt | 性格标签（御姐型/元气型 pill） |
| `radius-lg` | 16 pt | 中等卡片元素 |
| `radius-xl` | 20 pt | 角色卡片整体圆角 |
| `radius-2xl` | 24 pt | 大型浮层 |
| `radius-pill` | 27 pt | 确认选择按钮（完整胶囊，height/2） |
| `radius-full` | 9999 pt | 完整圆形（头像容器、选中勾圆形按钮） |

---

## Shadow

| Token | 颜色 | 透明度 | Blur | Offset X | Offset Y | Spread | 使用场景 |
|-------|------|--------|------|---------|---------|--------|---------|
| `shadow-card` | `#000000` | 0.06 | 12 pt | 0 | 4 pt | 0 | 角色卡片 |
| `shadow-cta-button` | `#FF8FAB` | 0.35 | 16 pt | 0 | 6 pt | 0 | 确认选择按钮 |
| `shadow-avatar-ring` | `#C8B6FF` / `#A7C7E7` | 0.5 | 8 pt | 0 | 0 | 4 pt | 头像光晕描边（不同角色不同色） |
| `shadow-heart-glass` | `#FFB7C5` | 0.3 | 20 pt | 0 | 8 pt | 0 | 玻璃心形图标投影（估算值） |

---

## Blur（毛玻璃）

| Token | 值 | 使用场景 |
|-------|----|---------|
| `blur-glass-heart` | 8 pt（估算值） | 心形图标内部毛玻璃效果 |
| `blur-overlay` | 0 pt | 英雄区底部渐变叠加（无 blur） |

---

## Opacity

| Token | 值 | 使用场景 |
|-------|----|---------|
| `opacity-glass` | 0.55 | 玻璃组件基础透明度 |
| `opacity-glass-border` | 0.70 | 玻璃组件描边 |
| `opacity-description-text` | 0.75（估算值） | 角色描述段落文字 |
| `opacity-hero-overlay` | 0.80 | 英雄区底部渐变叠加 |
| `opacity-avatar-glow` | 0.50 | 头像光晕环 |

---

## Typography

### 字体族

| Token | 值 |
|-------|----|
| `font-family-chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` |
| `font-family-latin` | `SF Pro Rounded, system-ui, sans-serif` |

### 字号 / 字重 / 行高 / 字间距

| Token | 字号 | 字重 | 行高 | 字间距 | 颜色 | 用途 |
|-------|------|------|------|--------|------|------|
| `text-status-bar` | 15 pt | 600 Semibold | 1.2 | 0 | #1A1A2E | 状态栏时间 |
| `text-header-title` | 17 pt | 500 Medium | 1.3 | 0 | #3A3A4A | 导航栏标题 |
| `text-character-name` | 18 pt | 700 Bold | 1.2 | 0 | #1A1A2E（估算） | 角色名称 |
| `text-tag` | 12 pt | 500 Medium | 1.0 | 0 | 各 tag 专属色 | 性格标签 |
| `text-description` | 13 pt | 400 Regular | 1.6 | 0.2 pt | rgba(58,58,74,0.75) | 角色描述 |
| `text-cta-button` | 17 pt | 600 Semibold | 1.2 | 0.5 pt | #FFFFFF | 确认选择按钮 |
| `text-select-button` | 15 pt | 500 Medium | 1.2 | 0 | #FFB7C5 | 未选中"选择"按钮 |

---

## Spacing Scale

基础单位：4 pt

| Token | 值 | 常见用途 |
|-------|----|---------|
| `spacing-1` | 4 pt | 最小间距 |
| `spacing-2` | 8 pt | 标题与描述间距，Tag 内边距 |
| `spacing-3` | 12 pt | 卡片间距，头像与文字列间距 |
| `spacing-4` | 16 pt | 页面水平 Padding，卡片内 Padding |
| `spacing-5` | 20 pt | Header 水平 Padding，底部 CTA Padding |
| `spacing-6` | 24 pt | 大元素间距（估算值备用） |
| `spacing-8` | 32 pt | 区块间距（估算值备用） |
| `spacing-10` | 40 pt | 英雄区内心形距顶距离 |
| `spacing-12` | 48 pt | 大区块（估算值备用） |
| `spacing-16` | 64 pt | 超大间距（估算值备用） |

---

## Motion

| Token | 值 | 说明 |
|-------|----|------|
| `duration-fast` | 150 ms | 按钮按压反馈 |
| `duration-normal` | 250 ms | 卡片选中状态切换 |
| `duration-slow` | 400 ms | 页面进入动画 |
| `duration-hero` | 600 ms | 英雄区心形浮现 |
| `delay-card-stagger` | 80 ms | 卡片逐一出现的错落延迟 |
| `easing-standard` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | 标准过渡曲线（Material） |
| `easing-decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 元素进场减速 |
| `easing-spring` | `spring(1, 200, 20, 0)` | 选中态弹性反馈（推荐值） |
| `easing-bounce` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 确认按钮点击回弹 |
