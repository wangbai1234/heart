# 03 Design Tokens — Redeem 兑换页

## Color

| Token 名称 | Hex / RGBA | 使用场景 |
|------------|-----------|---------|
| `color.primary` | `#FFB7C5` | 品牌主色，Cherry Pink；立即激活按钮渐变主色 |
| `color.primary.light` | `#FFC8D4` | 按钮渐变终点、输入框聚焦边框 |
| `color.primary.soft` | `rgba(255,183,197,0.20)` | 粘贴按钮背景、步骤序号 badge 背景 |
| `color.secondary` | `#A7C7E7` | 天空蓝；背景渐变中层辅助色 |
| `color.accent` | `#C8B6FF` | 薰衣草紫；礼品盒插画丝带与蝴蝶结色调 |
| `color.background.top` | `#E8C8F0` | 背景渐变顶部（淡粉紫） |
| `color.background.mid` | `#F0B8D0` | 背景渐变中部（cherry pink 淡） |
| `color.background.bottom` | `#FFD8E0` | 背景渐变底部（浅粉） |
| `color.surface` | `#FFF8F3` | 奶油白；卡片主背景 |
| `color.surface.card` | `rgba(255,248,243,0.92)` | Input Card 背景（轻微半透明） |
| `color.glass` | `rgba(255,255,255,0.55)` | 毛玻璃组件背景（粘贴按钮等） |
| `color.glass.light` | `rgba(255,255,255,0.88)` | FAQ 卡片背景（高不透明度） |
| `color.border` | `rgba(255,183,197,0.35)` | 输入框边框（默认态） |
| `color.border.focused` | `#FFB7C5` | 输入框聚焦边框 |
| `color.border.error` | `#FF6B6B` | 输入框错误状态边框 |
| `color.divider` | `rgba(200,182,255,0.20)` | 分隔线（若有） |
| `color.text.primary` | `#3A3A4A` | 主要文字（标题、步骤内容） |
| `color.text.secondary` | `#6B6B7A` | 次要文字（副标题说明文字） |
| `color.text.placeholder` | `rgba(58,58,74,0.35)` | 输入框占位符（4-4-4 格子中的浅色字符） |
| `color.text.brand` | `#FF8FAB` | 品牌强调文字（「去爱发电 →」链接文字） |
| `color.text.disclaimer` | `rgba(58,58,74,0.50)` | 免责声明文字 |
| `color.overlay` | `rgba(0,0,0,0.40)` | 模态遮罩（本页未直接使用，保留） |
| `color.success` | `#6BCB77` | 激活成功状态（Toast 图标） |
| `color.warning` | `#FFD93D` | 警告提示（本页未直接出现） |
| `color.danger` | `#FF6B6B` | 错误状态（兑换码无效） |
| `color.info` | `#A7C7E7` | 信息提示 |
| `color.step.badge` | `rgba(255,183,197,0.30)` | 步骤序号圆形 badge 背景（粉色） |
| `color.step.badge.text` | `#FF8FAB` | 步骤序号文字颜色 |

---

## Gradient

| Token 名称 | 渐变定义 | 方向 | 用途 |
|------------|---------|------|------|
| `gradient.background` | `#E0B8E8` → `#F4C0D0` → `#FFD8E0` | top → bottom (180°) | 全屏背景渐变 |
| `gradient.button.primary` | `#FFB7C5` → `#FF9EAF` | left → right (90°) | 立即激活按钮 |
| `gradient.button.primary.hover` | `#FF9EAF` → `#FF8FA0` | left → right (90°) | 按钮 pressed/hover 态 |
| `gradient.card` | `rgba(255,248,243,0.95)` → `rgba(255,245,240,0.90)` | top → bottom | Input Card 背景微渐变 |
| `gradient.sky` | `rgba(224,200,240,0.80)` → `rgba(255,200,216,0.60)` | top → bottom | 背景天空云彩区域叠层 |

---

## Radius

| Token 名称 | 值（设计稿像素） | 逻辑像素（估算） | 使用场景 |
|------------|---------------|---------------|---------|
| `radius.xs` | 8px | 3pt | 最小圆角（标签等） |
| `radius.sm` | 16px | 6pt | 输入框单个字符格（估算值） |
| `radius.md` | 24px | 9pt | FAQ 折叠卡片 |
| `radius.lg` | 32px | 12pt | Input Card 主卡片 |
| `radius.xl` | 40px | 15pt | 粘贴按钮 |
| `radius.pill` | 9999px | 9999pt | 立即激活按钮（完全胶囊形） |
| `radius.badge` | 9999px | 9999pt | 步骤序号圆形 badge |
| `radius.input.group` | 20px | 8pt | 输入框组整体圆角（估算值） |

---

## Shadow

| Token 名称 | 颜色 | 透明度 | Blur | Offset X | Offset Y | Spread | 使用场景 |
|------------|------|--------|------|----------|----------|--------|---------|
| `shadow.card` | `#FFB7C5` | 0.15 | 40px | 0 | 8px | 0 | Input Card 投影 |
| `shadow.button.primary` | `#FF8FAB` | 0.40 | 24px | 0 | 8px | 0 | 立即激活按钮光晕投影 |
| `shadow.faq.card` | `rgba(0,0,0,0.06)` | — | 16px | 0 | 4px | 0 | FAQ 折叠卡片轻阴影 |
| `shadow.paste.button` | `rgba(255,183,197,0.20)` | — | 12px | 0 | 4px | 0 | 粘贴按钮轻阴影（估算值） |

---

## Blur

| Token 名称 | 值 | 使用场景 |
|------------|-----|---------|
| `blur.glass.sm` | 8px | 粘贴按钮毛玻璃模糊 |
| `blur.glass.md` | 16px | Input Card 背景模糊（轻） |
| `blur.glass.lg` | 24px | 深层背景模糊（如底部弹层，本页未直接出现） |

---

## Opacity

| Token 名称 | 值 | 使用场景 |
|------------|-----|---------|
| `opacity.surface.card` | 0.92 | Input Card 背景 |
| `opacity.glass` | 0.55 | 标准毛玻璃组件 |
| `opacity.glass.light` | 0.88 | FAQ 卡片 |
| `opacity.border.default` | 0.35 | 输入框默认边框 |
| `opacity.text.secondary` | 0.60 | 次要文字 |
| `opacity.text.placeholder` | 0.35 | 占位符文字 |
| `opacity.text.disclaimer` | 0.50 | 免责声明 |
| `opacity.disabled` | 0.40 | 禁用状态组件 |
| `opacity.step.badge.bg` | 0.30 | 步骤序号 badge 背景 |

---

## Typography

| Token 名称 | 字体族 | 字号（设计稿px） | 逻辑字号（pt） | 字重 | 行高 | 字间距 | 颜色 Token | 层级 |
|------------|--------|----------------|--------------|------|------|--------|-----------|------|
| `type.navigation.title` | PingFang SC | ≈44px | 17pt | SemiBold (600) | 1.3 | 0 | `color.text.primary` | Headline |
| `type.card.title` | PingFang SC | ≈52px | 20pt | Bold (700) | 1.35 | 0 | `color.text.primary` | Title |
| `type.card.subtitle` | PingFang SC | ≈34px | 13pt | Regular (400) | 1.6 | 0 | `color.text.secondary` | Body |
| `type.input.char` | SF Pro Rounded / PingFang SC | ≈44px | 17pt | Medium (500) | 1.0 | 0 | `color.text.primary` | Tabular |
| `type.paste.button` | PingFang SC | ≈32px | 12pt | Regular (400) | 1.4 | 0 | `color.text.secondary` | Caption |
| `type.button.primary` | PingFang SC | ≈44px | 17pt | SemiBold (600) | 1.0 | 0.5pt | `#FFFFFF` | Body |
| `type.faq.header` | PingFang SC | ≈40px | 15pt | SemiBold (600) | 1.3 | 0 | `color.text.primary` | Headline |
| `type.faq.step` | PingFang SC | ≈36px | 14pt | Regular (400) | 1.5 | 0 | `color.text.primary` | Body |
| `type.link.brand` | PingFang SC | ≈36px | 14pt | Medium (500) | 1.4 | 0 | `color.text.brand` | Body |
| `type.disclaimer` | PingFang SC | ≈28px | 11pt | Regular (400) | 1.5 | 0 | `color.text.disclaimer` | Caption |
| `type.step.badge` | PingFang SC / SF Pro Rounded | ≈28px | 11pt | SemiBold (600) | 1.0 | 0 | `color.step.badge.text` | Caption |

---

## Spacing Scale

| Token 名称 | 设计稿值 | 逻辑值（pt） | 说明 |
|------------|---------|------------|------|
| `spacing.1` | 8px | 3pt | 最小间距 |
| `spacing.2` | 16px | 6pt | 图标与文字间距 |
| `spacing.3` | 24px | 9pt | 小组件内间距 |
| `spacing.4` | 32px | 12pt | 标准间距（卡片内） |
| `spacing.5` | 40px | 15pt | 页面边距、组件间距 |
| `spacing.6` | 48px | 18pt | 节与节之间的间距 |
| `spacing.8` | 64px | 24pt | 大间距 |
| `spacing.10` | 80px | 30pt | 超大间距（估算值） |
| `spacing.12` | 96px | 36pt | 导航栏高度 |

---

## Motion

| Token 名称 | 值 | 说明 |
|------------|-----|------|
| `motion.duration.fast` | 150ms | 状态切换（pressed/hover） |
| `motion.duration.normal` | 250ms | 一般组件动画（卡片展开/收起） |
| `motion.duration.slow` | 400ms | 页面进出场动画 |
| `motion.duration.spring` | 500ms | 弹性动画（FAQ accordion 展开） |
| `motion.delay.stagger` | 50ms | 步骤列表逐项出现时的交错延迟 |
| `motion.easing.ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | 组件出现 |
| `motion.easing.ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | 状态切换 |
| `motion.easing.spring` | `cubic-bezier(0.175, 0.885, 0.32, 1.275)` | 弹性效果（accordion 展开） |
| `motion.easing.ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | 元素退出 |
