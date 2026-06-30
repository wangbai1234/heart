# 09 Accessibility — Redeem 兑换页

---

## 触摸目标尺寸（iOS HIG 标准 ≥ 44 × 44pt）

| 组件 | 可见尺寸（估算逻辑pt） | 触摸区尺寸 | 是否达标 |
|------|---------------------|-----------|---------|
| BackButton（返回 <） | ≈ 14 × 14pt（图标） | 需扩展至 ≥ 44 × 44pt | ⚠️ 需要增加透明触摸区 |
| 单个字符格（CharBox） | ≈ 24 × 30pt（估算值） | 键盘输入，整组为一个输入域 | ✅ 整组输入区域足够大 |
| PasteButton | ≈ 107 × 27pt（估算值） | 高度 ≈ 27pt，需确保 ≥ 44pt | ⚠️ 高度可能不足，建议增加垂直 padding |
| ActivateButton | ≈ 360 × 36pt（估算值） | ≈ 360 × 36pt | ⚠️ 高度估算约 36pt，应确保 ≥ 44pt；设计稿视觉上较高，实际实现需验证 |
| FAQAccordion Header | ≈ 360 × 30pt（估算值） | 整行可点击区域 | ✅ 整行宽度足够，高度需确保 ≥ 44pt |
| 去爱发电链接 | ≈ 80 × 14pt（文字） | 需扩展触摸区至 ≥ 44pt 高 | ⚠️ 需要增加垂直 padding 扩展触摸区 |

**建议**：所有可交互元素的触摸响应区域至少扩展至 44 × 44pt，可通过增加内边距或使用透明覆盖区实现，视觉不必改变。

---

## 颜色对比度（WCAG 2.1 标准）

| 文字 | 背景 | 预估对比度 | 标准 | 评估 |
|------|------|-----------|------|------|
| `#3A3A4A` (页面标题/正文) | `rgba(255,248,243,0.92)` (卡片背景) | ≈ 9.5:1 | AA/AAA | ✅ 优秀 |
| `#3A3A4A` (步骤文字) | `rgba(255,255,255,0.88)` (FAQ 卡片背景) | ≈ 9.5:1 | AA/AAA | ✅ 优秀 |
| `#6B6B7A` (副标题) | `rgba(255,248,243,0.92)` (卡片背景) | ≈ 4.8:1 | AA | ✅ 通过（正常文字 AA 要求 4.5:1） |
| `#FFFFFF` (按钮文字) | `#FFB7C5` (按钮背景渐变) | ≈ 2.5:1 | — | ❌ 未达 WCAG AA（3:1 for large text，4.5:1 for normal text）；建议加深按钮背景或使用更深的文字色 |
| `#FF8FAB` (品牌链接) | `rgba(255,255,255,0.88)` (FAQ 卡片) | ≈ 3.2:1 | 大文字 AA | ⚠️ 接近边界；若字号 ≥ 18pt 或加粗 ≥ 14pt，可达 WCAG AA；建议加深至 `#E8607A` |
| `rgba(58,58,74,0.50)` (免责) | `#FFD8E0` (背景) | ≈ 3.8:1 | — | ⚠️ 未达 AA（4.5:1）；建议免责文字不透明度提高至 0.65 |
| `#FF8FAB` (步骤 badge 数字) | `rgba(255,183,197,0.30)` (badge 背景) | ≈ 1.8:1 | — | ❌ 对比度极低；badge 为装饰性元素，数字信息通过步骤文字重复传达，影响可接受；建议 badge 数字加深至 `#D44062` |

**重要建议**：
- 「立即激活」按钮文字对比度不足，是最关键的无障碍问题，建议修正
- 可使用 [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) 在实现阶段逐项验证

---

## 焦点状态（Keyboard Focus）

| 组件 | 焦点环建议 | 说明 |
|------|-----------|------|
| BackButton | 2px `#FFB7C5` 实线焦点环，圆角 4pt | iOS 上通过 UIFocusSystem 管理 |
| CharBox（输入格） | 2px `#FFB7C5` 实线边框，已在 Focused 状态定义 | ✅ 设计已有 focused 态 |
| PasteButton | 2px `#FFB7C5` 实线焦点环，圆角与组件一致 | 需在实现中确认 |
| ActivateButton | 2px `#FF8FAB` 实线焦点环 | 对高亮色使用品牌色焦点环 |
| FAQAccordion Header | 2px `#FFB7C5` 虚线焦点环（区分于 pressed 态） | 建议 |
| 去爱发电链接 | 下划线 + 2px 焦点环 | 链接 focus 需额外下划线指示 |

**Tab 顺序建议**（从上到下，逻辑顺序）：
1. BackButton
2. CharBox_1_1 → CharBox_1_2 → CharBox_1_3 → CharBox_1_4（作为一个 input group）
3. CharBox_2_1 → CharBox_2_2 → CharBox_2_3 → CharBox_2_4
4. CharBox_3_1 → CharBox_3_2 → CharBox_3_3 → CharBox_3_4
5. PasteButton
6. ActivateButton
7. FAQAccordion Header（可 Tab 到，Enter 展开/折叠）
8. 去爱发电链接（仅展开时可 Tab 到）

---

## 文本可读性

| 文字元素 | 字号（逻辑pt） | 行高 | 是否 ≥ 12pt | 行高是否 ≥ 1.4 |
|---------|-------------|------|------------|--------------|
| 页面标题「兑换会员」 | ≈ 17pt | 1.3 | ✅ | ⚠️ 行高 1.3 略低，单行标题可接受 |
| 卡片主标题 | ≈ 20pt | 1.35 | ✅ | ⚠️ 略低，单行可接受 |
| 副标题说明 | ≈ 13pt | 1.6 | ✅ | ✅ |
| 粘贴按钮文字 | ≈ 12pt | 1.4 | ✅ | ✅ |
| 按钮「立即激活」 | ≈ 17pt | 1.0（单行） | ✅ | N/A（单行，无换行） |
| FAQ 标题 | ≈ 15pt | 1.3 | ✅ | ⚠️ 单行可接受 |
| 步骤文字 | ≈ 14pt | 1.5 | ✅ | ✅ |
| 品牌链接 | ≈ 14pt | 1.4 | ✅ | ✅ |
| 免责声明 | ≈ 11pt | 1.5 | ⚠️ 边界值（iOS HIG 最小推荐 11pt） | ✅ |
| 步骤 badge 数字 | ≈ 11pt | 1.0 | ⚠️ 边界值 | N/A（单字符） |

**建议**：免责声明字号 11pt 为 iOS 最小可读边界，若可能，建议提升至 12pt。

---

## ARIA 建议（Web 实现参考 / React Native accessibilityRole）

| 组件 | role | label / accessibilityLabel | 说明 |
|------|------|---------------------------|------|
| BackButton | `button` | "返回上一页" | 图标按钮必须有文字标签 |
| NavigationBar Title | `heading` level=1 | "兑换会员" | 页面标题 |
| RedeemCodeInput（整组） | `group` | "兑换码输入框，格式为12位字母数字" | 分组输入整体语义 |
| CharBox（每个格） | `textbox` | "兑换码第N位" | 辅助技术逐格读出 |
| PasteButton | `button` | "粘贴兑换码" | |
| ActivateButton | `button` | "立即激活" + disabled 时追加 "请先填写完整兑换码" | |
| FAQAccordion Header | `button` | "如何获取兑换码，当前已展开/已折叠" | `aria-expanded` 动态更新 |
| StepList | `list` | — | |
| StepItem | `listitem` | — | |
| 去爱发电链接 | `link` | "前往爱发电赞助页面" | 明确目标，避免仅「去爱发电」 |
| DisclaimerText | `note` | "兑换码一次性有效，激活后不可退还。" | |

---

## Keyboard Navigation

| 操作 | 键盘行为 |
|------|---------|
| Tab | 按 Tab 顺序在可聚焦元素间移动 |
| Shift+Tab | 反向 Tab |
| Enter / Space | 激活按钮（BackButton、PasteButton、ActivateButton） |
| Enter（FAQAccordion Header 聚焦时） | 展开/折叠 accordion |
| Enter（去爱发电链接聚焦时） | 打开外部链接 |
| Escape | 关闭系统键盘（输入框聚焦时） |
| 方向键（Left/Right，输入格间） | 在 CharBox 间移动焦点（自定义实现建议） |

---

## Screen Reader 朗读文本建议（VoiceOver / TalkBack）

| 元素 | 建议朗读文本（中文） |
|------|------------------|
| BackButton | "返回" |
| 页面标题 | "兑换会员，页面" |
| 礼品盒插画 | "装饰插画：礼品盒"（role=image，decorative 可设为 aria-hidden=true） |
| 卡片主标题 | "输入兑换码激活会员" |
| 副标题 | "在爱发电赞助后，你会收到一串12位的兑换码。" |
| CharBox（第1段第1格） | "兑换码，第一段，第1格，共4格，请输入字母或数字" |
| PasteButton | "粘贴兑换码，按钮" |
| ActivateButton（启用） | "立即激活，按钮" |
| ActivateButton（禁用） | "立即激活，按钮，不可用，请先填写完整兑换码" |
| FAQAccordion（折叠） | "如何获取兑换码，已折叠，按钮，双击展开" |
| FAQAccordion（展开） | "如何获取兑换码，已展开，按钮，双击折叠" |
| StepItem_1 | "第一步：前往爱发电赞助页面" |
| StepItem_2 | "第二步：选择心仪的赞助挡位" |
| StepItem_3 | "第三步：完成支付后查收兑换码邮件" |
| StepItem_4 | "第四步：返回 yuoyuo 输入兑换码" |
| 去爱发电链接 | "前往爱发电赞助页面，链接，将在浏览器中打开" |
| DisclaimerText | "兑换码一次性有效，激活后不可退还。" |

---

## 移动端操作友好度

### 单手操作分析（右手拇指，iPhone 14 390pt 宽）

| 区域 | 拇指可达性 | 分析 |
|------|-----------|------|
| BackButton（左上） | ⚠️ 单手拇指难达区域 | 左上角需要拇指延伸，可支持右滑手势替代 |
| 输入框组（中部） | ✅ 拇指舒适区 | 屏幕中部，单手操作友好 |
| PasteButton（卡片内，居中） | ✅ 拇指舒适区 | |
| ActivateButton（中下部） | ✅ 拇指舒适区 | 大按钮，易于单手点击 |
| FAQAccordion Header（中下部） | ✅ | |
| 去爱发电链接（页面下方） | ⚠️ 需拇指延伸 | 若 FAQ 展开，链接位置较低；可接受，用户有意图时会滚动 |
| 免责声明（底部） | N/A | 仅展示，无交互 |

### 手势支持建议
- 右滑返回（Edge Swipe）：系统级手势，建议保留标准 iOS 导航手势
- 点击空白处 dismiss 键盘：当输入框聚焦时，点击输入区域外的空白 → 键盘收起

### 拇指区域分布（iPhone 14 390pt）
- 舒适区：屏幕下半部（y > 420pt）
- 可到达区：屏幕中部（y: 280~420pt）
- 困难区：屏幕顶部（y < 280pt）

主要操作（输入框、粘贴、激活）均在舒适~可到达区，设计总体单手友好。
