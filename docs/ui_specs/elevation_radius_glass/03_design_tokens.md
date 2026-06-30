# 03 设计令牌 — Shadow / Radius / Glass Sample

> 本文件直接从 PNG 资产中提取，为 yuoyuo 设计系统的核心 Token 定义。

---

## 1. 颜色（Color）

### 主色板

| Token 名称 | 色值 | 用途 |
|-----------|------|------|
| `color.primary` | `#FFB7C5` | 樱花粉，Section 标题图标圆点、底部 ♥ |
| `color.secondary` | `#A7C7E7` | 天空蓝（出现于玻璃区块背景插画中） |
| `color.accent` | `#C8B6FF` | 薰衣草紫（设计系统备用，本图未直接使用） |
| `color.surface` | `#FFF8F3` | 奶油白，页面背景基底 |
| `color.ink` | `#3A3A4A` | 炭黑，所有标题与正文文字 |

### 背景与表面

| Token 名称 | 色值 | 用途 |
|-----------|------|------|
| `color.background.page` | `#FFF8F3` | 画布底色（奶油白基调） |
| `color.background.glow` | `rgba(255,183,197,0.45)` | 右上角樱花粉光晕（估算值） |
| `color.surface.card` | `rgba(255,255,255,0.95)` | 主容器卡片背景 |
| `color.surface.sampleBlock` | `rgba(255,255,255,1.0)` | Radius / Elevation 示例方块 |

### 玻璃覆层

| Token 名称 | 色值 | 用途 |
|-----------|------|------|
| `color.glass.35` | `rgba(255,255,255,0.35)` | 玻璃 35% 遮罩 |
| `color.glass.55` | `rgba(255,255,255,0.55)` | 玻璃 55% 遮罩（标准值） |
| `color.glass.75` | `rgba(255,255,255,0.75)` | 玻璃 75% 遮罩 |
| `color.glass.tinted` | `rgba(255,255,255,0.55) + 色调叠加` | 玻璃着色变体（白色 55% + 浅粉/蓝色调，估算值） |

### 边框与分割

| Token 名称 | 色值 | 用途 |
|-----------|------|------|
| `color.border.subtle` | `rgba(0,0,0,0.04)` | 方块极淡边框（估算值） |
| `color.divider` | `rgba(0,0,0,0.06)` | Section 间分隔（如有） |

### 文字色

| Token 名称 | 色值 | 用途 |
|-----------|------|------|
| `color.text.primary` | `#3A3A4A` | 标题、正文 |
| `color.text.secondary` | `rgba(58,58,74,0.60)` | 副描述文字（阴影参数描述行，估算值） |
| `color.text.brand` | `#FFB7C5` | 品牌色文字（底部 ♥ 图标） |

### 语义色

| Token 名称 | 色值 | 用途 |
|-----------|------|------|
| `color.semantic.info` | `#A7C7E7` | 天蓝（信息状态） |
| `color.semantic.warm` | `#FFB7C5` | 樱花粉（温暖状态） |

---

## 2. 渐变（Gradient）

### 页面背景渐变

| 属性 | 值 |
|------|-----|
| Token 名称 | `gradient.background.page` |
| 类型 | Radial Gradient（径向渐变，右上角为光源） |
| 光源色 | `#FFD4DD`（浅粉，高光中心，估算值） |
| 基底色 | `#FFF8F3`（奶油白） |
| 光晕范围 | 约右上 1/4 画布（估算值） |
| 用途 | 画布整体背景 |

### 无其他渐变

本资产未定义其他独立渐变 Token，玻璃区域背景来自插画图片而非程序渐变。

---

## 3. 圆角半径（Border Radius）

> 直接从 PNG Section 1 读取，为精确值。

| Token 名称 | 值 | 场景建议 |
|-----------|-----|---------|
| `radius.xs` | `4px` | 标签、徽标、小 chip |
| `radius.sm` | `8px` | 按钮、小卡片、输入框 |
| `radius.md` | `16px` | 标准卡片、对话气泡、模块块 |
| `radius.lg` | `24px` | 大卡片、底部 Sheet |
| `radius.xl` | `32px` | 主容器、全屏弹窗、页面大容器 |
| `radius.full` | `9999px` | 圆形按钮、头像、Pill 形状（体系补充） |

---

## 4. 阴影（Shadow / Elevation）

> 直接从 PNG Section 2 读取，为精确值。阴影颜色推断为黑色（`#000000`），方向为正下方（Y offset 正值）。

| Token 名称 | 等级名 | 模糊半径 | Y Offset（估算值） | X Offset | 颜色 | 不透明度 | 场景 |
|-----------|--------|---------|-----------------|---------|------|---------|------|
| `shadow.none` | 平面 | 0 | 0 | 0 | — | 0 | 完全平面元素 |
| `shadow.soft` | 柔和 | `6px` | `2px`（估算值） | 0 | `#000000` | `0.04` | 列表项、轻微悬浮 |
| `shadow.card` | 卡片 | `12px` | `4px`（估算值） | 0 | `#000000` | `0.06` | 标准卡片、对话卡 |
| `shadow.sheet` | 薄片 | `24px` | `8px`（估算值） | 0 | `#000000` | `0.08` | 底部 Sheet、悬浮面板 |
| `shadow.modal` | 模态 | `40px` | `12px`（估算值） | 0 | `#000000` | `0.10` | 模态弹窗、最高层级 |

> Y Offset 标注为"估算值"，PNG 中未明确标注偏移量数值。

### CSS box-shadow 参考格式（非代码，仅作规格记录）

```
shadow.soft  → 0 2px 6px rgba(0,0,0,0.04)
shadow.card  → 0 4px 12px rgba(0,0,0,0.06)
shadow.sheet → 0 8px 24px rgba(0,0,0,0.08)
shadow.modal → 0 12px 40px rgba(0,0,0,0.10)
```

---

## 5. 模糊（Blur）

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `blur.glass` | `16px` | 玻璃覆层背景模糊（4种变体统一使用） |
| `blur.glow` | `约 60px`（估算值） | 页面背景光晕散射模糊 |

---

## 6. 透明度（Opacity）

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `opacity.glass.light` | `0.35` | 玻璃 35% 轻薄覆层 |
| `opacity.glass.mid` | `0.55` | 玻璃 55% 标准覆层 |
| `opacity.glass.heavy` | `0.75` | 玻璃 75% 厚重覆层 |
| `opacity.shadow.soft` | `0.04` | 柔和阴影透明度 |
| `opacity.shadow.card` | `0.06` | 卡片阴影透明度 |
| `opacity.shadow.sheet` | `0.08` | 薄片阴影透明度 |
| `opacity.shadow.modal` | `0.10` | 模态阴影透明度 |

---

## 7. 字体（Typography）

> 本资产为参考图，字体来自设计系统定义，结合图中观察补充。

### 字体族

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `font.family.chinese` | `"PingFang SC", "HarmonyOS Sans SC", sans-serif` | 中文内容 |
| `font.family.latin` | `"SF Pro Rounded", sans-serif` | 数字、英文内容 |

### 字号（图中观察）

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `font.size.pageTitle` | 约 `28–32px`（估算值） | 页面标题"yuoyuo · 设计令牌参考" |
| `font.size.sectionTitle` | 约 `18–20px`（估算值） | Section 标题（"圆角半径"等） |
| `font.size.label.primary` | 约 `14px`（估算值） | 方块下方主标签（"4px"、"柔和(6/0.04)"等） |
| `font.size.label.secondary` | 约 `12px`（估算值） | 副描述（"阴影模糊 6px / 不透明度 0.04"） |
| `font.size.footer` | 约 `13–14px`（估算值） | 底部署名 |

### 字重

| Token 名称 | 值 | 用途 |
|-----------|-----|------|
| `font.weight.semibold` | `600` | 页面标题 |
| `font.weight.medium` | `500` | Section 标题 |
| `font.weight.regular` | `400` | 标签、描述文字 |

---

## 8. 间距（Spacing Scale）

> 结合图中估算，建立基础 4px 格栅。

| Token 名称 | 值 | 说明 |
|-----------|-----|------|
| `spacing.1` | `4px` | 最小间距，也是 radius.xs |
| `spacing.2` | `8px` | 图标与文字 Gap |
| `spacing.3` | `12px` | 方块与标签间距 |
| `spacing.4` | `16px` | 方块间 Gap |
| `spacing.6` | `24px` | Section 内标题与内容间距 |
| `spacing.8` | `32px` | 主容器底部 Padding |
| `spacing.10` | `40px` | Section 间垂直间距 |
| `spacing.12` | `48px` | 主容器左右/顶部 Padding |

---

## 9. 动效（Motion）

> N/A for this asset type — 本资产为静态参考图，不定义动效 Token。
> 动效 Token 参见独立动效规范文档。

---

## 10. Token 命名约定

- 命名采用 **点分层级**：`{类别}.{子类别}.{变体}`
- 示例：`shadow.card`、`radius.md`、`color.glass.55`
- 所有 Token 均小写，使用英文，禁止中文 Token 名
- 尺寸单位统一为 `px`
