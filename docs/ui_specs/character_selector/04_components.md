# 04 Components — 角色页 Character Selector

---

## 1. StatusBar（系统状态栏）

- 组件名称：StatusBar
- 作用：显示系统时间、网络信号、WiFi、电池
- 层级：最顶层 Z-index 100
- 尺寸：390 × 47 pt（含 Safe Area）
- 布局：Flex Row，SpaceBetween
  - 左：时间"9:41"，15 pt Semibold
  - 右：信号（3格）、WiFi（扇形）、电池（满格）图标组，间距 6 pt
- 状态：系统组件，不可交互
- 样式：无独立背景，继承页面色 #FFF8F3

---

## 2. NavigationBar（顶部导航栏）

- 组件名称：NavigationBar
- 作用：提供页面标题和返回操作
- 层级：固定顶部，Z-index 90
- 尺寸：390 × 44 pt
- 布局：Flex Row，AlignCenter，三区布局
  - 左区（44 × 44 pt touch target）：DismissButton 组件
  - 中区（Flex-grow）：PageTitle 组件，居中
  - 右区：空（约 44 pt 宽度占位，保持标题视觉居中）
- 状态：固定，无滚动
- 背景：透明，继承 #FFF8F3

### 2.1 DismissButton（关闭/返回按钮）

- 图标：∨（向下 chevron），约 20 × 20 pt，线宽约 2 pt
- 颜色：#3A3A4A（Ink）
- Touch Target：44 × 44 pt
- 状态：Default / Pressed（opacity 0.6 + scale 0.9）
- 交互：点击 → dismiss 当前 modal 页面，返回上一屏

### 2.2 PageTitle（页面标题）

- 文字："选择一位陪伴你的人"
- 字号：17 pt，Medium 500
- 颜色：#3A3A4A
- 对齐：水平居中
- 状态：静态文本

---

## 3. HeroSection（天空英雄区）

- 组件名称：HeroSection
- 作用：视觉引导，建立梦幻氛围，品牌符号展示
- 层级：Z-index 10，位于卡片列表之下
- 尺寸：390 × 约 280 pt（估算值）
- 布局：相对定位容器，子元素绝对定位
- 内部元素：
  - BackgroundImage：动漫天空插画，全覆盖
  - BottomFadeOverlay：底部渐变叠加，height 约 80 pt
  - GlassHeart：玻璃心形图标，居中定位

### 3.1 HeroBackgroundImage（英雄区背景图）

- 尺寸：390 × 约 280 pt（全宽，估算值）
- 内容：动漫风格天空，粉色/紫色/橙色渐变云层，月亮（右上角白色圆），樱花光效
- 渲染方式：图片资源（非 CSS 渐变）
- 状态：静态图片

### 3.2 GlassHeart（玻璃心形图标）

- 组件名称：GlassHeart
- 作用：品牌核心符号，视觉焦点
- 尺寸：约 120 × 110 pt（估算值）
- 位置：英雄区水平居中，距顶约 40 pt（估算值）
- 样式：
  - 心形轮廓
  - 填充：rgba(255,255,255,0.55) + 内部粉紫渐变光晕
  - 描边：rgba(255,255,255,0.70)，约 1.5 pt
  - Backdrop Blur：8 pt（估算值）
  - Drop Shadow：rgba(255,182,193,0.3) Blur 20 pt
- 状态：Default / 轻微浮动动画（推测）
- 无直接交互

---

## 4. CharacterCardList（角色卡列表容器）

- 组件名称：CharacterCardList
- 作用：可滚动的角色卡片列表
- 布局：垂直 ScrollView，Flex Column，Gap 12 pt
- Padding：水平 16 pt，顶部约 12 pt（与英雄区重叠约 40 pt 以实现叠加效果）
- 滚动：垂直，可惯性滚动，无水平滚动
- 状态：正常 / 滚动中

---

## 5. CharacterCard（角色卡片）

- 组件名称：CharacterCard
- 作用：展示单个角色信息，支持选中操作
- 尺寸：358 × 约 200 pt（估算值，高度由内容决定）
- 背景：#FFFFFF，圆角 20 pt
- Shadow：rgba(0,0,0,0.06) Blur 12 pt, Y +4 pt
- 内部 Padding：16 pt 四周
- 布局：Flex Row，AlignStart（顶部对齐）

### 状态

| 状态 | 样式变化 |
|------|---------|
| Default（未选中） | 白色背景，无特殊描边，右上角显示"选择"描边按钮 |
| Selected（已选中） | 白色背景，右上角变为实心粉色勾选圆圈 |
| Pressed | scale 0.98，shadow 变小，持续 150 ms |
| Disabled | 不适用（所有角色可选） |

### 5.1 CharacterAvatar（角色头像容器）

- 组件名称：CharacterAvatar
- 作用：显示角色插画，带光晕描边标识角色
- 尺寸：约 120 × 120 pt（估算值）
- 形状：圆形（border-radius: 9999 pt）
- 内容：角色插画图片，object-fit: cover
- 光晕描边：
  - 神无月 凛：紫色（#C8B6FF）渐变光晕描边，约 3 pt，+ 外发光 Blur 8 pt
  - 桃乐丝：蓝色（#A7C7E7）渐变光晕描边，约 3 pt，+ 外发光 Blur 8 pt
- 内部背景渐变：配合角色主色调（紫色/蓝色深色背景）

### 5.2 CharacterInfo（角色信息区）

- 布局：Flex Column，AlignStart，Flex-grow 1，Padding Left 12 pt

#### CharacterNameRow（名字行）

- 布局：Flex Row，AlignCenter，Gap 8 pt
- 角色名称：约 18 pt Bold，颜色 #1A1A2E（估算值）
- PersonalityTag 组件（见下）

#### PersonalityTag（性格标签）

- 组件名称：PersonalityTag
- 作用：简明标注角色性格类型
- 布局：Inline Flex，Padding 3 pt 8 pt（估算值）
- 圆角：12 pt（pill 形）
- 尺寸：约 48 × 22 pt（估算值）

| 角色 | 标签文字 | 背景色 | 文字颜色 |
|------|---------|--------|---------|
| 神无月 凛 | 御姐型 | rgba(200,182,255,0.3) | #8B5CF6（估算值） |
| 桃乐丝 | 元气型 | rgba(167,199,231,0.3) | #3B82F6（估算值） |

#### CharacterDescription（角色描述文本）

- Margin Top：8 pt
- 字号：13 pt，Regular 400
- 行高：1.6（估算值）
- 颜色：rgba(58,58,74,0.75)
- 全文显示，不截断

### 5.3 SelectButton（选择按钮，未选中态）

- 组件名称：SelectButton (Unselected)
- 位置：绝对定位，卡片右上角，Padding 16 pt
- 尺寸：约 68 × 36 pt（估算值）
- 圆角：18 pt（胶囊）
- 背景：透明
- 描边：1.5 pt solid #FFB7C5
- 文字："选择"，约 15 pt，Medium 500，颜色 #FFB7C5
- 状态：Default / Pressed（背景 rgba(255,183,197,0.15)）

### 5.4 SelectedIndicator（已选中指示器）

- 组件名称：SelectedIndicator
- 位置：绝对定位，卡片右上角，Padding 16 pt
- 尺寸：约 40 × 40 pt
- 形状：圆形（border-radius 9999 pt）
- 背景：#FFB7C5（实心粉色）
- 内容：白色勾图标，约 18 × 14 pt，stroke 2.5 pt
- Shadow：rgba(255,183,197,0.4) Blur 8 pt

---

## 6. ConfirmCTABar（底部确认按钮区）

- 组件名称：ConfirmCTABar
- 作用：固定底部的主操作区，触发选择确认
- 位置：fixed bottom 0
- 尺寸：390 × 80 pt（含 Safe Area 34 pt）
- 背景：#FFF8F3（不透明，遮挡滚动内容）
- Padding：Top 12 pt，LR 20 pt，Bottom 34 pt（Safe Area）

### 6.1 ConfirmButton（确认选择按钮）

- 组件名称：ConfirmButton
- 作用：触发最终选择确认，进入聊天主页
- 尺寸：350 × 54 pt
- 圆角：27 pt（胶囊）
- 背景：线性渐变 #FF8FAB → #FFB7C5（Left to Right）
- 文字："确认选择"，17 pt Semibold，白色，居中
- Shadow：rgba(255,143,171,0.35) Blur 16 pt, Y +6 pt
- 状态：
  - Default：完整渐变 + shadow
  - Pressed：scale 0.97，shadow 减弱，150 ms
  - Disabled（无角色选中）：opacity 0.5，shadow 消失（推测，设计稿未体现）

---

## 7. HomeIndicator（系统底部条）

- 组件名称：HomeIndicator
- 作用：iOS 系统 Home Gesture 指示条
- 尺寸：130 × 5 pt，水平居中
- 圆角：2.5 pt（pill）
- 颜色：rgba(58,58,74,0.30)
- 位置：距底部 8 pt（估算值）
- 状态：系统组件，不可自定义交互

---

## 可复用组件建议

| 组件 | 复用理由 |
|------|---------|
| PersonalityTag | 多个角色均需标签，且颜色可通过 prop 传入；其他页面（角色详情页）也需展示 |
| CharacterAvatar | 聊天页、个人设置页均需展示角色头像光晕 |
| SelectButton / SelectedIndicator | 可封装为 SelectableControl，统一选中/未选中状态管理 |
| ConfirmButton | 全局胶囊主操作按钮，同款按钮在注册流程、设置页等均会出现 |
| GlassHeart | 品牌图标，欢迎页/空状态页可复用 |
| NavigationBar | 全局顶部导航，可提取为 AppBar 组件 |
