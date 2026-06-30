# 03 Design Tokens — 设置页 Settings

---

## Color

### 品牌色 / Brand
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-primary` | `#FFB7C5` | 主品牌粉色，会员标签背景、Toggle ON 轨道、Slider Thumb、Icon 描边 |
| `color-primary-deep` | `#FF85A1` | 主品牌粉色深版，Toggle 渐变终点、按下态 |
| `color-secondary` | `#A7C7E7` | 天空蓝，辅助色（本页未显著使用） |
| `color-accent` | `#C8B6FF` | 薰衣草紫，背景光晕、渐变点缀 |

### 背景色 / Background
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-bg-page-top` | `#FDEEF3` | 页面背景渐变起点（顶部浅粉）（估算值） |
| `color-bg-page-mid` | `#F5E8F5` | 页面背景渐变中点（薰衣草白粉）（估算值） |
| `color-bg-page-bottom` | `#E8D5F0` | 页面背景渐变终点（深紫粉）（估算值） |
| `color-surface` | `#FFF8F3` | 奶油白，卡片底层参考色 |

### 卡片 / Surface & Glass
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-card-bg` | `rgba(255,255,255,0.88)` | GroupCard 背景（半透白，轻 Glass 效果）（估算值） |
| `color-card-profile-bg` | `rgba(255,255,255,0.90)` | Profile 卡背景（略高不透明度）（估算值） |
| `color-glass` | `rgba(255,255,255,0.55)` | 标准 Glass Token（用于 overlay 浮层等） |
| `color-divider` | `rgba(229,224,234,0.8)` | 行内分隔线（估算值） |
| `color-border` | `rgba(255,183,197,0.25)` | 卡片边框（极淡粉色描边，若有）（估算值） |

### 文字 / Text
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-text-primary` | `#3A3A4A` | 主文字（页面标题、Row Label、名字） |
| `color-text-secondary` | `#8A8A9A` | 次要文字（Section Label、副文字如日期） |
| `color-text-placeholder` | `#BCBCC8` | 占位文字（估算值） |
| `color-text-danger` | `#FF85A1` | 危险操作文字（注销账号）（估算值） |
| `color-text-member-badge` | `#FF85A1` | 会员标签文字颜色（估算值） |

### 状态色 / Semantic
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-success` | `#7ECBA5` | 成功状态（本页未显著使用）（估算值） |
| `color-warning` | `#FFD580` | 警告状态（本页未显著使用）（估算值） |
| `color-danger` | `#FF85A1` | 危险/破坏性操作（注销账号粉红警示） |
| `color-info` | `#A7C7E7` | 信息提示（本页未显著使用） |

### 控件专用色
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-toggle-on-track` | `#FFB7C5` 至 `#FF85A1` | Toggle ON 轨道渐变 |
| `color-toggle-thumb` | `#FFFFFF` | Toggle 滑块 |
| `color-toggle-off-track` | `rgba(200,200,210,0.5)` | Toggle OFF 轨道（估算值） |
| `color-slider-track` | `rgba(200,200,210,0.6)` | Slider 未选中轨道（估算值） |
| `color-slider-thumb` | `#FFB7C5` | Slider Thumb 颜色 |
| `color-segment-selected-bg` | `#FFFFFF` | Segment Picker 选中项背景 |
| `color-segment-container-bg` | `rgba(240,235,245,0.8)` | Segment Picker 容器背景（估算值） |
| `color-chevron` | `#C0C0CC` | 列表右侧箭头颜色（估算值） |

### Overlay
| Token Name | Hex / RGBA | 用途 |
|-----------|-----------|------|
| `color-overlay` | `rgba(30,20,40,0.4)` | Modal/弹窗遮罩（估算值） |

---

## Gradient

### 页面背景渐变
```
name: bg-page-gradient
type: linear
direction: 180deg（从上到下）
stops:
  - 0%   #FDEEF3  （浅粉白）（估算值）
  - 45%  #F5E8F5  （薰衣草白粉）（估算值）
  - 100% #E8D5F0  （紫粉色）（估算值）
opacity: 1.0
用途: 全屏固定背景
```

### 底部光晕（Glow）
```
name: bg-glow-bottom-left
type: radial
center: 左下角（约 x=0, y=bottom）
radius: ~200 pt（估算值）
stops:
  - 0%   rgba(200,182,255,0.6)  （薰衣草紫）（估算值）
  - 100% rgba(200,182,255,0.0)
用途: 背景装饰光晕
```

### Toggle ON 轨道渐变
```
name: toggle-on-gradient
type: linear
direction: 90deg（左到右）
stops:
  - 0%   #FFB7C5
  - 100% #FF85A1
用途: 积极提醒 Toggle 开启状态
```

### 会员标签背景
```
name: badge-member-bg
type: linear or solid
stops:
  - 0%   rgba(255,183,197,0.25)（估算值）
  - 100% rgba(255,183,197,0.15)（估算值）
用途: Profile 卡会员身份标签
```

---

## Radius（圆角）

| Token Name | 数值 | 使用场景 |
|-----------|------|---------|
| `radius-xs` | 4 pt | 细节装饰（估算值） |
| `radius-sm` | 8 pt | 小标签内圆角（估算值） |
| `radius-md` | 12 pt | 行内 Segment Picker（估算值） |
| `radius-lg` | 16 pt | 中型卡片（估算值） |
| `radius-xl` | 20 pt | 主要 GroupCard、Profile Card（估算值） |
| `radius-2xl` | 24 pt | 大型浮层/Modal（估算值） |
| `radius-full` | 9999 pt | 圆形头像、圆形 Toggle、圆形 Thumb |
| `radius-badge` | 11 pt | 会员身份标签（估算值） |

---

## Shadow（阴影）

| Token Name | 参数 | 使用场景 |
|-----------|------|---------|
| `shadow-card` | `color: rgba(180,160,200,0.12), blur: 16pt, offset: (0,4pt), spread: 0` | GroupCard 投影（估算值） |
| `shadow-profile-card` | `color: rgba(180,160,200,0.15), blur: 20pt, offset: (0,6pt), spread: 0` | Profile 卡投影（估算值） |
| `shadow-segment-selected` | `color: rgba(0,0,0,0.08), blur: 4pt, offset: (0,1pt), spread: 0` | Segment Picker 选中项（估算值） |
| `shadow-toggle` | `color: rgba(0,0,0,0.10), blur: 6pt, offset: (0,2pt), spread: 0` | Toggle 控件（估算值） |

---

## Blur（模糊）

| Token Name | 数值 | 使用场景 |
|-----------|------|---------|
| `blur-glass-light` | 12 pt | 卡片轻 glassmorphism（估算值） |
| `blur-glass-heavy` | 20 pt | 浮层/Modal 毛玻璃（估算值） |
| `blur-glow` | 40 pt | 背景光晕装饰（估算值） |

---

## Opacity（透明度）

| Token Name | 值 | 使用场景 |
|-----------|-----|---------|
| `opacity-card` | 0.88 | GroupCard 背景透明度（估算值） |
| `opacity-glass` | 0.55 | 标准 Glass 层（估算值） |
| `opacity-divider` | 0.8 | 分隔线透明度（估算值） |
| `opacity-icon-secondary` | 0.65 | 次要图标（估算值） |
| `opacity-disabled` | 0.4 | 禁用态（估算值） |
| `opacity-overlay` | 0.4 | 遮罩层（估算值） |

---

## Typography（字体排版）

### 字体族
```
Chinese: PingFang SC / HarmonyOS Sans SC
Latin & Numbers: SF Pro Rounded
```

### 文字层级规范

| 层级 | 名称 | 字号 | 字重 | 行高 | 字间距 | 颜色 Token | 使用场景 |
|------|------|------|------|------|--------|-----------|---------|
| T1 | Display | — | — | — | — | — | 本页未使用 |
| T2 | Title / NavBar | 18 pt | Medium(500) | 24 pt | 0 | `color-text-primary` | 导航栏"设置"标题（估算值） |
| T3 | Headline | 17 pt | Semibold(600) | 22 pt | 0 | `color-text-primary` | 用户名"晨曦"（估算值） |
| T4 | Body | 15–16 pt | Regular(400) | 22 pt | 0 | `color-text-primary` | 设置行 Label（估算值） |
| T5 | Body Secondary | 13 pt | Regular(400) | 18 pt | 0 | `color-text-secondary` | 副文字（日期、时段）（估算值） |
| T6 | Caption | 12 pt | Regular(400) | 16 pt | 0.2 pt | `color-text-secondary` | Section Label 分组标题（估算值） |
| T7 | Badge | 12 pt | Medium(500) | 16 pt | 0.3 pt | `color-text-member-badge` | 会员身份标签（估算值） |
| T8 | Segment | 13 pt | Regular(400) | — | 0 | `color-text-primary` | Segment Picker 选项（估算值） |

---

## Spacing Scale（间距体系）

| Token Name | 数值 | 典型用途 |
|-----------|------|---------|
| `space-1` | 4 pt | 微间距、图标内边距 |
| `space-2` | 8 pt | 行内元素间距、标签内边距 |
| `space-3` | 12 pt | 卡片之间 gap（估算值） |
| `space-4` | 16 pt | 标准水平 margin、卡片内 padding |
| `space-5` | 20 pt | 较大内容间距（估算值） |
| `space-6` | 24 pt | 段落/区块间距（估算值） |
| `space-8` | 32 pt | 大区块间距（估算值） |
| `space-10` | 40 pt | 底部 ScrollView padding |
| `space-12` | 48 pt | 导航栏高度（估算值） |
| `space-16` | 64 pt | 大间距（估算值） |

---

## Motion（动效建议）

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `duration-fast` | 150 ms | 按钮按下态、Chevron 旋转（估算值） |
| `duration-medium` | 250 ms | Toggle 切换、页面转场元素（估算值） |
| `duration-slow` | 400 ms | 页面进入/退出（估算值） |
| `delay-stagger` | 30–50 ms | 列表项逐项入场延迟（估算值） |
| `easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | 大部分过渡（Material Standard） |
| `easing-decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 进入动画 |
| `easing-accelerate` | `cubic-bezier(0.4, 0.0, 1, 1)` | 退出动画 |
| `spring-toggle` | `damping: 0.7, stiffness: 200` | Toggle 弹簧动效（估算值） |
| `spring-slider` | `damping: 0.8, stiffness: 150` | Slider Thumb 拖拽回弹（估算值） |
