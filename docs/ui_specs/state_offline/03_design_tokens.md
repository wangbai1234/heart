# 03 Design Tokens — 离线降级状态页

## Color Tokens

### 品牌色
| Token | HEX / RGBA | 用途 |
|-------|-----------|------|
| `color.primary` | `#FFB7C5` | 时钟角标按钮背景、云朵图标粉色、重试按钮边框与文字、用户气泡渐变起点 |
| `color.secondary` | `#A7C7E7` | 双勾「✓✓」颜色、已读状态指示 |
| `color.accent` | `#C8B6FF` | （当前页未见直接使用，作为全局 token 保留） |
| `color.surface` | `#FFF8F3` | 页面背景渐变终点（奶油白） |
| `color.ink` | `#3A3A4A` | 所有正文消息文字颜色 |

### 背景色
| Token | HEX / RGBA | 用途 |
|-------|-----------|------|
| `color.bg.page-top` | `#FFF0F0` | 页面顶部背景（浅粉）（估算值） |
| `color.bg.page-bottom` | `#FFF8F3` | 页面底部背景（奶油白） |
| `color.bg.banner` | `rgba(255,255,255,0.85)` | 离线横幅背景，半透明白 |
| `color.bg.bubble.ai` | `rgba(255,255,255,0.90)` | AI 消息气泡背景 |
| `color.bg.bubble.user.from` | `#FFE4EC` | 用户气泡渐变起点（粉） |
| `color.bg.bubble.user.to` | `#FFDDE8` | 用户气泡渐变终点（浅粉）（估算值） |
| `color.bg.composer` | `rgba(255,255,255,0.80)` | Composer 背景，毛玻璃底色 |
| `color.bg.input` | `rgba(255,255,255,0.60)` | 输入框背景 |
| `color.bg.clock-btn` | `#FFB7C5` | 时钟角标按钮实色填充 |

### 文字色
| Token | HEX / RGBA | 用途 |
|-------|-----------|------|
| `color.text.primary` | `#3A3A4A` | 消息正文、横幅文字 |
| `color.text.secondary` | `#A0A0B0` | Nav 副标题「离线 · 消息将自动发送」（估算值） |
| `color.text.muted` | `#ACACAC` | 时间戳 |
| `color.text.staged` | `#C0A0A0` | 暂存分割线两行文字（暖灰粉）（估算值） |
| `color.text.placeholder` | `#C0C0C8` | Composer 输入框 Placeholder（估算值） |
| `color.text.retry` | `#FFB7C5` | 「重试」按钮文字色 |

### 图标色
| Token | HEX / RGBA | 用途 |
|-------|-----------|------|
| `color.icon.nav` | `#3A3A4A` | 电话、更多图标颜色（暗色） |
| `color.icon.add-btn` | `#A0A0A8` | `+` 按钮图标色（灰） |
| `color.icon.clock` | `#FFFFFF` | 时钟图标（白色，在粉色圆形上） |
| `color.icon.cloud` | `#FFB7C5` | 横幅云朵图标 |

### 边框 / 分隔线
| Token | HEX / RGBA | 用途 |
|-------|-----------|------|
| `color.border.retry-btn` | `#FFB7C5` | 「重试」按钮边框 |
| `color.border.add-btn` | `#D0D0D0` | `+` 按钮边框圆圈（估算值） |
| `color.border.composer-top` | `rgba(0,0,0,0.08)` | Composer 顶部分隔线 |

---

## Gradient Tokens
| Token | 定义 | 用途 |
|-------|------|------|
| `gradient.bg.page` | `linear-gradient(180deg, #FFF0F0 0%, #FFF8F3 100%)` | 全页背景 |
| `gradient.bubble.user` | `linear-gradient(135deg, #FFE4EC 0%, #FFDDE8 100%)` | 用户消息气泡（估算值） |

---

## Border Radius Tokens
| Token | 值 | 用途 |
|-------|-----|------|
| `radius.banner` | `16 pt` | 离线横幅 |
| `radius.retry-btn` | `16 pt`（pill） | 「重试」按钮，高度一半 |
| `radius.bubble.ai.tl` | `4 pt` | AI 气泡左上角（尖角感） |
| `radius.bubble.ai.tr` | `16 pt` | AI 气泡右上角 |
| `radius.bubble.ai.br` | `16 pt` | AI 气泡右下角 |
| `radius.bubble.ai.bl` | `16 pt` | AI 气泡左下角 |
| `radius.bubble.user.tl` | `16 pt` | 用户气泡左上角 |
| `radius.bubble.user.tr` | `4 pt` | 用户气泡右上角（尖角感） |
| `radius.bubble.user.br` | `16 pt` | 用户气泡右下角 |
| `radius.bubble.user.bl` | `16 pt` | 用户气泡左下角 |
| `radius.avatar` | `50%`（圆形） | 头像图片 |
| `radius.clock-btn` | `50%`（圆形） | 时钟角标按钮 |
| `radius.add-btn` | `50%`（圆形） | `+` 按钮 |
| `radius.input` | `18 pt`（pill） | 输入框 |

---

## Shadow Tokens
| Token | 值 | 用途 |
|-------|-----|------|
| `shadow.banner` | `0 2pt 8pt rgba(0,0,0,0.06)` | 离线横幅投影（轻柔浮起） |
| `shadow.bubble.ai` | `0 1pt 4pt rgba(0,0,0,0.05)` | AI 气泡轻投影（估算值） |
| `shadow.clock-btn` | `0 2pt 6pt rgba(255,183,197,0.40)` | 时钟按钮粉色发光投影（估算值） |

---

## Blur Tokens
| Token | 值 | 用途 |
|-------|-----|------|
| `blur.banner` | `backdrop-filter: blur(8pt)` | 横幅毛玻璃效果 |
| `blur.composer` | `backdrop-filter: blur(8pt)` | Composer 底部毛玻璃 |

---

## Opacity Tokens
| Token | 值 | 用途 |
|-------|-----|------|
| `opacity.history-dimmed` | `0.92` | 历史消息区整体暗淡（离线状态） |
| `opacity.banner-bg` | `0.85` | 横幅背景透明度 |
| `opacity.composer-bg` | `0.80` | Composer 背景透明度 |
| `opacity.input-bg` | `0.60` | 输入框背景透明度 |

---

## Typography Tokens

### 字体家族
| Token | 值 |
|-------|-----|
| `font.family.chinese` | `PingFang SC, HarmonyOS Sans SC, sans-serif` |
| `font.family.latin` | `SF Pro Rounded, system-ui, sans-serif` |

### 字号 / 字重
| Token | 字号 | 字重 | 行高 | 用途 |
|-------|------|------|------|------|
| `type.nav-title` | `17 pt` | `600 (SemiBold)` | `22 pt` | Nav 主标题「悠悠」 |
| `type.nav-subtitle` | `12 pt` | `400 (Regular)` | `16 pt` | Nav 副标题「离线 · 消息将自动发送」 |
| `type.banner-text` | `14 pt` | `400 (Regular)` | `20 pt` | 横幅说明文字 |
| `type.retry-btn` | `13 pt` | `500 (Medium)` | `18 pt` | 「重试」按钮文字 |
| `type.timestamp` | `12 pt` | `400 (Regular)` | `16 pt` | 时间戳 |
| `type.bubble-text` | `15 pt` | `400 (Regular)` | `22 pt` | 消息气泡正文 |
| `type.staged-label` | `13 pt` | `400 (Regular)` | `18 pt` | 暂存分割线第一行 |
| `type.staged-sub` | `12 pt` | `400 (Regular)` | `16 pt` | 暂存分割线第二行 |
| `type.placeholder` | `15 pt` | `400 (Regular)` | `22 pt` | 输入框 Placeholder |
| `type.status-bar` | `15 pt` | `600 (SemiBold)` | `20 pt` | 状态栏时间「9:41」 |

---

## Spacing Tokens
| Token | 值 | 用途 |
|-------|-----|------|
| `spacing.page-h` | `16 pt` | 页面水平边距（Margin） |
| `spacing.bubble-gap-v` | `8 pt` | 同一说话方相邻气泡间距（估算值） |
| `spacing.group-gap-v` | `16 pt` | 不同时间戳分组间距（估算值） |
| `spacing.avatar-bubble-gap` | `8 pt` | 头像与气泡之间间隙 |
| `spacing.bubble-pad-h` | `12 pt` | 气泡内水平 Padding |
| `spacing.bubble-pad-v` | `10 pt` | 气泡内垂直 Padding |
| `spacing.banner-pad-h` | `16 pt` | 横幅内水平 Padding |
| `spacing.banner-pad-v` | `12 pt` | 横幅内垂直 Padding |
| `spacing.banner-icon-gap` | `10 pt` | 横幅云朵图标与文字间隙 |
| `spacing.composer-pad-h` | `16 pt` | Composer 水平 Padding |
| `spacing.composer-pad-v` | `8 pt` | Composer 垂直 Padding |
| `spacing.input-gap` | `8 pt` | 输入框与左右按钮间隙 |
| `spacing.nav-pad-h` | `16 pt` | 导航栏水平 Padding |
| `spacing.staged-div-v` | `4 pt` | 暂存分割线两行文字间距 |

---

## Motion Tokens

| Token | 值 | 用途 |
|-------|-----|------|
| `motion.banner-enter.duration` | `300 ms` | 横幅下滑入场 |
| `motion.banner-enter.easing` | `cubic-bezier(0.34, 1.56, 0.64, 1.0)` | 横幅入场弹性（spring） |
| `motion.banner-exit.duration` | `200 ms` | 横幅上滑离场 |
| `motion.banner-exit.easing` | `ease-in` | 横幅离场 |
| `motion.history-dim.duration` | `400 ms` | 历史区透明度降至 0.92 |
| `motion.history-dim.easing` | `ease-out` | 暗淡过渡 |
| `motion.divider-enter.duration` | `250 ms` | 暂存分割线淡入 |
| `motion.clock-badge-enter.duration` | `200 ms` | 时钟角标缩放入场 |
| `motion.clock-badge-enter.easing` | `cubic-bezier(0.34, 1.56, 0.64, 1.0)` | 时钟角标弹入 |
| `motion.retry-btn-press.scale` | `0.96` | 重试按钮按下缩放 |
| `motion.retry-btn-press.duration` | `100 ms` | 按下反馈时长 |
