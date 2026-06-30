# 10 Acceptance Checklist — 角色页 Character Selector

> 目标：整体视觉一致度 ≥ 95%
> 验收者在每条前标注 [x] 通过，[ ] 不通过，[~] 部分通过并注明原因。

---

## 布局（Layout）

- [ ] 页面背景是否直接使用浅色模式 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png` 或深色模式 `/Users/wanglixun/heart/assets/backgrounds/暗色背景图.png`
- [ ] StatusBar 高度 47 pt，位于最顶部
- [ ] NavigationBar 高度 44 pt，紧接 StatusBar 之下
- [ ] 英雄区（Hero Section）高度约 280 pt（估算），全宽 390 pt
- [ ] Hero 是否直接使用 `/Users/wanglixun/heart/assets/backgrounds/background_character_hero.webp`
- [ ] 角色卡列表区 Padding 水平 16 pt，卡片间距 12 pt
- [ ] ConfirmCTABar 固定于底部，不随内容滚动
- [ ] ConfirmCTABar 高度 80 pt（含 Safe Area Bottom 34 pt）
- [ ] HomeIndicator 在页面最底部，居中显示

---

## Spacing / Padding / Margin

- [ ] 页面水平内容 Padding = 16 pt（卡片两侧）
- [ ] 导航栏水平 Padding = 20 pt（左右各 20 pt）
- [ ] ConfirmButton 左右 Padding = 20 pt（距屏幕边缘）
- [ ] 角色卡内部 Padding = 16 pt 四周
- [ ] 头像容器与文字列间距 = 12 pt
- [ ] 角色名与描述文字间距 = 8 pt
- [ ] 名字行中名称与性格标签间距 = 8 pt
- [ ] 卡片与卡片之间间距 = 12 pt

---

## 圆角（Radius）

- [ ] 角色卡片圆角 = 20 pt
- [ ] 性格标签（御姐型/元气型）圆角 = 12 pt（pill 形）
- [ ] "选择"描边按钮圆角 = 18 pt（胶囊）
- [ ] SelectedIndicator（实心粉圆）圆角 = 9999 pt（完整圆形）
- [ ] 确认选择按钮圆角 = 27 pt（胶囊，等于 height / 2）
- [ ] 头像容器圆角 = 9999 pt（完整圆形）
- [ ] HomeIndicator 条圆角 = 2.5 pt

---

## 阴影（Shadow）

- [ ] 角色卡片阴影：rgba(0,0,0,0.06)，Blur 12 pt，Offset Y +4 pt
- [ ] 确认按钮阴影：rgba(255,143,171,0.35)，Blur 16 pt，Offset Y +6 pt
- [ ] 神无月凛头像光晕：紫色描边 + 外发光 Blur 8 pt（rgba(200,182,255,0.5)）
- [ ] 桃乐丝头像光晕：蓝色描边 + 外发光 Blur 8 pt（rgba(167,199,231,0.5)）
- [ ] SelectedIndicator（勾圆）有轻微粉色投影

---

## Blur 效果

- [ ] 玻璃心形图标有 Backdrop Blur 效果（约 8 pt）
- [ ] 玻璃心形内部有半透明质感（不是实心填充）
- [ ] 英雄区底部渐变叠加层为纯颜色渐变，无 blur

---

## 渐变颜色/方向（Gradient）

- [ ] 确认按钮渐变：从左 #FF8FAB → 右 #FFB7C5，方向水平
- [ ] 英雄区底部：从透明 → #FFF8F3，方向从上至下
- [ ] 玻璃心形内部有粉紫渐变光晕（非纯色填充）
- [ ] 天空背景包含粉色/紫色/橙色渐变云层（动漫插画风格）

---

## 字体/字号/字重/行高（Typography）

- [ ] 导航标题"选择一位陪伴你的人"：17 pt，Medium 500，#3A3A4A
- [ ] 角色名称（神无月 凛 / 桃乐丝）：18 pt，Bold 700，深色（约 #1A1A2E）
- [ ] 性格标签文字（御姐型 / 元气型）：12 pt，Medium 500
- [ ] 角色描述段落：13 pt，Regular 400，行高 1.6，rgba(58,58,74,0.75)
- [ ] 确认按钮文字"确认选择"：17 pt，Semibold 600，#FFFFFF
- [ ] "选择"按钮文字：15 pt，Medium 500，#FFB7C5
- [ ] 字体使用 PingFang SC / HarmonyOS Sans SC（中文），SF Pro Rounded（英文/数字）

---

## 组件尺寸（Component Dimensions）

- [ ] 角色卡宽度 = 358 pt（390 - 32 pt padding）
- [ ] 角色卡高度约 200 pt（允许因内容高度有 ±20 pt 浮动）
- [ ] 头像容器直径 = 约 120 pt（圆形）
- [ ] 神无月凛头像是否直接使用 `character_shenwuyue_avatar.png`
- [ ] 桃乐丝头像是否直接使用 `character_taolesi_avatar.png`
- [ ] SelectedIndicator 直径 = 约 40 pt
- [ ] "选择"按钮尺寸约 68 × 36 pt（建议验收时接受 ±4 pt 误差）
- [ ] 确认按钮：宽 350 pt × 高 54 pt
- [ ] 玻璃心形：约 120 × 110 pt

---

## Glass Effect 透明度

- [ ] 玻璃心形主体透明度约 0.55（可透见背景天空）
- [ ] 玻璃心形描边透明度约 0.70
- [ ] 玻璃质感有层次感（非单一透明度平铺）

---

## 视觉重量（Visual Weight）

- [ ] 英雄区（天空+心形）视觉重量轻盈，不压制下方内容
- [ ] 角色名称视觉重量最重（Bold 最大字号），扫视时最先注意到
- [ ] SelectedIndicator（粉色圆勾）视觉上明显区分已选/未选状态
- [ ] 确认按钮在底部有足够视觉吸引力，不被忽略
- [ ] 性格标签（御姐型/元气型）视觉存在但不喧宾夺主

---

## 对齐（Alignment）

- [ ] 导航标题水平居中于屏幕
- [ ] 玻璃心形水平居中于英雄区
- [ ] 卡片内头像与文字区顶部对齐（Align Start）
- [ ] 名字行内名称与标签垂直居中对齐
- [ ] 确认按钮水平居中于底部 CTA 区
- [ ] HomeIndicator 水平居中
- [ ] 所有卡片左右边缘与页面 16 pt padding 对齐

---

## Safe Area 遵守

- [ ] 状态栏内容在 Safe Area Top 47 pt 范围内
- [ ] ConfirmButton 底部边缘在 Safe Area Bottom 34 pt 上方（不侵入 Home Indicator 区域）
- [ ] HomeIndicator 条位于 Safe Area Bottom 区域内
- [ ] 导航栏不遮挡状态栏内容

---

## 底部栏（Bottom Bar）

- [ ] ConfirmCTABar 背景色不透明（#FFF8F3），遮挡滚动的卡片内容
- [ ] ConfirmButton 渐变方向正确（左 → 右）
- [ ] ConfirmButton 按压态有轻微 scale 缩小（0.97）
- [ ] HomeIndicator 正确显示在 ConfirmCTABar 下方

---

## 状态指示器

- [ ] 已选中的角色卡片，右上角显示实心粉色圆形 + 白色勾（SelectedIndicator）
- [ ] 未选中的角色卡片，右上角显示描边"选择"按钮（SelectButton）
- [ ] 同一时刻只有一张卡片处于选中态
- [ ] 进入页面时，第一张卡（神无月 凛）默认处于选中态
- [ ] 性格标签颜色：御姐型为紫色系，元气型为蓝色系，两者视觉可区分

---

## 颜色符合 Design Token

- [ ] 页面背景色 = `color-surface` (#FFF8F3)，未使用纯白 #FFFFFF 作为背景
- [ ] 卡片背景色 = `color-card` (#FFFFFF)
- [ ] 主色 = `color-primary` (#FFB7C5)，应用于按钮渐变终点、标签、SelectedIndicator
- [ ] 深粉色 = `color-primary-deep` (#FF8FAB)，应用于按钮渐变起点
- [ ] 未使用任何未在 Design Token 中定义的颜色

---

## 应用名拼写

- [ ] 本页面如有显示应用名，必须为 "yuoyuo"（全小写，无空格，无大写）
- [ ] 本页面未见应用名显示（仅见 UI 内容），此条通过

---

## 整体视觉一致度评估

- [ ] 整体风格符合"二次元 healing + 玻璃拟态 + 梦幻渐变"定义
- [ ] 整体配色与 yuoyuo 品牌色系一致（cherry pink 主导，sky blue/lavender 辅助）
- [ ] 字体统一，无混用其他字体
- [ ] 所有圆角使用预定义 token 值，无随意圆角
- [ ] 图标风格统一（线条型，非填充型）
- [ ] 视觉重量层级清晰：天空 < 卡片 < 名称 < 按钮 CTA

**验收通过标准：**
- 全部 □ 项通过：视觉一致度 100%（极佳）
- ≥ 90% □ 项通过：视觉一致度 ≥ 95%（可发布）
- < 90% □ 项通过：需返工修正后重新验收
