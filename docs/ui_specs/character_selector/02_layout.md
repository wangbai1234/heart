# 02 Layout — 角色页 Character Selector

## 画布规格
- 设计画布：1024 × 1536 px
- 逻辑设备：iPhone 14，390 × 844 pt（@3x 分辨率）
- Safe Area Top：47 px（逻辑）
- Safe Area Bottom：34 px（逻辑）
- 以下所有尺寸均为逻辑像素（pt），估算值已标注

---

## 层级总览（从底到顶，Z 轴）

| Z 层 | 区域 | 说明 |
|------|------|------|
| 0 | Page Background | 全页奶油底色 #FFF8F3 |
| 1 | Hero Background Image | 天空动漫背景图（渐变粉紫） |
| 2 | Hero Overlay | 轻微白色渐变叠加，底部过渡到页面背景色 |
| 3 | Glass Heart Icon | 玻璃心形图标，浮于天空英雄区中央 |
| 4 | Character Cards | 白色圆角卡片列表，覆盖英雄区底部 |
| 5 | Status Bar | 顶部系统状态栏 |
| 6 | Header Bar | 标题栏（半透明） |
| 7 | Bottom CTA Bar | 底部确认按钮区（固定定位） |
| 8 | Home Indicator | 系统 Home 条 |

---

## 1. 状态栏（Status Bar）

- 高度：47 pt（含 Safe Area Top）
- 内容：左侧时间"9:41"，右侧信号/WiFi/电池图标
- 背景：继承页面背景色 #FFF8F3（无独立背景）
- Padding Top：14 pt（估算值）
- 字号：约 15 pt，字重 Semibold

---

## 2. 顶部导航栏（Header Bar）

- 高度：44 pt
- Top 起始：47 pt（Safe Area 之后）
- 背景：无独立背景色，继承 #FFF8F3
- Padding Left/Right：20 pt
- 布局：Flex Row，三栏布局
  - 左区：∨（向下箭头图标），约 24 × 24 pt，点击关闭/返回
  - 中区：标题"选择一位陪伴你的人"，居中，Flex-grow
  - 右区：空（无按钮）

---

## 3. 英雄区（Hero Section）

- 顶部起始：91 pt（状态栏 47 + 导航栏 44）
- 高度：约 280 pt（估算值）
- 宽度：390 pt（全宽）
- 背景：动漫天空插画图，粉色/浅紫色渐变云层，底部向 #FFF8F3 柔和过渡
- 内容：
  - 玻璃心形图标，居中于英雄区上半部
  - 心形尺寸：约 120 × 110 pt（估算值）
  - 心形距英雄区顶部：约 40 pt（估算值）
- 底部过渡：底部约 60 pt 高度渐变至页面背景色，无硬边界

---

## 4. 角色卡列表区（Character Card List）

- 顶部起始：约 320 pt（覆盖英雄区底部）
- 底部结束：约 720 pt（距底部 CTA 上方）
- 宽度：390 pt
- Padding Left/Right：16 pt
- 内部 Gap（卡片间距）：12 pt
- 滚动方向：垂直滚动（ScrollView）
- 可见卡片数量：2 张（第三张需向下滚动）

### 4.1 角色卡（Character Card）

- 宽度：390 - 32 = 358 pt（含两侧 16 pt padding）
- 高度：约 200 pt（估算值，含内边距）
- 背景：白色 #FFFFFF，圆角 20 pt
- Shadow：rgba(0,0,0,0.06) Blur 12 pt, Offset Y 4 pt
- Padding 内部：16 pt 四周

#### 卡片内部布局（Flex Row）

- 左列：头像圆形区域
  - 宽高：约 120 × 120 pt（估算值）
  - 形状：Circle（border-radius 60 pt）
  - 包含：角色插图 + 彩色光晕描边
  
- 右列：文字内容区（Flex Column）
  - Flex-grow: 1
  - Padding Left（与头像间距）：12 pt
  
  - 行1（标题行）：Flex Row，Align Center，Gap 8 pt
    - 角色名称（如"神无月 凛"）：约 18 pt，Bold
    - 性格标签（如"御姐型"）：Tag 组件，见 04_components.md
    
  - 行2（描述文本区）：
    - Margin Top：8 pt
    - 字号：13 pt（估算值）
    - 行高：1.6（估算值）
    - 颜色：#3A3A4A（Ink，略降透明度）
    - 最大行数：不截断（全文显示）
    
  - 右上角操作按钮：绝对定位于卡片右上角
    - 已选中：实心粉色圆形（约 40 × 40 pt），白色勾图标
    - 未选中：描边粉色圆角矩形"选择"按钮，约 68 × 36 pt

---

## 5. 底部确认按钮区（Bottom CTA Bar）

- 位置：固定底部，覆盖 Safe Area Bottom
- 高度：80 pt（含 Safe Area Bottom 34 pt）
- 背景：继承页面背景色 #FFF8F3
- Padding Left/Right：20 pt
- Padding Top：12 pt
- Padding Bottom：34 pt（Safe Area Bottom）

### 5.1 确认按钮（Confirm Button）

- 宽度：全宽 - 40 pt = 350 pt
- 高度：54 pt
- 背景：粉色渐变（从左至右，#FF8FAB → #FFB7C5）
- 圆角：27 pt（胶囊形）
- 文字："确认选择"，白色，约 17 pt，Semibold，居中
- Shadow：rgba(255,135,171,0.35) Blur 16 pt, Offset Y 6 pt

---

## 6. 底部 Home Indicator

- 高度：34 pt（iOS Safe Area Bottom）
- 内容：深灰色横条，约 130 × 5 pt，居中，圆角
- 背景：继承页面背景

---

## 滚动区域说明

- 角色卡列表为垂直滚动 ScrollView
- 英雄区不滚动（固定在顶部，或随滚动向上消失）
- 底部 CTA 区固定定位，不随内容滚动
- 状态栏和导航栏固定于顶部

---

## Spacing / Padding 汇总（估算值）

| 区域 | 值 |
|------|----|
| Page Horizontal Padding | 16 pt |
| Card Internal Padding | 16 pt |
| Card Gap | 12 pt |
| Header Padding LR | 20 pt |
| Bottom CTA Padding LR | 20 pt |
| Avatar - Text Gap | 12 pt |
| Title Row Gap | 8 pt |
| Title - Description Gap | 8 pt |
