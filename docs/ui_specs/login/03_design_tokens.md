# 03 Design Tokens — 登录页 Login

所有值以目视分析为准，标注「（估算值）」表示目测推算，不可直接用于生产，需与设计源文件核对。

---

## Color

### Brand
| Token | Value | 说明 |
|-------|-------|------|
| `color.brand.primary` | `#FFB7C5` | 樱花粉，主色调 |
| `color.brand.secondary` | `#A7C7E7` | 天蓝色，辅助色 |
| `color.brand.accent` | `#C8B6FF` | 薰衣草紫，强调色 |

### Background / Surface
| Token | Value | 说明 |
|-------|-------|------|
| `color.bg.page` | `#FFF8F3` | 奶油白，页面底色 |
| `color.bg.surface` | `rgba(255,255,255,0.75)` | 表单卡毛玻璃底色（估算值） |
| `color.bg.glass` | `rgba(255,255,255,0.55)` | 标准玻璃面底色 |
| `color.bg.overlay` | `rgba(255,240,245,0.60)` | 插画与内容区过渡遮罩（估算值） |

### Text
| Token | Value | 说明 |
|-------|-------|------|
| `color.text.primary` | `#3A3A4A` | 主文字（yuoyuo字标、兑换码文字） |
| `color.text.secondary` | `#8A8898` | 次要文字（说明文字、协议文字基底）（估算值） |
| `color.text.placeholder` | `#B0A8B4` | 邮箱输入占位符（估算值） |
| `color.text.link` | `#FFB7C5` | 协议链接文字色 |
| `color.text.on-primary` | `#FFFFFF` | 主按钮文字 |

### Divider / Border
| Token | Value | 说明 |
|-------|-------|------|
| `color.divider` | `rgba(0,0,0,0.06)` | 输入行与说明文字之间的分隔线（估算值） |
| `color.border.card` | `rgba(255,255,255,0.60)` | 表单卡玻璃边框（估算值） |

### Semantic（本页未见，保留定义）
| Token | Value | 说明 |
|-------|-------|------|
| `color.semantic.success` | `#4CAF50` | 成功状态（设计稿未体现） |
| `color.semantic.warning` | `#FFB74D` | 警告状态（设计稿未体现） |
| `color.semantic.danger` | `#FF5252` | 错误状态（邮箱格式错误，设计稿未体现） |
| `color.semantic.info` | `#4FC3F7` | 信息提示（设计稿未体现） |

---

## Gradient

### 插画区背景渐变（天空）
| 属性 | 值 |
|------|----|
| 类型 | 多色径向/线性混合（anime sky）（估算值） |
| 顶部颜色 | `#9B8EC4`（薰衣草灰紫，估算值） |
| 中部颜色 | `#E8C4D0`（浅玫瑰粉，估算值） |
| 底部/地平线 | `#FFDDC1`（暖桃橙，估算值） |
| 方向 | 从上至下（top → bottom） |
| 用途 | 插画区全幅背景 |

### 页面下半背景渐变
| 属性 | 值 |
|------|----|
| 起点颜色 | `#FFDDD8`（淡粉，估算值） |
| 终点颜色 | `#FFF8F3`（奶油白） |
| 方向 | 从上至下（top → bottom） |
| 用途 | 品牌区 + 表单区 + 底部区背景 |

### 主按钮渐变
| 属性 | 值 |
|------|----|
| 起点颜色 | `#FFB7C5`（樱花粉） |
| 终点颜色 | `#FF8FAB`（深玫红粉，估算值） |
| 方向 | 从左至右（left → right） |
| 透明度 | 100% |
| 用途 | 「发送登录链接」按钮背景 |

### 玻璃心形光晕
| 属性 | 值 |
|------|----|
| 类型 | 径向渐变（radial） |
| 中心颜色 | `rgba(255,255,255,0.90)`（白色高光，估算值） |
| 边缘颜色 | `rgba(200,182,255,0.70)`（薰衣草紫，估算值） |
| 外层光晕 | `rgba(255,183,197,0.40)`（粉色软光，估算值） |
| 用途 | 玻璃心形图标主体 |

---

## Radius

| Token | Value | 使用场景 |
|-------|-------|---------|
| `radius.xs` | `4px` | 微小元素（tag 等，本页未见） |
| `radius.sm` | `8px` | 小元素 |
| `radius.md` | `16px` | 中等元素 |
| `radius.lg` | `24px` | 输入行圆角（估算值） |
| `radius.xl` | `32px` | 表单卡圆角（估算值） |
| `radius.2xl` | `48px` | 表单卡圆角（视觉更准确，估算值） |
| `radius.pill` | `9999px` | 主按钮（完整 pill 形状） |
| `radius.circle` | `50%` | 图标容器圆形 |

---

## Shadow

### 表单卡阴影
| 属性 | 值 |
|------|----|
| 颜色 | `rgba(255,183,197,0.15)`（粉色软阴影，估算值） |
| Blur | `40px`（估算值） |
| Offset X | `0px` |
| Offset Y | `8px`（估算值） |
| Spread | `0px` |

### 主按钮阴影
| 属性 | 值 |
|------|----|
| 颜色 | `rgba(255,143,171,0.35)`（玫红粉阴影，估算值） |
| Blur | `24px`（估算值） |
| Offset X | `0px` |
| Offset Y | `8px`（估算值） |
| Spread | `-4px`（估算值） |

### 玻璃心形发光效果
| 属性 | 值 |
|------|----|
| 颜色 | `rgba(255,255,255,0.80)`（白色辉光，估算值） |
| Blur | `60px`（估算值） |
| Offset | `0, 0`（四向均匀） |
| 用途 | 心形图标外发光（glow） |

---

## Blur

| Token | Value | 使用场景 |
|-------|-------|---------|
| `blur.glass-sm` | `12px`（估算值） | 轻度毛玻璃（细节叠层） |
| `blur.glass-md` | `20px`（估算值） | 表单卡背景模糊 |
| `blur.glass-lg` | `40px`（估算值） | 强度毛玻璃效果 |

---

## Opacity

| Token | Value | 使用场景 |
|-------|-------|---------|
| `opacity.glass` | `0.75` | 表单卡白色背景（估算值） |
| `opacity.glass-border` | `0.60` | 玻璃卡边框（估算值） |
| `opacity.overlay` | `0.60` | 插画与内容过渡遮罩（估算值） |
| `opacity.placeholder` | `0.50` | 输入框占位文字（估算值） |
| `opacity.divider` | `0.06` | 分隔线（估算值） |

---

## Typography

### 字体族
| Token | Value | 用途 |
|-------|-------|------|
| `font.family.chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` | 中文文本 |
| `font.family.brand` | `SF Pro Rounded, system-ui, sans-serif` | "yuoyuo" 字标（拉丁字符） |
| `font.family.ui` | `PingFang SC, SF Pro Rounded, sans-serif` | 按钮、输入框等 UI 文本 |

### 字号 Scale（设计画布 1024px 基准，估算值）
| Token | Canvas Size | 逻辑 Size | 使用场景 |
|-------|-------------|-----------|---------|
| `font.size.display` | `96px` | `~36px` | "yuoyuo" 品牌字标 |
| `font.size.title-lg` | `36px` | `~14px` | Tagline（估算值） |
| `font.size.body-lg` | `40px` | `~15px` | 主按钮文字（估算值） |
| `font.size.body-md` | `28px` | `~11px` | 说明文字（估算值） |
| `font.size.body-sm` | `26px` | `~10px` | 协议文字（估算值） |
| `font.size.caption` | `30px` | `~11px` | 兑换码链接（估算值） |
| `font.size.placeholder` | `28px` | `~11px` | 输入框占位文字（估算值） |

### 字重
| Token | Value | 使用场景 |
|-------|-------|---------|
| `font.weight.regular` | `400` | 说明文字、协议文字 |
| `font.weight.medium` | `500` | 按钮文字、输入占位 |
| `font.weight.semibold` | `600` | Tagline |
| `font.weight.bold` | `700` | "yuoyuo" 字标 |

### 行高
| Token | Value | 使用场景 |
|-------|-------|---------|
| `line-height.tight` | `1.2` | 大标题 / 字标 |
| `line-height.normal` | `1.5` | 说明文字、协议文字 |
| `line-height.loose` | `1.6` | 长文说明（估算值） |

### 字间距
| Token | Value | 使用场景 |
|-------|-------|---------|
| `letter-spacing.brand` | `-0.02em`（估算值） | "yuoyuo" 字标 |
| `letter-spacing.ui` | `0` | 默认 UI 文本 |
| `letter-spacing.chinese` | `0.02em`（估算值） | 中文 Tagline |

---

## Spacing Scale

| Token | Value | 使用场景示例 |
|-------|-------|------------|
| `space.1` | `4px` | 微间距 |
| `space.2` | `8px` | 图标与文字间距 |
| `space.3` | `12px` | 小间距 |
| `space.4` | `16px` | 标准间距 |
| `space.5` | `20px` | 中等间距 |
| `space.6` | `24px` | 说明文字上边距 |
| `space.8` | `32px` | 按钮上边距 |
| `space.10` | `40px` | 区块间距 |
| `space.12` | `48px` | 表单卡 Padding |
| `space.16` | `64px` | 页面左右边距 |
| `space.20` | `80px` | 大区块间距 |
| `space.24` | `96px` | 安全区高度参考 |

---

## Motion

| Token | Value | 使用场景 |
|-------|-------|---------|
| `motion.duration.fast` | `150ms` | Pressed 状态反馈 |
| `motion.duration.normal` | `300ms` | 页面元素入场 |
| `motion.duration.slow` | `500ms` | 插画渐入、页面转场 |
| `motion.duration.hero` | `800ms` | 心形图标漂浮动画（估算值） |
| `motion.delay.stagger` | `80ms` | 元素逐一入场延迟 |
| `motion.easing.ease-out` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 元素入场 |
| `motion.easing.ease-in-out` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | 通用过渡 |
| `motion.easing.spring` | `spring(1, 100, 10, 0)`（估算值） | 心形漂浮弹簧动画 |
| `motion.easing.bounce` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 按钮 Pressed 弹回 |
