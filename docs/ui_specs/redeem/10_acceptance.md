# 10 Acceptance Checklist — Redeem 兑换页

> 目标：整体视觉一致度 ≥ 95%
> 验收方式：将实现截图与设计稿（15_redeem.png）逐像素对比，每项打钩确认。

---

## Layout 布局

- □ 全屏背景是否直接使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` 或深色模式使用 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- □ 背景图是否保留原始云层与光感，无重画痕迹
- □ NavigationBar 固定在 Safe Area 顶部，不随内容滚动
- □ InputCard 左右外边距对称（≈ 15pt 逻辑），与设计稿一致
- □ ActivateButton 与 InputCard 上下间距约 15pt，目视一致
- □ FAQAccordion Card 与 ActivateButton 上下间距约 18pt，目视一致
- □ 免责声明文字距 FAQ 卡片底部约 15pt，目视一致
- □ 整页内容在 iPhone 14 竖屏下，键盘弹出时不被遮挡（KeyboardAvoidingView 正常工作）
- □ Bottom Safe Area 正确预留（34pt），Home Indicator 居中展示

---

## Spacing / Padding / Margin 间距

- □ InputCard 内部 padding 四边均匀（≈ 15pt）
- □ 礼品盒插画与主标题之间间距约 12pt
- □ 主标题与副标题间距约 5pt
- □ 副标题与输入框组间距约 15pt
- □ 输入框组与粘贴按钮间距约 12pt
- □ 输入框三段之间分隔符（「-」）间距视觉对称
- □ FAQ 步骤列表各行间距约 12pt，目视均匀

---

## Radius 圆角

- □ InputCard 圆角约 12pt（逻辑），视觉柔和，无尖角
- □ ActivateButton 为完全 pill 形（圆角 = 高度/2），两端半圆饱满
- □ PasteButton 为 pill 形圆角，目视一致
- □ FAQ 折叠卡片圆角约 9pt，视觉一致
- □ 步骤序号 badge 为完整圆形
- □ 各字符格（CharBox）圆角约 6pt，视觉柔和
- □ Home Indicator 为 pill 形

---

## Shadow 阴影

- □ InputCard 有粉色光晕投影（`0 8px 40px rgba(255,183,197,0.15)`），方向向下，扩散柔和
- □ ActivateButton 有粉红色光晕阴影（`0 8px 24px rgba(255,143,171,0.40)`），视觉有浮感
- □ FAQ 卡片有轻微灰色阴影（`0 4px 16px rgba(0,0,0,0.06)`），与背景有层次区分
- □ PasteButton 有轻粉色阴影，与卡片背景区分

---

## Blur 毛玻璃效果

- □ PasteButton 背景有轻微毛玻璃模糊效果（backdrop-blur ≈ 8px）
- □ InputCard 背景有轻微模糊（≈ 16px），与纯白色不同
- □ FAQ 卡片背景接近不透明（opacity ≈ 0.88），毛玻璃效果不明显，但仍有轻微透明感

---

## Background / Gradient

- □ 是否未将背景替换为代码渐变
- □ ActivateButton 渐变方向为从左到右（90°），从 `#FFB7C5` 到 `#FF9EAF`
- □ 渐变过渡平滑，无色带分层

---

## Typography 排版

- □ 页面标题「兑换会员」：居中，SemiBold，约 17pt，颜色 `#3A3A4A`
- □ 卡片主标题「输入兑换码激活会员」：居中，Bold，约 20pt，颜色 `#3A3A4A`
- □ 副标题说明：居中，Regular，约 13pt，颜色 `#6B6B7A`，多行时行高 ≥ 1.5
- □ 兑换码字符格内字体：SF Pro Rounded / PingFang SC，约 17pt，对齐居中
- □ 粘贴按钮文字：Regular，约 12pt，`#6B6B7A`
- □ ActivateButton 文字「立即激活」：SemiBold，约 17pt，`#FFFFFF`，居中
- □ FAQ 标题「如何获取兑换码」：SemiBold，约 15pt，`#3A3A4A`
- □ 步骤文字：Regular，约 14pt，`#3A3A4A`，行高 ≥ 1.4
- □ 品牌链接「去爱发电 →」：Medium，约 14pt，`#FF8FAB`，居中
- □ 免责声明：Regular，约 11pt，`rgba(58,58,74,0.50)`，居中
- □ 步骤 badge 数字：SemiBold，约 11pt，`#FF8FAB`

---

## 组件尺寸

- □ 礼品盒插画渲染尺寸约 91 × 91pt（逻辑），比例正确，无变形拉伸
- □ 礼品盒是否直接使用 `/Users/wanglixun/heart/assets/backgrounds/兑换页礼品盒.png`
- □ InputCard 高度与设计稿目视一致（包含插画、文字、输入框、粘贴按钮）
- □ ActivateButton 高度 ≥ 44pt（iOS HIG 要求），视觉厚重感与设计稿一致
- □ PasteButton 高度 ≥ 44pt（需确认）
- □ 字符格每格宽高比例与设计稿一致（近似正方形）
- □ FAQ 步骤 badge 宽高均为约 18pt（圆形）
- □ FAQAccordion 展开高度与设计稿目视一致

---

## Glass Effect 透明度

- □ InputCard 背景为 `rgba(255,248,243,0.92)`，非纯白（可通过背景渐变透出验证）
- □ PasteButton 背景为半透明白色（`rgba(255,255,255,0.60)`），下方有背景透出
- □ FAQ 卡片背景为 `rgba(255,255,255,0.88)`，高不透明但非完全不透明

---

## Visual Weight 视觉重量

- □ ActivateButton 为页面最重的视觉元素（渐变实底 + 大阴影），引导视觉焦点正确
- □ InputCard 为次重量元素，主标题次于按钮
- □ FAQ 折叠卡片视觉重量低于主输入卡片
- □ 免责声明为最轻视觉元素（低对比度文字）
- □ 整体视觉层次：背景 < 卡片 < FAQ < 激活按钮，层次清晰

---

## Alignment 对齐

- □ 页面标题「兑换会员」精确水平居中
- □ 礼品盒插画精确水平居中于 InputCard
- □ 卡片内所有文字元素（主标题、副标题）水平居中
- □ 兑换码输入框组整体水平居中于卡片内容区
- □ 三段输入格视觉对称（左/中/右段宽度相等）
- □ 粘贴按钮水平居中
- □ ActivateButton 与 InputCard 左右边缘对齐
- □ FAQ 卡片与 ActivateButton 左右边缘对齐
- □ FAQ 步骤列表左对齐（badge 左对齐，文字左对齐）
- □ 「去爱发电 →」链接水平居中于 FAQ 卡片
- □ 免责声明文字水平居中
- □ Home Indicator 水平居中

---

## Safe Area 遵守

- □ 所有内容在 Status Bar 下方（≥ 47pt safe area top）
- □ 所有内容在 Bottom Safe Area 上方（≥ 34pt safe area bottom）
- □ NavigationBar 起始 y 位置在 Status Bar 底部
- □ 最后一个内容元素（免责声明）与 Home Indicator 之间有足够间距（≥ 16pt）

---

## 底部栏 / Tab 栏

此页面无底部 Tab Bar，底部仅显示系统 Home Indicator。
- □ 确认无底部 Tab Bar 出现在此页面
- □ Home Indicator 颜色为深色（`#3A3A4A`），与浅色背景形成对比

---

## 状态指示器

- □ 输入框 Default 态：浅粉边框，占位符文字可见
- □ 输入框 Focused 态：边框高亮至 `#FFB7C5`，当前格光标可见
- □ 输入框 Filled 态：字符清晰可读，颜色 `#3A3A4A`
- □ 输入框 Error 态：边框变为 `#FF6B6B`，整组输入框抖动动画执行
- □ ActivateButton 禁用态：opacity 降低（约 0.60），颜色偏淡
- □ ActivateButton 激活态（12位已填）：渐变全亮，阴影明显
- □ ActivateButton Loading 态：spinner 显示，文字隐藏
- □ FAQAccordion 折叠/展开态：chevron 旋转方向正确
- □ PasteButton Disabled 态（剪贴板空）：opacity ≈ 0.40

---

## 颜色 100% 符合 Design Token

- □ 背景渐变颜色值与 `gradient.background` token 一致
- □ ActivateButton 渐变颜色与 `gradient.button.primary` token 一致
- □ InputCard 背景颜色与 `color.surface.card` token 一致
- □ 主标题颜色为 `color.text.primary`（`#3A3A4A`）
- □ 副标题颜色为 `color.text.secondary`（`#6B6B7A`）
- □ 品牌链接颜色为 `color.text.brand`（`#FF8FAB`）
- □ 步骤 badge 背景与 `color.step.badge` token 一致
- □ 步骤 badge 数字颜色与 `color.step.badge.text` token 一致
- □ 免责声明颜色与 `color.text.disclaimer` token 一致
- □ 无任何组件使用设计规范外的颜色值

---

## 应用名拼写

- □ 步骤 4 文字中「返回yuoyuo输入兑换码」应用名拼写为「yuoyuo」（全小写，无大写）
- □ 页面内无「YuoYuo」「Yuoyuo」「YUOYUO」等错误大小写形式
- □ 确认所有出现 yuoyuo 名称的位置均使用纯小写

---

## 整体视觉一致性（综合评分）

- □ 与设计稿 15_redeem.png 整体视觉相似度 ≥ 95%
- □ 颜色偏差在可接受范围内（目视无明显差异）
- □ 字体渲染与设计稿接近（PingFang SC 字重一致）
- □ 插画位置、比例与设计稿一致
- □ 整页情感基调（温暖、礼物感、治愈）与设计稿传达一致

---

**验收通过标准**：所有 □ 项中，必须项（Layout、Typography、Color Token、应用名拼写）100% 通过；其余项目通过率 ≥ 95%。
