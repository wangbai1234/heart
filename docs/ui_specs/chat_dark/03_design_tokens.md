# 03 Design Tokens — 聊天页 Chat（深色模式）

## Color

### 基础色板

| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-primary` | `#FFB7C5` | 樱花粉，发送按钮、AI输入中气泡圆点、强调色 |
| `color-primary-dark` | `#E8A0B0` | 粉色按压态 |
| `color-secondary` | `#A7C7E7` | 天蓝，在线状态圆点 |
| `color-accent` | `#C8B6FF` | 薰衣草紫，装饰光点、波形渐变 |
| `color-accent-deep` | `#9B8EC4` | 深紫，部分装饰元素 |

### 背景色

| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-bg-page` | `#1B1923` | 页面主背景（深紫星云底色） |
| `color-bg-nebula` | `#221B32` | 星云纹理叠加色 |
| `color-bg-cloud` | `rgba(80,50,120,0.25)` | 背景云雾装饰层 |
| `color-surface-dark` | `rgba(30,27,40,0.85)` | Header/Input Bar 毛玻璃底色 |
| `color-surface-bubble-ai` | `rgba(45,40,65,0.90)` | AI 消息气泡背景 |
| `color-surface-bubble-user` | `#3B5BDB` 至 `#2F4AC5` 渐变 | 用户消息气泡（靛蓝渐变） |
| `color-surface-typing` | `rgba(45,40,65,0.80)` | AI"输入中"气泡背景 |
| `color-surface-input` | `rgba(255,255,255,0.08)` | 输入框背景 |
| `color-surface-plus-btn` | `rgba(255,255,255,0.12)` | "+"按钮背景 |

### Glass / 毛玻璃

| Token Name | RGBA | 用途 |
|------------|------|------|
| `color-glass-header` | `rgba(30,27,40,0.75)` | 顶部导航栏毛玻璃层 |
| `color-glass-input-bar` | `rgba(30,27,40,0.80)` | 底部输入栏毛玻璃层 |
| `color-glass-border` | `rgba(255,255,255,0.10)` | 毛玻璃元素边框 |

### 边框 / 分隔线

| Token Name | RGBA | 用途 |
|------------|------|------|
| `color-border-bubble-ai` | `rgba(255,160,200,0.18)` | AI 气泡粉色边缘光边框 |
| `color-border-glass` | `rgba(255,255,255,0.10)` | 玻璃组件通用边框 |
| `color-divider` | `rgba(255,255,255,0.08)` | 分隔线（如有） |

### 文字色

| Token Name | Hex / RGBA | 用途 |
|------------|------------|------|
| `color-text-primary` | `#FFFFFF` | 主要文字（角色名、消息正文） |
| `color-text-secondary` | `rgba(255,255,255,0.70)` | 次要文字（状态文字、副标题） |
| `color-text-caption` | `rgba(255,255,255,0.45)` | 辅助文字（时间戳、AI 朗读提示） |
| `color-text-placeholder` | `rgba(255,255,255,0.40)` | 输入框占位文字 |
| `color-text-user-bubble` | `#FFFFFF` | 用户气泡内文字 |
| `color-text-ai-bubble` | `#F0EEFF` | AI 气泡内文字（略带蓝紫色调） |

### 特殊功能色

| Token Name | Hex | 用途 |
|------------|-----|------|
| `color-online-dot` | `#7EB8F7` | 在线状态指示点（蓝色） |
| `color-send-btn` | `#FFB7C5` | 发送按钮背景粉色 |
| `color-play-btn-bg` | `rgba(255,183,197,0.25)` | 播放按钮外圆圈 |
| `color-play-icon` | `#FFB7C5` | 播放三角形图标色 |

### 系统状态色

| Token Name | Hex | 用途 |
|------------|-----|------|
| `color-success` | `#7BE89E` | 成功状态（深色模式适配） |
| `color-warning` | `#FFD580` | 警告状态 |
| `color-danger` | `#FF7A7A` | 错误/危险状态 |
| `color-info` | `#7EB8F7` | 信息状态 |

### Overlay

| Token Name | RGBA | 用途 |
|------------|------|------|
| `color-overlay-dark` | `rgba(0,0,0,0.50)` | 弹出层遮罩 |
| `color-overlay-light` | `rgba(27,25,35,0.60)` | 内容区半透明遮罩 |

---

## Gradient

### AI 消息气泡边缘光（Edge Glow）
- 类型：Border Glow / Box Shadow
- 颜色：从 `rgba(255,160,190,0.30)` → 透明
- 方向：全周边（类似发光边框）
- 用途：AI 气泡的粉色光晕效果

### 用户消息气泡渐变
- 类型：Linear Gradient
- 起点颜色：`#3B5BDB`（靛蓝）
- 终点颜色：`#2F4AC5`（深靛蓝）
- 方向：135deg（左上到右下）
- 用途：用户发送的消息气泡背景

### 页面背景渐变
- 类型：Radial Gradient + Texture
- 主色：`#1B1923`
- 叠加：`#221B32` 云雾纹理层
- 效果：深色星云，边缘有紫色云雾装饰

### 语音波形渐变
- 类型：Linear Gradient（水平方向）
- 颜色范围：`#FFB7C5`（粉色）→ `#C8B6FF`（薰衣草）→ `#A7C7E7`（天蓝）
- 方向：0deg（左到右）
- 用途：语音消息波形图颜色

### 发送按钮背景
- 类型：Solid / Radial Gradient
- 颜色：`#FFB7C5` 为主，可能带轻微高光
- 用途：发送按钮圆形背景

---

## Radius

| Token Name | 值 | 使用场景 |
|------------|---|---------|
| `radius-xs` | 8 px | 极小元素圆角 |
| `radius-sm` | 12 px | 小型图标按钮 |
| `radius-md` | 16 px | 状态点、小按钮 |
| `radius-lg` | 24 px | 输入框 |
| `radius-xl` | 32 px | 消息气泡、Header 底角 |
| `radius-2xl` | 40 px | 输入栏整体、语音气泡 |
| `radius-full` | 9999 px | 头像（圆形）、在线状态点、发送按钮、"+"按钮 |

#### 各组件圆角
- AI 文字气泡：`radius-xl` 32 px（所有角），左下角为尖角约 8 px（估算值）
- 用户文字气泡：`radius-xl` 32 px（所有角），右下角为尖角约 8 px（估算值）
- 语音消息气泡：`radius-xl` 32 px（估算值）
- "输入中"气泡：`radius-xl` 32 px（估算值）
- Header Bar：顶部无圆角，底部 `radius-2xl` 32 px（估算值）
- 输入栏容器：`radius-2xl` 40 px（估算值）
- 输入框内部：`radius-full`（全胶囊形）
- 发送按钮：`radius-full`（完整圆形）
- "+"按钮：`radius-full`（完整圆形）
- 头像：`radius-full`（完整圆形）

---

## Shadow

| Token Name | 颜色 | 透明度 | Blur | Offset X | Offset Y | Spread | 使用场景 |
|------------|------|--------|------|----------|----------|--------|---------|
| `shadow-bubble-ai` | `#FFB7C5` | 0.25 | 20 px | 0 | 0 | 0 | AI 气泡粉色光晕 |
| `shadow-bubble-ai-inner` | `#E090B0` | 0.15 | 8 px | 0 | 2 px | -2 px | AI 气泡内边框光 |
| `shadow-send-btn` | `#FFB7C5` | 0.40 | 16 px | 0 | 4 px | 0 | 发送按钮粉色辉光 |
| `shadow-header` | `#000000` | 0.20 | 12 px | 0 | 4 px | 0 | Header 底部投影 |
| `shadow-voice-bubble` | `#FFB7C5` | 0.20 | 24 px | 0 | 0 | 0 | 语音气泡粉色辉光 |

---

## Blur

| Token Name | 值 | 使用场景 |
|------------|---|---------|
| `blur-glass-sm` | 12 px | 轻度毛玻璃（辅助元素） |
| `blur-glass-md` | 20 px | 标准毛玻璃（Header、Input Bar） |
| `blur-glass-lg` | 32 px | 强毛玻璃（弹出层） |
| `blur-bg-decoration` | 40 px | 背景云雾装饰模糊 |

---

## Opacity

| Token Name | 值 | 使用场景 |
|------------|---|---------|
| `opacity-glass-header` | 0.75 | Header 毛玻璃透明度 |
| `opacity-glass-input` | 0.80 | Input Bar 毛玻璃透明度 |
| `opacity-bubble-ai` | 0.90 | AI 气泡背景透明度 |
| `opacity-text-secondary` | 0.70 | 次要文字 |
| `opacity-text-caption` | 0.45 | 辅助文字/时间戳 |
| `opacity-text-placeholder` | 0.40 | 占位文字 |
| `opacity-border-glass` | 0.10 | 玻璃边框 |
| `opacity-cloud-decoration` | 0.25 | 背景云雾装饰 |
| `opacity-home-indicator` | 0.30 | 底部 Home Indicator |

---

## Typography

| Token Name | 字体族 | 字号 | 字重 | 行高 | 字间距 | 颜色 Token | 用途 |
|------------|--------|------|------|------|--------|------------|------|
| `type-title-lg` | PingFang SC | ~32 px（估算）| SemiBold / 600 | 1.3 | 0 | `color-text-primary` | 角色名"小屿" |
| `type-body-lg` | PingFang SC | ~28 px（估算）| Regular / 400 | 1.5 | 0 | `color-text-ai-bubble` | AI 消息正文 |
| `type-body-md` | PingFang SC | ~28 px（估算）| Regular / 400 | 1.5 | 0 | `color-text-user-bubble` | 用户消息正文 |
| `type-caption` | PingFang SC | ~22 px（估算）| Regular / 400 | 1.4 | 0 | `color-text-caption` | 时间戳、AI 朗读提示 |
| `type-status` | PingFang SC | ~22 px（估算）| Regular / 400 | 1.2 | 0 | `color-text-secondary` | "温柔在线"状态文字 |
| `type-tabular` | SF Pro Rounded | ~26 px（估算）| Regular / 400 | 1.0 | 0 | `color-text-caption` | 语音时长"0:18" |
| `type-system` | SF Pro Rounded | ~24 px（估算）| Semibold / 600 | 1.0 | 0 | `color-text-primary` | 状态栏时间"9:41" |
| `type-placeholder` | PingFang SC | ~28 px（估算）| Regular / 400 | 1.0 | 0 | `color-text-placeholder` | 输入框占位文字 |

---

## Spacing Scale

| Token Name | 值 | 用途 |
|------------|---|------|
| `space-1` | 4 px | 极小间距（圆点与文字） |
| `space-2` | 8 px | 紧密间距（状态点与文字） |
| `space-3` | 12 px | 小间距（气泡尾角） |
| `space-4` | 16 px | 基础间距（Input Bar 元素间距） |
| `space-5` | 20 px | 中等间距 |
| `space-6` | 24 px | 消息间距、气泡内边距垂直 |
| `space-7` | 28 px | — |
| `space-8` | 32 px | 页面边距、气泡内边距水平 |
| `space-10` | 40 px | Header 左右内边距 |
| `space-12` | 48 px | 大间距 |
| `space-16` | 64 px | 超大间距（Header 与消息区） |

---

## Motion

| Token Name | 值 | 用途 |
|------------|---|------|
| `duration-fast` | 150ms | 按钮点击反馈 |
| `duration-normal` | 250ms | 标准过渡（气泡出现、状态变化） |
| `duration-slow` | 400ms | 页面转场、复杂动画 |
| `duration-extra-slow` | 600ms | 入场动画 |
| `delay-stagger` | 50ms | 消息气泡逐条出现的交错延迟 |
| `easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | 标准缓动（Material Motion） |
| `easing-decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 减速进入（元素从外滑入） |
| `easing-accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | 加速退出（元素滑出） |
| `spring-bounce` | `spring(stiffness: 300, damping: 25)` | 气泡弹入动效（推荐值） |
| `typing-dot-duration` | 800ms loop | "···"输入中动效循环时长 |
