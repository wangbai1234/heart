# 03 Design Tokens — 反馈组件三联

## Color Tokens

### 品牌色

| Token | Hex / Value | 用途 |
|-------|-------------|------|
| `color.brand.primary` | `#FFB7C5` | Cherry Pink — Toast 图标、按钮、Radio 选中态、数字徽章 |
| `color.brand.secondary` | `#A7C7E7` | Sky Blue — 备用（本资产未出现） |
| `color.brand.accent` | `#C8B6FF` | Lavender — 备用（本资产未出现） |

### 表面色

| Token | Hex / Value | 用途 |
|-------|-------------|------|
| `color.surface.cream` | `#FFF8F3` | 全局 cream 底色 |
| `color.surface.canvas` | `#FFF0F3` | 画布背景（浅樱花粉，略深于 cream） |
| `color.surface.white` | `#FFFFFF` | Toast 背景、Modal Card 背景、Sheet 背景 |
| `color.surface.input` | `#F5F5F5` | 输入栏背景（估算值） |

### 文字色

| Token | Hex / Value | 用途 |
|-------|-------------|------|
| `color.ink.primary` | `#3A3A4A` | 主文字（标题、按钮文字） |
| `color.ink.secondary` | `#888888` | 副标题、说明文字（估算值） |
| `color.ink.placeholder` | `#BBBBBB` | 输入框 Placeholder（估算值） |
| `color.ink.white` | `#FFFFFF` | 主按钮内文字（反色） |

### 遮罩色

| Token | Hex / Value | 用途 |
|-------|-------------|------|
| `color.scrim.modal` | `rgba(0, 0, 0, 0.45)` | Modal 背景遮罩（深） |
| `color.scrim.sheet` | `rgba(0, 0, 0, 0.25)` | Bottom Sheet 背景遮罩（浅） |

### 状态色

| Token | Hex / Value | 用途 |
|-------|-------------|------|
| `color.state.success` | `#FFB7C5` | Toast 成功图标背景（与品牌色统一，非绿色） |
| `color.state.destructive` | `#FFB7C5` | 破坏性 Modal 主按钮（温暖化处理，非红色） |

### 边框 / 描边色

| Token | Hex / Value | 用途 |
|-------|-------------|------|
| `color.border.subtle` | `rgba(0, 0, 0, 0.08)` | 卡片轻微描边（估算值） |
| `color.border.radio` | `#CCCCCC` | Radio 未选中状态描边（估算值） |
| `color.border.radio.active` | `#FFB7C5` | Radio 选中状态描边 |
| `color.border.cancel-btn` | `#E8E8E8` | 取消按钮描边（估算值） |

---

## Gradient Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `gradient.button.primary` | `linear-gradient(135deg, #FFB7C5 0%, #FF8FA3 100%)` | 主操作按钮（确认退出、完成）（估算值） |
| `gradient.background.chat` | `linear-gradient(180deg, #FFE4EC 0%, #FFF5F8 40%, #EEE8FF 100%)` | 聊天页背景（估算值，基于图像观察） |
| `gradient.phone.bg` | `linear-gradient(180deg, #FFD6E4 0%, #FFFFFF 50%, #E8E0FF 100%)` | 手机屏内渐变背景（估算值） |

---

## Border Radius Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `radius.toast` | `22px` | Toast 胶囊形（全圆角，高度一半）（估算值） |
| `radius.modal` | `20px` | Modal 卡片圆角（估算值） |
| `radius.sheet.top` | `20px` | Bottom Sheet 顶部圆角（估算值） |
| `radius.button.primary` | `24px` | 主操作按钮圆角（接近全圆角）（估算值） |
| `radius.button.secondary` | `24px` | 次操作按钮圆角（估算值） |
| `radius.avatar` | `50%` | Avatar 完整圆形 |
| `radius.radio` | `50%` | Radio 按钮圆形 |
| `radius.badge` | `50%` | 数字徽章圆形 |
| `radius.phone` | `40px` | 手机框架圆角（估算值） |

---

## Shadow Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `shadow.toast` | `0 4px 16px rgba(0, 0, 0, 0.10)` | Toast 轻柔阴影（估算值） |
| `shadow.modal` | `0 8px 32px rgba(0, 0, 0, 0.18)` | Modal 较明显投影（估算值） |
| `shadow.sheet` | `0 -4px 20px rgba(0, 0, 0, 0.10)` | Sheet 顶部阴影（向上投影，估算值） |
| `shadow.button` | `0 2px 8px rgba(255, 143, 163, 0.35)` | 粉色按钮光晕阴影（估算值） |

---

## Blur Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `blur.none` | `0px` | Modal Card、Sheet（不模糊背景，依赖 scrim） |
| `blur.glass` | `12px` | 如需玻璃态变体（本资产未直接显示，但属于 DNA） |

---

## Opacity Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `opacity.scrim.modal` | `0.45` | Modal scrim |
| `opacity.scrim.sheet` | `0.25` | Sheet scrim |
| `opacity.inactive` | `0.38` | 禁用状态（本资产未出现） |
| `opacity.placeholder` | `0.45` | 输入框 placeholder（估算值） |

---

## Typography Tokens

### 字体族

| Token | Value | 用途 |
|-------|-------|------|
| `font.family.cn` | `"PingFang SC", "HarmonyOS Sans SC", sans-serif` | 全部中文文字 |
| `font.family.en` | `"SF Pro Rounded", sans-serif` | 数字、英文 |

### 字号与行高

| Token | Size | Weight | Line Height | 用途 |
|-------|------|--------|-------------|------|
| `text.modal.title` | `20px` | `600` (SemiBold) | `1.3` | Modal 标题"确认退出登录？" |
| `text.modal.body` | `13px` | `400` (Regular) | `1.5` | Modal 副标说明文字 |
| `text.sheet.title` | `17px` | `600` (SemiBold) | `1.4` | Sheet 标题"选择主题" |
| `text.sheet.option` | `16px` | `400` (Regular) | `1.4` | Sheet Radio 选项文字 |
| `text.button.primary` | `16px` | `600` (SemiBold) | `1` | 主操作按钮文字 |
| `text.button.secondary` | `16px` | `400` (Regular) | `1` | 次操作按钮文字 |
| `text.toast` | `14px` | `400` (Regular) | `1.4` | Toast 通知文字 |
| `text.nav.title` | `16px` | `600` (SemiBold) | `1` | NavBar 名称（估算值） |
| `text.nav.subtitle` | `11px` | `400` (Regular) | `1` | NavBar 副标（估算值） |
| `text.status.time` | `15px` | `600` (SemiBold) | `1` | 状态栏时间"9:41" |
| `text.badge` | `14px` | `700` (Bold) | `1` | 底部标注徽章数字 |
| `text.annotation` | `13px` | `400` (Regular) | `1.4` | 底部标注说明文字 |
| `text.input.placeholder` | `14px` | `400` (Regular) | `1` | 输入框 placeholder（估算值） |

---

## Spacing Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `spacing.4` | `4px` | Drag Handle 高度 |
| `spacing.8` | `8px` | 小间距 |
| `spacing.12` | `12px` | Radio 选项间距（估算值） |
| `spacing.16` | `16px` | Toast 距 NavBar 距离、卡片内小 padding |
| `spacing.20` | `20px` | Radio 选项水平 padding |
| `spacing.24` | `24px` | Modal / Sheet 内容 padding（估算值） |
| `spacing.32` | `32px` | Modal 图标区域高度（估算值） |
| `spacing.36` | `36px` | Drag Handle 宽度、Avatar 尺寸 |
| `spacing.44` | `44px` | Toast 高度（估算值）、最小触摸目标 |
| `spacing.48` | `48px` | 主按钮高度（估算值）、画布 padding |
| `spacing.64` | `64px` | 手机间距（估算值） |

---

## Motion Tokens

| Token | Value | 用途 |
|-------|-------|------|
| `motion.duration.toast.in` | `300ms` | Toast 进入动画时长（估算值） |
| `motion.duration.toast.out` | `200ms` | Toast 退出动画时长（估算值） |
| `motion.duration.toast.hold` | `2500ms` | Toast 停留时长 |
| `motion.duration.modal.in` | `250ms` | Modal 进入动画时长（估算值） |
| `motion.duration.modal.out` | `200ms` | Modal 退出动画时长（估算值） |
| `motion.duration.sheet.in` | `350ms` | Sheet 滑入动画时长（估算值） |
| `motion.duration.sheet.out` | `300ms` | Sheet 滑出动画时长（估算值） |
| `motion.easing.enter` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 弹性进入曲线（spring feel） |
| `motion.easing.exit` | `cubic-bezier(0.25, 0.46, 0.45, 0.94)` | 缓出退出曲线 |
| `motion.easing.sheet` | `cubic-bezier(0.32, 0.72, 0, 1)` | iOS-style Sheet 弹出曲线 |
