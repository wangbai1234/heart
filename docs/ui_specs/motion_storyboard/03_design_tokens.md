# 03 Design Tokens

## 颜色体系（Color）

### 主色 / 品牌色

| Token | 值 | 用途 |
|-------|----|------|
| `color.primary` | `#FFB7C5` | Cherry Pink，用户气泡背景、+ 按钮、序号圆圈、语音波粉色点 |
| `color.secondary` | `#A7C7E7` | Sky Blue，情绪球渐变色之一 |
| `color.accent` | `#C8B6FF` | Lavender，语音波紫色渐变端、情绪球渐变色之一 |

### 背景 / 表面

| Token | 值 | 用途 |
|-------|----|------|
| `color.surface` | `#FFF8F3` | 奶白，画布背景色、屏幕背景 |
| `color.surface.chat` | `#FFF5F5`（估算值） | 聊天消息列表背景（极浅粉） |
| `color.glass` | `rgba(255,255,255,0.55)` | 毛玻璃表面，输入栏背景 |
| `color.glass.bubble.ai` | `rgba(255,255,255,0.85)`（估算值） | AI 消息气泡背景 |

### 文字颜色

| Token | 值 | 用途 |
|-------|----|------|
| `color.text.primary` | `#3A3A4A` | Ink，主文字（动效标题、消息正文） |
| `color.text.secondary` | `#6B6B7A`（估算值） | 副文字（描述说明文字） |
| `color.text.timestamp` | `#AAAAAA`（估算值） | 时间戳文字 |
| `color.text.placeholder` | `#BBBBCC`（估算值） | 输入框占位文字 |
| `color.text.online` | `#7DCE7D`（估算值） | "在线"绿色状态文字 |

### 气泡颜色

| Token | 值 | 用途 |
|-------|----|------|
| `color.bubble.user.bg` | `#FFD6DF`（估算值，较 primary 浅） | 用户消息气泡背景 |
| `color.bubble.ai.bg` | `rgba(255,255,255,0.90)`（估算值） | AI 消息气泡背景（白色） |
| `color.bubble.new.glow` | `rgba(255,183,197,0.35)`（估算值） | 新气泡绽放时的粉色光晕 |

### 分割线 / 边框

| Token | 值 | 用途 |
|-------|----|------|
| `color.divider` | `rgba(0,0,0,0.06)`（估算值） | 输入栏上方分割线 |
| `color.border.device` | `#FFFFFF` | 设备框边框白色 |

### 语义色

| Token | 值 | 用途 |
|-------|----|------|
| `color.semantic.online` | `#7DCE7D`（估算值） | 在线状态 |
| `color.semantic.read` | `#FFB7C5` | 已读回执 ✓ |

---

## 渐变体系（Gradient）

### 情绪球渐变（Emotion Orb）

| 属性 | 值 |
|------|----|
| 类型 | 径向渐变 + 线性渐变叠加 |
| 中心色 | `rgba(255,255,255,0.95)`（白色高光核心） |
| 中间色 | `#A7C7E7`（Sky Blue）/ `#C8B6FF`（Lavender） |
| 边缘色 | `#FFB7C5`（Cherry Pink） |
| 整体形态 | 球形，带柔和外发光 |
| 用途 | Header 中央情绪球（脉冲动效） |

### 气泡绽放光晕渐变

| 属性 | 值 |
|------|----|
| 类型 | 径向渐变 |
| 中心色 | `rgba(255,183,197,0.5)`（估算值） |
| 边缘色 | `rgba(255,183,197,0)` |
| 用途 | 新消息气泡出现时的外发光 |

### 语音波颜色渐变

| 属性 | 值 |
|------|----|
| 起点色 | `#FFB7C5`（Cherry Pink） |
| 终点色 | `#C8B6FF`（Lavender） |
| 方向 | 从左到右（水平） |
| 用途 | 5 个语音波点的颜色分布 |

---

## 圆角体系（Border Radius）

| Token | 值 | 用途 |
|-------|----|------|
| `radius.xs` | `8px`（估算值） | 小组件内部 |
| `radius.sm` | `12px`（估算值） | 小卡片、图标容器 |
| `radius.md` | `16px`（估算值） | AI 消息气泡 |
| `radius.lg` | `20px`（估算值） | 用户消息气泡、输入框 |
| `radius.xl` | `24px`（估算值） | 输入栏整体容器 |
| `radius.full` | `9999px` | 头像、圆形按钮、序号圆圈、情绪球 |
| `radius.device` | `47px`（估算值） | iPhone 14 设备框 |

---

## 阴影体系（Shadow）

| Token | 颜色 | 透明度 | Blur | Offset Y | Spread | 用途 |
|-------|------|--------|------|----------|--------|------|
| `shadow.bubble.ai` | `#000000` | 0.05（估算值） | 8px | 2px | 0 | AI 气泡投影 |
| `shadow.bubble.user` | `#FFB7C5` | 0.20（估算值） | 12px | 2px | -2px | 用户粉色气泡投影 |
| `shadow.orb` | `#C8B6FF` | 0.35（估算值） | 20px | 0 | 0 | 情绪球外发光 |
| `shadow.button.plus` | `#FFB7C5` | 0.40（估算值） | 8px | 2px | 0 | + 按钮投影 |
| `shadow.device` | `#000000` | 0.10（估算值） | 24px | 4px | 0 | 设备框整体投影 |

---

## 毛玻璃 / 模糊（Blur）

| Token | 值 | 用途 |
|-------|----|------|
| `blur.glass.sm` | `8px` | 输入栏背景轻度模糊 |
| `blur.glass.md` | `16px`（估算值） | AI 气泡轻微模糊 |
| `blur.glass.lg` | `24px`（估算值） | 情绪球背景模糊 |
| `blur.page.transition` | `背景降亮度，无显式 blur` | 页面过渡底层（brightness 0.92） |

---

## 透明度（Opacity）

| Token | 值 | 用途 |
|-------|----|------|
| `opacity.full` | `1.0` | 正常状态 |
| `opacity.page.behind` | `0.92` | 页面过渡时底层页面亮度 |
| `opacity.bubble.enter.start` | `0` | 气泡绽放进入起始 |
| `opacity.bubble.enter.end` | `1.0` | 气泡绽放进入结束 |
| `opacity.glass.surface` | `0.55` | 毛玻璃表面透明度 |

---

## 字体排版（Typography）

### 字体家族

| 场景 | 字体 |
|------|------|
| 中文正文 | PingFang SC / HarmonyOS Sans SC |
| 数字 / 拉丁字母 | SF Pro Rounded |
| 标题（yuoyuo logo） | SF Pro Rounded，Medium |

### 字号层级

| Token | 字号 | 字重 | 行高 | 用途 |
|-------|------|------|------|------|
| `type.display` | 28px（估算） | Medium | 1.3 | 画布标题 `yuoyuo · Motion` |
| `type.section.title` | 16px（估算） | Semibold | 1.4 | 动效名称标题 |
| `type.body` | 14px（估算） | Regular | 1.6 | 消息气泡正文 |
| `type.body.sm` | 13px（估算） | Regular | 1.5 | 动效描述说明文字 |
| `type.caption` | 11px（估算） | Regular | 1.3 | 时间戳文字 |
| `type.status` | 11px（估算） | Regular | 1.2 | 导航栏"在线"状态 |
| `type.placeholder` | 14px（估算） | Regular | 1.4 | 输入框占位文字 |
| `type.nav.title` | 15px（估算） | Semibold | 1.3 | 导航栏昵称 |

---

## 间距刻度（Spacing Scale）

| Token | 值 |
|-------|----|
| `spacing.1` | 4px |
| `spacing.2` | 8px |
| `spacing.3` | 12px |
| `spacing.4` | 16px |
| `spacing.5` | 20px |
| `spacing.6` | 24px |
| `spacing.8` | 32px |
| `spacing.10` | 40px |

---

## 动效参数（Motion Tokens）

### 持续时间（Duration）

| Token | 值 | 用途 |
|-------|----|------|
| `motion.duration.bubble.bloom` | `300ms` | 气泡绽放完整动效 |
| `motion.duration.bubble.glow` | `150ms` | 气泡伴随粉色光晕淡出 |
| `motion.duration.orb.pulse` | `1200ms` | 情绪球单次脉冲周期 |
| `motion.duration.page.transition` | `400ms` | 页面过渡（Sheet 滑入） |
| `motion.duration.voice.wave` | `实时（N/A）` | 语音波实时驱动，无固定时长 |

### 延迟（Delay）

| Token | 值 | 用途 |
|-------|----|------|
| `motion.delay.bubble.glow` | `0ms` | 光晕与气泡同时开始 |
| `motion.delay.orb.loop` | `0ms` | 情绪球进入即循环 |

### 缓动曲线（Easing）

| Token | 曲线 | 用途 |
|-------|------|------|
| `motion.easing.bubble.bloom` | `ease-out` / `cubic-bezier(0.34,1.56,0.64,1)`（弹性缓出） | 气泡从 0.92→1.0 弹出感 |
| `motion.easing.orb.pulse` | `ease-in-out` | 情绪球呼吸感缓动 |
| `motion.easing.page.transition` | `ease-in-out` / Apple Spring | 页面过渡自然感 |
| `motion.easing.voice.wave` | `linear`（实时映射） | 语音波跟随音频振幅 |

### 弹性参数（Spring，情绪球脉冲）

| Token | 值 |
|-------|----|
| `motion.spring.stiffness` | 150（估算值） |
| `motion.spring.damping` | 12（估算值） |
| `motion.spring.mass` | 1 |

### 变换参数（Transform）

| 动效 | 属性 | 起始值 | 结束值 |
|------|------|--------|--------|
| 气泡绽放 | scale | 0.92 | 1.0 |
| 气泡绽放 | opacity | 0 | 1.0 |
| 气泡绽放（光晕） | opacity | 0.5→0（估算） | — |
| 情绪球脉冲 | scale | 1.0 | 1.06 → 1.0（往复） |
| 情绪球脉冲 | 光晕 opacity | 强→弱→强（循环） | — |
| 页面过渡（底层） | translateY | 0 | 8px（向下压） |
| 页面过渡（底层） | scale | 1.0 | 0.99 |
| 页面过渡（底层） | brightness | 1.0 | 0.92 |
| 页面过渡（顶层） | translateY | 100%（屏幕底） | 0（顶部） |
| 语音波 | 点高度/振幅 | 基准高度 | 随音频实时变化 |
