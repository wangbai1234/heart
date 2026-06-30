# 03 Design Tokens — Icon Set（24×24 系统图标）

## Color Tokens

### 图标颜色

| Token 名称 | 值 | 说明 | 出现位置 |
|-----------|-----|------|---------|
| `icon.default` | #4A4A6A（估算值） | 图标默认描边色，深蓝灰带紫调 | 全部 36 个图标 |
| `icon.primary` | #FFB7C5 | 激活/选中状态图标色（樱花粉，来自品牌 Primary） | 导航激活态 |
| `icon.secondary` | #A7C7E7 | 次要激活状态（天蓝，来自品牌 Secondary） | 语音/音频激活 |
| `icon.accent` | #C8B6FF | 强调状态（薰衣草紫，来自品牌 Accent） | Sparkle、Crown 等激励类 |
| `icon.disabled` | rgba(74, 74, 106, 0.30) | 禁用状态，30% 透明度 | MicOff 等禁用态 |
| `icon.on-primary` | #FFFFFF | 在彩色背景按钮上的图标色 | 填充型按钮内图标 |

### 背景颜色

| Token 名称 | 值 | 说明 |
|-----------|-----|------|
| `surface.canvas` | #FAF0EC（估算值） | 图标库画布背景色，暖奶油白 |
| `surface.card` | #FFFFFF | Row 1 图标组背景卡片色 |
| `surface.default` | #FFF8F3 | App 全局 Surface 色（参考品牌规范） |

### 品牌色（全局参考）

| Token 名称 | 值 | 说明 |
|-----------|-----|------|
| `color.primary` | #FFB7C5 | 樱花粉，主品牌色 |
| `color.secondary` | #A7C7E7 | 天空蓝，副品牌色 |
| `color.accent` | #C8B6FF | 薰衣草紫，强调色 |
| `color.ink` | #3A3A4A | 主文字 / 深色图标 |
| `color.surface` | #FFF8F3 | 奶油白，主背景 |

### 语义色（应用于图标状态）

| Token 名称 | 值 | 说明 |
|-----------|-----|------|
| `semantic.success` | #68D391（建议值） | 确认 / 成功（✓ 图标激活态） |
| `semantic.warning` | #F6AD55（建议值） | 警告 |
| `semantic.error` | #FC8181（建议值） | 错误 / 危险（× / Trash 危险态） |
| `semantic.info` | #76E4F7（建议值） | 信息提示 |

---

## Gradient Tokens

**本资产图标为纯单色描边，不使用渐变。**

以下为图标在激活/高亮状态下的建议渐变规范（设计稿未定义，为推导值）：

| Token 名称 | 起点色 | 终点色 | 方向 | 透明度 | 用途 |
|-----------|--------|--------|------|--------|------|
| `gradient.icon.love` | #FFB7C5 | #C8B6FF | 135° | 100% | Heart / AI Companion 图标激活渐变 |
| `gradient.icon.magic` | #C8B6FF | #A7C7E7 | 135° | 100% | Sparkle 魔法图标激活渐变 |
| `gradient.icon.warm` | #FFB7C5 | #FFD4A0 | 180° | 100% | Gift / Crown VIP 激励类渐变 |

---

## Radius Tokens

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `radius.icon-container` | 20 px（估算值） | Row 1 白色背景卡片圆角 |
| `radius.icon-bg` | 12 px（估算值） | 单图标触控背景圆角（Hover/Press 状态） |
| `radius.icon-none` | 0 | 图标描边路径本身无外部圆角容器 |

**图标路径内部圆角（stroke round cap / join）：**
- Stroke Line Cap: Round
- Stroke Line Join: Round
- 圆角系数：与图标 24dp 尺寸成正比，约 2–3 px 视觉圆角（估算值）

---

## Shadow Tokens

**图标本体不使用阴影。**

以下为图标容器在激活状态下的建议 Glow 效果（设计稿未定义，推导值）：

| Token 名称 | 颜色 | 透明度 | Blur | X Offset | Y Offset | Spread | 场景 |
|-----------|------|--------|------|---------|---------|--------|------|
| `shadow.icon.glow-pink` | #FFB7C5 | 60% | 12 px | 0 | 0 | 0 | 导航激活态粉色光晕 |
| `shadow.icon.glow-purple` | #C8B6FF | 60% | 12 px | 0 | 0 | 0 | Sparkle/Crown 激活光晕 |
| `shadow.icon.glow-blue` | #A7C7E7 | 60% | 12 px | 0 | 0 | 0 | 语音/音频激活光晕 |

---

## Blur Tokens

**N/A for this asset type（图标本体）** — 图标本身不使用模糊效果。

毛玻璃效果在图标承载的容器层级应用：

| Token 名称 | Blur 值 | 用途 |
|-----------|---------|------|
| `blur.glass.toolbar` | 20 px | 工具栏玻璃背景 |
| `blur.glass.nav` | 16 px | 底部导航栏玻璃背景 |

---

## Opacity Tokens

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `opacity.icon.default` | 100% | 正常状态 |
| `opacity.icon.disabled` | 30% | 禁用状态（如 MicOff 斜线覆盖效果） |
| `opacity.icon.pressed` | 70% | 按下瞬间反馈 |
| `opacity.icon.ghost` | 50% | 次要/辅助图标 |

---

## Typography Tokens

**N/A for this asset type（图标库无文字内容）**

图标若需搭配标签文字，使用以下 Token：

| Token 名称 | 字体 | 字号 | 字重 | 行高 | 颜色 |
|-----------|------|------|------|------|------|
| `type.icon-label` | PingFang SC | 10 px | Regular (400) | 14 px | `icon.default` |
| `type.icon-label-active` | PingFang SC | 10 px | Medium (500) | 14 px | `color.primary` |

---

## Spacing Scale

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `spacing.icon.size-sm` | 16 dp | 小图标尺寸 |
| `spacing.icon.size-md` | 24 dp | 标准图标尺寸（本套图标规范） |
| `spacing.icon.size-lg` | 32 dp | 大图标尺寸 |
| `spacing.icon.touch-target` | 44 dp | 最小触控区域（iOS HIG 规范） |
| `spacing.icon.padding-inner` | 10 dp | 图标到触控区域边缘内边距 |
| `spacing.icon.grid-gap` | 38 px（估算值） | 画布展示中的图标间距 |
| `spacing.icon.canvas-padding` | 60 px（估算值） | 画布四周外边距 |

---

## Motion Tokens（图标动效）

**设计稿未定义具体数值，以下为推导建议值：**

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `motion.icon.tap-duration` | 100 ms | 点击按下反馈持续时间 |
| `motion.icon.tap-easing` | ease-out | 点击缩放缓动 |
| `motion.icon.tap-scale` | 0.88 | 点击缩放比例 |
| `motion.icon.select-duration` | 200 ms | 导航切换选中动效 |
| `motion.icon.select-easing` | cubic-bezier(0.34, 1.56, 0.64, 1) | 弹性选中（轻微回弹） |
| `motion.icon.hover-duration` | 150 ms | Hover 色彩渐变时长（Web端） |
| `motion.icon.hover-easing` | ease-in-out | Hover 缓动 |
| `motion.icon.glow-duration` | 300 ms | 激活光晕淡入时长 |
| `motion.icon.glow-delay` | 0 ms | 无延迟即时响应 |
| `motion.icon.spring-stiffness` | 400 | Spring 弹性系数（React Native Animated） |
| `motion.icon.spring-damping` | 20 | Spring 阻尼系数 |

---

## 图标 Stroke 参数（画布实测估算）

| 参数 | 画布值（1024px基准） | 24dp换算值 | 说明 |
|------|-------------------|------------|------|
| Stroke Width | 约 14–16 px（估算值） | 约 1.5 dp | 标准描边宽度 |
| Stroke Line Cap | Round | Round | 端点圆头 |
| Stroke Line Join | Round | Round | 连接处圆角 |
| Stroke Color | #4A4A6A（估算值） | — | 深蓝灰紫 |
| Fill | None | None | 纯描边，无填充 |
