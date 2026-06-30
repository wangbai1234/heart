# 04 Components — Redeem 兑换页

---

## 1. NavigationBar（导航栏）

**作用**：提供页面标题展示与返回导航。

**层级**：固定在 Safe Area 顶部，Z-index 高于页面内容。

**尺寸（估算）**：
- 宽度：1024px（全宽）
- 高度：≈ 96px

**布局**：
- Flex Row，justify-content: space-between，align-items: center
- 左侧：返回按钮（触摸区域 ≥ 88×88px）
- 中间：标题文字（绝对居中）
- 右侧：空区域（保持对称）

**状态**：
- Default：正常显示
- Scroll（有内容滚动到导航栏下方时）：可考虑加轻微背景模糊，⚠️ 设计稿未定义

**样式细节**：
- 背景：透明，背景渐变透出
- 标题字：「兑换会员」，PingFang SC SemiBold ≈ 44px（设计稿），颜色 `#3A3A4A`
- 返回按钮：「<」符号，字重 Medium，颜色 `#3A3A4A`，距左边 ≈ 48px

**交互**：点击返回按钮 → pop 当前页面（右滑退出动画）

---

## 2. BackButton（返回按钮）

**作用**：导航返回上一级页面。

**层级**：NavigationBar 内左侧。

**尺寸（估算）**：
- 可见图标尺寸：≈ 36×36px
- 触摸响应区域：≈ 88×88px（iOS HIG 标准）

**状态**：
- Default：`#3A3A4A` 不透明度 100%
- Pressed：不透明度降至 50%，持续 150ms

**样式细节**：「<」字符或 chevron.left SF Symbol 图标

**交互**：点击 → 页面 pop 退出（系统级右滑手势也应支持）

---

## 3. InputCard（兑换码输入卡片）

**作用**：包含礼品插画、说明文字、兑换码输入框组、粘贴按钮的主操作区域。

**层级**：页面主内容区，位于 NavigationBar 下方。

**尺寸（估算）**：
- 宽度：≈ 944px（左右各 40px 外边距）
- 高度：≈ 560px（估算值，取决于内部内容）
- 圆角：≈ 32px
- 左右外边距：≈ 40px

**布局**：Flex Column，align-items: center，padding ≈ 40px，gap ≈ 32px

**状态**：
- Default：正常显示
- Input Active（输入框聚焦时）：卡片无明显变化，输入框自身高亮

**样式细节**：
- 背景：`rgba(255, 248, 243, 0.92)`
- 阴影：`0 8px 40px rgba(255,183,197,0.15)`
- 边框：无硬边框（依靠背景色与背景渐变区分层次）

**子组件**：GiftIllustration、CardTitle、CardSubtitle、RedeemCodeInput、PasteButton

---

## 4. GiftIllustration（礼品盒插画）

**作用**：视觉装饰，强化"礼物"惊喜感。

**层级**：InputCard 内顶部，居中。

**尺寸（估算）**：
- 插画渲染尺寸：≈ 240 × 240px（估算值）
- 包含轻微漂浮效果的装饰碎片（飘落的心/花瓣）

**布局**：水平居中

**状态**：
- Default：静止展示
- ⚠️ 入场动画：设计稿未定义，建议参考 Motion Storyboard（建议轻微上下浮动循环动画，幅度 ≈ 6px，周期 ≈ 3s）

**样式细节**：
- 礼品盒主体：白色/浅粉色，带光泽高光
- 蝴蝶结：薰衣草紫 `#C8B6FF`，带淡紫色丝带
- 装饰碎片（飘落花瓣/心形）：粉色调
- 风格：二次元插画，软渲染，无硬边线

**资源建议**：`illustration_gift_box.png` 或 SVG（推荐 Lottie 动画版本）

---

## 5. CardTitle（卡片主标题）

**作用**：引导用户核心操作意图。

**尺寸（估算）**：高度约 ≈ 56px

**样式细节**：
- 文字：「输入兑换码激活会员」
- 字体：PingFang SC Bold ≈ 52px（设计稿）
- 颜色：`#3A3A4A`
- 对齐：水平居中

---

## 6. CardSubtitle（卡片副标题）

**作用**：说明兑换码来源，引导用户预期。

**尺寸（估算）**：高度约 ≈ 44px

**样式细节**：
- 文字：「在「爱发电」赞助后，你会收到一串12位的兑换码。」
- 字体：PingFang SC Regular ≈ 34px（设计稿）
- 颜色：`#6B6B7A`（次要文字色）
- 对齐：水平居中

---

## 7. RedeemCodeInput（4-4-4 分组兑换码输入框）

**作用**：12 位兑换码的结构化输入控件，分三段各 4 位。

**层级**：InputCard 内，位于副标题下方。

**尺寸（估算）**：
- 整体宽度：撑满卡片内容区（≈ 864px）
- 整体高度：≈ 80px
- 单个字符格宽度：≈ 64px（估算值）
- 单个字符格高度：≈ 80px（估算值）
- 字符格圆角：≈ 16px（估算值）
- 三段之间的「-」分隔符：≈ 32px 宽区域

**布局**：
- Flex Row，justify-content: center，align-items: center
- 第一段：4 个字符格，Flex Row，gap ≈ 8px
- 分隔符「-」
- 第二段：4 个字符格，Flex Row，gap ≈ 8px
- 分隔符「-」
- 第三段：4 个字符格，Flex Row，gap ≈ 8px

**状态**：
- Default（空）：字符格显示浅色占位字符（设计稿中可见模糊字符），边框 `rgba(255,183,197,0.35)`
- Focused（当前输入格）：边框高亮 `#FFB7C5`，光标可见
- Filled（已输入字符）：字符显示 `#3A3A4A`
- Error：边框变为 `#FF6B6B`，整组输入框抖动动画

**样式细节**：
- 字符格背景：`rgba(255,255,255,0.70)`（估算值）
- 字符格边框：1px solid，默认 `rgba(255,183,197,0.35)`
- 字符格圆角：≈ 16px（估算值）
- 分隔符「-」：颜色 `#FFB7C5`，字号 ≈ 40px，居中

**交互**：
- 点击任意格 → 弹出系统键盘（数字+字母）
- 输入一格满后自动跳到下一格
- 第 4 格满后自动跳到下一段首格
- 12 格全满后自动 dismiss 键盘（可选）
- 支持退格删除

---

## 8. PasteButton（粘贴兑换码按钮）

**作用**：从剪贴板一键粘贴 12 位兑换码，填入输入框。

**层级**：InputCard 内，位于输入框下方，居中。

**尺寸（估算）**：
- 宽度：≈ 280px（估算值）
- 高度：≈ 72px（估算值）
- 圆角：≈ 36px（pill）

**布局**：Flex Row，align-items: center，justify-content: center，gap ≈ 12px

**状态**：
- Default：正常显示（半透明白色背景 + 轻边框）
- Pressed：scale 下降至 0.97，持续 150ms
- Disabled：不透明度 0.40（剪贴板为空时）

**样式细节**：
- 背景：`rgba(255,255,255,0.60)`（毛玻璃）
- 边框：1px solid `rgba(255,183,197,0.40)`
- 图标：📋 剪贴板图标（SF Symbol: doc.on.clipboard），颜色 `#FF8FAB`，尺寸 ≈ 28px
- 文字：「粘贴兑换码」，PingFang SC Regular ≈ 32px（设计稿），颜色 `#6B6B7A`

**交互**：点击 → 读取系统剪贴板 → 自动填入输入框 → 若格式不符则 Toast 提示「格式不正确，请检查兑换码」

---

## 9. ActivateButton（立即激活按钮）

**作用**：提交兑换码，发起激活请求。

**层级**：InputCard 下方，页面主操作按钮。

**尺寸（估算）**：
- 宽度：≈ 944px（与卡片同宽）
- 高度：≈ 96px
- 圆角：≈ 48px（完全 pill）

**布局**：Flex Row，align-items: center，justify-content: center

**状态**：
- Default（未输入完整）：渐变背景不透明度降低（≈ 0.60）或整体 opacity 0.60；⚠️ 设计稿未定义具体禁用态，建议参考 Motion Storyboard
- Active（12位已输入）：渐变全亮，阴影明显
- Pressed：scale 0.97，阴影缩小，持续 150ms
- Loading：按钮内显示旋转 loading 指示器，文字隐藏
- Success：按钮变绿（可选 Toast 替代）

**样式细节**：
- 背景：`linear-gradient(90deg, #FFB7C5, #FF9EAF)`
- 阴影：`0 8px 24px rgba(255,143,171,0.40)`
- 文字：「立即激活」，PingFang SC SemiBold ≈ 44px，颜色 `#FFFFFF`，字间距 ≈ 0.5pt

**交互**：
- 点击 → API 请求激活 → Loading 态 → 成功/失败处理
- 12位未填满时：按钮为禁用态，点击提示「请先填写完整兑换码」

---

## 10. FAQAccordion（如何获取兑换码 折叠卡片）

**作用**：为未持有兑换码的用户提供引导说明，默认折叠以减少信息干扰；设计稿中呈展开状态。

**层级**：ActivateButton 下方，页面次要内容区。

**尺寸（估算）**：
- 宽度：≈ 944px
- 折叠态高度：≈ 80px
- 展开态高度：≈ 480px（估算值，包含 4 步骤 + 链接）
- 圆角：≈ 24px

**布局**：Flex Column

**状态**：
- Collapsed（默认）：只显示 Header 行
- Expanded（设计稿当前状态）：显示 Header + 步骤列表 + 「去爱发电」链接

**Header 行样式**：
- Flex Row，justify-content: space-between，align-items: center，padding ≈ 32px
- 左侧：❓ 圆形图标（橙色/玫红轮廓）+ 「如何获取兑换码」文字（SemiBold）
- 右侧：chevron.down 图标（展开时旋转 180°）

**展开内容**：
- 步骤列表（4 条），每条 Flex Row：numbered badge + 步骤说明文字
- 步骤间 gap ≈ 32px
- 底部：「去爱发电 →」品牌色链接，居中，与最后步骤间距 ≈ 40px

**步骤 Badge**：
- 宽高：≈ 48 × 48px（圆形）（估算值）
- 背景：`rgba(255,183,197,0.30)`
- 数字颜色：`#FF8FAB`
- 字号：≈ 28px SemiBold

**样式细节（卡片）**：
- 背景：`rgba(255,255,255,0.88)`
- 阴影：`0 4px 16px rgba(0,0,0,0.06)`
- 边框：无

**交互**：
- 点击 Header → 展开/折叠动画（高度插值，duration 250ms，easing ease-out）
- 点击「去爱发电 →」→ 打开外部浏览器（爱发电赞助链接）

---

## 11. StepItem（步骤列表项）

**作用**：单条操作引导步骤展示。

**层级**：FAQAccordion 展开区域内。

**尺寸（估算）**：每行高度 ≈ 56px，flex row

**样式细节**：
- Badge：圆形，粉色，数字「1」「2」「3」「4」
- 步骤文字：PingFang SC Regular ≈ 36px，`#3A3A4A`

步骤内容：
1. 前往「爱发电」赞助页面
2. 选择心仪的赞助挡位
3. 完成支付后查收兑换码邮件
4. 返回 yuoyuo 输入兑换码

---

## 12. ExternalLink（去爱发电 链接）

**作用**：引导未赞助用户跳转至爱发电赞助页完成购买。

**尺寸（估算）**：高度 ≈ 52px，宽度自适应内容

**样式细节**：
- 文字：「去爱发电 →」
- 字体：PingFang SC Medium ≈ 36px
- 颜色：`#FF8FAB`（品牌链接色）
- 水平居中

**状态**：
- Default：正常
- Pressed：不透明度降至 0.60

---

## 13. DisclaimerText（免责声明文字）

**作用**：法律免责，告知用户兑换码的一次性特性。

**层级**：FAQ 卡片下方，页面底部区域。

**尺寸（估算）**：高度 ≈ 48px

**样式细节**：
- 文字：「兑换码一次性有效，激活后不可退还。」
- 字体：PingFang SC Regular ≈ 28px（设计稿）
- 颜色：`rgba(58,58,74,0.50)`
- 对齐：水平居中

---

## 14. HomeIndicator（Home 指示条）

**作用**：iPhone 底部 Home 手势指示器。

**尺寸（估算）**：
- 宽度：≈ 260px
- 高度：≈ 8px
- 圆角：≈ 4px（pill）

**样式细节**：
- 颜色：`#3A3A4A`（与背景形成适度对比）
- 水平居中
- 距底部 safe area 边缘 ≈ 16px

---

## 可复用组件建议

| 组件 | 理由 |
|------|------|
| `NavigationBar` | 全 App 通用导航模式，可接受 title、leftAction、rightAction 三个 prop |
| `RedeemCodeInput` | 兑换码场景专用，但输入框分组逻辑（N-N-N）可抽象为 `SegmentedCodeInput` |
| `PasteButton` | 轻量粘贴功能，可在所有需要粘贴代码/序列号的场景复用 |
| `ActivateButton` / 主 CTA 按钮 | 全 App 主操作按钮风格一致，可作为 `PrimaryButton` 组件 |
| `FAQAccordion` | 折叠说明卡片，可抽象为 `AccordionCard`，prop 传入 title 和 content |
| `StepList` + `StepItem` | 步骤引导在多个场景复用（新手引导、流程说明等） |
| `DisclaimerText` | 全 App 底部法律说明，可接受文字内容作 prop |
| `GiftIllustration` | 此页专属，但动效框架（Lottie 容器）可复用 |
