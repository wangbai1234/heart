# 03 Design Tokens — App Icon（多色版 + 单色版）

## Color Tokens

### 展示画布背景

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `color.canvas.background` | `#FAE8D8` | 温暖米杏色，展示背景（估算值，接近 #FFF8F3 偏橙） |

### 全色渐变版 — 主体颜色

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `color.icon.full.gradient.start` | `#FFB7C5` | 樱花粉，左侧起点（与品牌 Primary 一致） |
| `color.icon.full.gradient.mid` | `#C8B6FF` | 薰衣草紫，中部过渡（与品牌 Accent 一致） |
| `color.icon.full.gradient.end` | `#A7C7E7` | 天蓝色，右侧终点（与品牌 Secondary 一致） |
| `color.icon.full.edge.highlight` | `rgba(255,255,255,0.75)` | 边缘玻璃高光（估算值） |
| `color.icon.full.inner.cloud` | `rgba(255,255,255,0.60)` | 内部云朵纹理（估算值） |
| `color.icon.full.sparkle` | `rgba(255,255,255,0.85)` | 星光点缀（估算值） |
| `color.icon.full.glow` | `rgba(255,183,197,0.40)` | 底部粉色外发光（估算值） |
| `color.icon.full.glow.blue` | `rgba(167,199,231,0.25)` | 底部蓝色外发光混合（估算值） |

### 单色版 — 主体颜色

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `color.icon.mono.base` | `#D6CDD4` | 主体基色，暖紫灰（估算值） |
| `color.icon.mono.highlight` | `#F0EBF0` | 顶部高光区域（估算值） |
| `color.icon.mono.shadow` | `#B8AEB8` | 暗部阴影（估算值） |
| `color.icon.mono.edge.highlight` | `rgba(255,255,255,0.65)` | 边缘玻璃高光（估算值） |
| `color.icon.mono.inner.cloud` | `rgba(255,255,255,0.45)` | 内部云朵（单色版饱和度更低，估算值） |
| `color.icon.mono.sparkle` | `rgba(255,255,255,0.80)` | 星光点缀（估算值） |
| `color.icon.mono.drop.shadow` | `rgba(180,160,160,0.25)` | 投影颜色（估算值） |
| `color.icon.mono.border` | `rgba(200,185,200,0.50)` | 轮廓描边（估算值） |

---

## Gradient Tokens

### 全色渐变版主体渐变

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `gradient.icon.full.body` | 方向：左下 → 右上（约 135°→ 315°，估算值） | 三色线性渐变 |
| 起点颜色 | `#FFB7C5`（粉红，左下方） | |
| 中间颜色 | `#C8B6FF`（薰衣草紫，中央偏左上） | 位置约 45%（估算值） |
| 终点颜色 | `#A7C7E7`（天蓝，右上方） | |
| 透明度 | 100% 不透明 | |

### 全色渐变版顶部高光渐变

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `gradient.icon.full.specular` | 径向渐变（Radial） | 模拟玻璃球面反光 |
| 中心颜色 | `rgba(255,255,255,0.80)` | |
| 边缘颜色 | `rgba(255,255,255,0.00)` | 完全透明 |
| 中心位置 | 图标顶部左侧 ≈ 30% x, 20% y（估算值） | |

### 单色版主体渐变

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `gradient.icon.mono.body` | 方向：左下 → 右上（约 135°，估算值） | |
| 起点颜色 | `#E8E0E8`（浅米紫，左下） | 估算值 |
| 终点颜色 | `#C0B8C8`（暖灰紫，右上） | 估算值 |

### 外发光渐变（全色版）

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `gradient.icon.full.outer.glow` | 椭圆径向渐变 | 底部地面光晕 |
| 中心颜色 | `rgba(200,182,255,0.45)` | 薰衣草紫光 |
| 边缘颜色 | `rgba(200,182,255,0.00)` | 完全透明 |

---

## Radius Tokens

| Token 名称 | 值（估算值） | 使用场景 |
|------------|------------|---------|
| `radius.icon.shape` | 动态曲线（非固定值） | 心形+气泡融合为自由曲线，不可用 border-radius 表达 |
| `radius.icon.tail.tip` | ≈ 12 px（估算值） | 气泡尾巴末端圆润处理 |
| `radius.icon.top.valley` | ≈ 20 px（估算值） | 心形顶部中央凹谷圆角 |
| `radius.icon.peak` | ≈ 40 px（估算值） | 心形双峰外侧曲率 |

注意：图标主体形状为复合贝塞尔曲线，所有 radius 值均为视觉估算，实际应以矢量路径控制点为准。

---

## Shadow Tokens

### 全色版外发光（Outer Glow）

| Token 名称 | 值（估算值） |
|------------|------------|
| `shadow.icon.full.glow` | |
| 颜色 | `rgba(200,182,255,0.45)` 混合 `rgba(255,183,197,0.35)` |
| Blur | 80 px |
| Spread | 0 px |
| Offset X | 0 px |
| Offset Y | +30 px（向下，贴近底部） |
| 场景 | 全色版图标底部环境光晕 |

### 单色版投影（Drop Shadow）

| Token 名称 | 值（估算值） |
|------------|------------|
| `shadow.icon.mono.drop` | |
| 颜色 | `rgba(180,160,160,0.25)` |
| Blur | 30 px |
| Spread | 0 px |
| Offset X | 0 px |
| Offset Y | +20 px |
| 场景 | 单色版图标底部落影 |

### 边缘内发光（Inner Edge Glow）

| Token 名称 | 值（估算值） |
|------------|------------|
| `shadow.icon.inner.edge` | |
| 颜色 | `rgba(255,255,255,0.55)` |
| Blur | 8 px |
| Spread | -2 px |
| Offset | 0 |
| 场景 | 两版本图标边缘玻璃折射效果 |

---

## Blur Tokens

| Token 名称 | 值（估算值） | 使用场景 |
|------------|------------|---------|
| `blur.icon.cloud.soft` | 12 px（估算值） | 内部云朵纹理的柔化模糊 |
| `blur.icon.glow.ambient` | 80 px（估算值） | 全色版底部环境光晕 |
| `blur.icon.shadow` | 30 px（估算值） | 单色版投影模糊 |

注：图标本身不使用毛玻璃（backdrop-filter），玻璃感通过渐变+高光+边缘光实现。

---

## Opacity Tokens

| Token 名称 | 值（估算值） | 使用场景 |
|------------|------------|---------|
| `opacity.icon.cloud` | 0.60 | 全色版内部云朵叠加 |
| `opacity.icon.cloud.mono` | 0.45 | 单色版内部云朵叠加 |
| `opacity.icon.sparkle` | 0.85 | 星光点缀 |
| `opacity.icon.specular` | 0.75 | 顶部高光椭圆 |
| `opacity.icon.edge.border` | 0.50 | 单色版轮廓描边 |
| `opacity.icon.glow` | 0.40 | 全色版外发光 |

---

## Typography Tokens

N/A for this asset type（图标内无文字元素）

App 名称「yuoyuo」不出现在图标画面内，不需要文字 token。

---

## Spacing Scale

N/A for this asset type（图标为单一符号，不存在组件间距体系）

参考展示画布布局间距：
| Token 名称 | 值（估算值） | 说明 |
|------------|------------|------|
| `spacing.icon.canvas.margin` | 55–80 px | 图标与画布边缘的透气间距 |
| `spacing.icon.between` | ≈ 30 px | 两版本图标间的视觉间距（经由中线自然分隔） |

---

## Motion Tokens

N/A for this asset type（PNG 静态图标，动效由应用层实现）

以下为建议值（设计意图，供研发参考）：

| Token 名称 | 值 | 使用场景 |
|------------|-----|---------|
| `motion.icon.press.scale` | 0.94 | 用户点击时压缩反馈 |
| `motion.icon.press.duration` | 120ms | 按下响应时间 |
| `motion.icon.press.easing` | `ease-out` | 压缩曲线 |
| `motion.icon.bounce.duration` | 400ms | 释放弹回 |
| `motion.icon.bounce.spring` | `spring(1, 100, 20, 0)` | 果冻弹性（iOS SwiftUI spring） |
| `motion.icon.glow.pulse.duration` | 2500ms | 外发光呼吸动效（桌面待机） |
| `motion.icon.glow.pulse.easing` | `ease-in-out` | 呼吸节奏 |
