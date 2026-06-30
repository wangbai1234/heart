# 03 Design Tokens — 加载 / 空状态

## Color Tokens

### 品牌色

| Token Name | Hex | 用途 |
|-----------|-----|------|
| `color.brand.cherry-pink` | `#FFB7C5` | Pill 图标、麦克风按钮、主要强调色 |
| `color.brand.sky-blue` | `#A7C7E7` | 插画宝石高光冷色区域 |
| `color.brand.lavender` | `#C8B6FF` | 宝石心形主色调、AI 打点动画（估算） |
| `color.brand.cream` | `#FFF8F3` | 品牌 Surface 基准 |

### 背景色

| Token Name | Hex | 用途 |
|-----------|-----|------|
| `color.bg.page` | `#FDF0EE`（估算） | 整页背景色，玫瑰米白 |
| `color.bg.skeleton` | `#F2D0D8`（估算） | 骨架气泡矩形底色 |
| `color.bg.skeleton-avatar` | `#F2C8D0`（估算） | 骨架头像占位圆底色 |

### 文字色

| Token Name | Hex | 用途 |
|-----------|-----|------|
| `color.text.primary` | `#3A3A4A` | 角色名、时间、引导文字 |
| `color.text.secondary` | `#A07888`（估算） | 副标题"在线 · 愿意倾听你的一切"、Pill 文字 |
| `color.text.placeholder` | `#C8B6C8`（估算） | 输入框占位文字 |

### 图标色

| Token Name | Hex | 用途 |
|-----------|-----|------|
| `color.icon.default` | `#8A8A9A`（估算） | 返回箭头、电话图标、更多菜单"···"、状态栏图标 |
| `color.icon.brand-pink` | `#FFB7C5` | Pill 笑脸图标、Pill 对话图标、麦克风图标 |
| `color.icon.gold` | `#E8C84A`（估算） | Pill 五角星图标（"给我讲个故事"） |

### Shimmer 动画专用色

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `color.shimmer.base` | `#F2D0D8`（估算） | 骨架底色 |
| `color.shimmer.highlight` | `rgba(255,255,255,0.60)`（估算） | 扫光高亮层 |

---

## Gradient Tokens

### 插画区云朵背景渐变

| Token Name | 值 |
|-----------|-----|
| `gradient.illustration.cloud` | `radial-gradient(ellipse 600px 280px at 50% 60%, rgba(255,183,197,0.60) 0%, rgba(200,182,255,0.40) 40%, rgba(255,248,243,0.00) 100%)` （估算值） |

### 心形宝石渐变（多层叠加）

| Token Name | 值 |
|-----------|-----|
| `gradient.gem.heart-primary` | 粉紫到透明蓝，具体值为插画资产，无法精确提取，参考色：`#F9A8D4` → `#C084FC` → `#93C5FD`（估算） |

### 骨架 Shimmer 渐变

| Token Name | 值 |
|-----------|-----|
| `gradient.shimmer.sweep` | `linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.60) 50%, transparent 100%)` （估算） |

---

## Border Radius Tokens

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `radius.avatar` | `50%` | 角色头像、骨架头像占位圆 |
| `radius.pill` | `32px`（估算） | 建议 Pill 完整圆角胶囊 |
| `radius.bubble` | `20px`（估算） | 对话气泡（正常态） |
| `radius.skeleton-bubble` | `16px`（估算） | 骨架矩形圆角 |
| `radius.input-bar` | `32px`（估算） | 底部输入栏容器 |
| `radius.icon-btn` | `50%` | "+" 按钮、麦克风按钮 |

---

## Shadow Tokens

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `shadow.avatar` | `0 2px 8px rgba(0,0,0,0.10)`（估算） | 角色头像投影 |
| `shadow.pill` | `0 2px 8px rgba(255,183,197,0.25)`（估算） | 建议 Pill 悬浮感 |
| `shadow.gem-heart` | `0 8px 32px rgba(200,182,255,0.50)`（估算） | 心形宝石插画光晕 |

---

## Blur Tokens

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `blur.glass-surface` | `12px`（估算） | 如有玻璃磨砂背景层（本设计中 Header/Input 未见明显 blur，暂标注） |
| `blur.cloud-glow` | `24px`（估算） | 云朵插画背景柔化 |

---

## Opacity Tokens

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `opacity.skeleton` | `1.0` | 骨架矩形不透明 |
| `opacity.cloud-bg` | `0.60`（估算） | 云朵背景渐变层透明度 |
| `opacity.shimmer-highlight` | `0.60`（估算） | Shimmer 扫光高亮透明度 |
| `opacity.placeholder-text` | `0.55`（估算） | 输入框占位文字 |

---

## Typography Tokens

### 字体族

| Token Name | 值 |
|-----------|-----|
| `font.family.cn` | `PingFang SC, HarmonyOS Sans SC, sans-serif` |
| `font.family.latin` | `SF Pro Rounded, system-ui, sans-serif` |

### 字号

| Token Name | pt 值 | px 值（@2.625×） | 用途 |
|-----------|--------|-----------------|------|
| `font.size.status-time` | `~16pt` | `~42px` | 状态栏时间"9:41" |
| `font.size.character-name` | `~17pt` | `~45px` | 角色名"悠悠" |
| `font.size.character-sub` | `~12pt` | `~32px` | 副标题/状态文字 |
| `font.size.guide-text` | `~18pt` | `~47px` | 引导文"我们刚认识，先聊点什么吧？"（估算） |
| `font.size.pill-label` | `~14pt` | `~37px` | Pill 按钮文字（估算） |
| `font.size.input-placeholder` | `~15pt` | `~39px` | 输入占位文字（估算） |

### 字重

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `font.weight.regular` | `400` | 副标题、Pill 文字、占位文字 |
| `font.weight.medium` | `500` | 引导文字 |
| `font.weight.semibold` | `600` | 角色名、状态栏时间 |

### 行高

| Token Name | 值 |
|-----------|-----|
| `font.line-height.tight` | `1.2` |
| `font.line-height.normal` | `1.4` |
| `font.line-height.loose` | `1.6` |

---

## Spacing Tokens

| Token Name | pt 值 | px 值（估算@设计稿） | 用途 |
|-----------|--------|-----------------|------|
| `spacing.xs` | `4pt` | `~10px` | 细间距 |
| `spacing.sm` | `8pt` | `~21px` | 小间距 |
| `spacing.md` | `16pt` | `~42px` | 标准间距（头像-名字间距等） |
| `spacing.lg` | `24pt` | `~63px` | 大间距（Pill 行 Padding）|
| `spacing.xl` | `32pt` | `~84px` | 超大间距（区块间距）|
| `spacing.page-h` | `20pt` | `~52px` | 页面水平 Padding（估算）|
| `spacing.header-v` | `12pt` | `~32px` | Header 垂直 Padding（估算）|

---

## Motion Tokens

| Token Name | 值 | 用途 |
|-----------|-----|------|
| `motion.duration.shimmer` | `1400ms` | Shimmer 一次扫光周期（估算） |
| `motion.duration.dot-typing` | `600ms` | "..."每个点出现的间隔（估算） |
| `motion.duration.fade-in` | `300ms` | 骨架消失 → 真实气泡淡入（估算） |
| `motion.duration.pulse` | `2000ms` | 心形宝石轻微浮动/呼吸周期（估算） |
| `motion.easing.default` | `cubic-bezier(0.25, 0.46, 0.45, 0.94)` | 标准缓动 ease-out |
| `motion.easing.spring` | `cubic-bezier(0.34, 1.56, 0.64, 1.00)` | 弹性缓动（Pill 点击反馈）|
| `motion.easing.linear` | `linear` | Shimmer 扫光均匀移动 |
| `motion.repeat.shimmer` | `infinite` | 循环 |
| `motion.repeat.dot-typing` | `infinite` | 循环 |
| `motion.repeat.pulse` | `infinite` | 循环 |
