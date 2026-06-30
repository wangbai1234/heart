# 02 Layout — 设置页 Settings

## 画布信息
- 设计画布尺寸：1024 × 1536 px
- 对应设备：iPhone 14（390 × 844 pt，@3x）
- 逻辑尺寸参考：390 × 844 pt（以下尺寸均为逻辑 pt，除非特别注明）
- Safe Area Top：47 pt（含状态栏 44 pt + 1 pt 内边距，估算值）
- Safe Area Bottom：34 pt

---

## 层级架构

```
Layer 0  — Background（全屏渐变 + 光晕装饰）
Layer 1  — SafeArea Content
  ├── StatusBar（系统状态栏，9:41，信号/WiFi/电池）
  ├── NavigationBar（返回 + 标题"设置"）
  └── ScrollView（可垂直滚动）
       ├── ProfileCard
       ├── SectionLabel "我的会员"
       ├── GroupCard 会员组
       │    ├── Row 会员兑换（带 chevron-down）
       │    └── Row 订阅状态（带日期 + chevron-right）
       ├── SectionLabel "外观"
       ├── GroupCard 外观组
       │    ├── Row 主题（Segment Picker）
       │    └── Row 字体大小（Slider）
       ├── SectionLabel "通知"
       ├── GroupCard 通知组
       │    ├── Row 积极提醒（Toggle ON）
       │    └── Row 静音（时段 + chevron-right）
       ├── SectionLabel "隐私与数据"
       ├── GroupCard 隐私组
       │    ├── Row 清除网格服务器（chevron-right）
       │    ├── Row 导出我的数据（chevron-right）
       │    └── Row 注销账号（警示粉色 + chevron-right）
       ├── SectionLabel "关于"
       └── GroupCard 关于组
            ├── Row 版本 1.0.0（chevron-right）
            ├── Row 用户协议 / 隐私政策（chevron-right）
            └── Row 联系我们（chevron-right）
```

---

## 区域尺寸规范

### 状态栏（StatusBar）
- 高度：44 pt（估算值）
- 背景：透明（通透背景）
- 内容：左侧时间 "9:41"（黑色，SF Pro Rounded Bold ~15pt），右侧信号/WiFi/电池图标

### 导航栏（NavigationBar）
- 高度：44 pt（估算值）
- 背景：透明
- 左侧返回按钮：`<` 符号，约 24×24 pt，距左边缘 ~20 pt（估算值）
- 标题"设置"：居中，PingFang SC Medium，约 18 pt，颜色 #3A3A4A（估算值）
- 与 StatusBar 合计顶部占用 ~88 pt（估算值）

### Profile 卡（ProfileCard）
- 宽度：全宽 - 水平 margin 各 16 pt，即约 358 pt（估算值）
- 高度：约 96 pt（估算值）
- 圆角：约 20 pt（估算值）
- 内部 Padding：水平 16 pt，垂直 16 pt（估算值）
- 头像：直径约 60 pt 圆形（估算值）
- 头像右侧间距：约 14 pt（估算值）
- 名字"晨曦"：约 17 pt Bold（估算值）
- 会员标签：位于名字下方，约 8 pt 间距，高度约 22 pt，圆角约 11 pt（估算值），水平 Padding 约 10 pt
- 右侧 chevron：约 20 pt，居垂直中心

### 分组标题（SectionLabel）
- 字号：约 12 pt（估算值）
- 颜色：约 #8A8A9A 灰色（估算值）
- 左对齐，与卡片左边缘对齐（x ~16 pt）
- 上方间距（与上一个卡片）：约 16 pt（估算值）
- 下方间距（与卡片）：约 6–8 pt（估算值）

### GroupCard（分组卡片）
- 宽度：全宽 - 左右各 16 pt margin，约 358 pt（估算值）
- 圆角：约 20 pt（估算值）
- 背景：白色或接近白色，约 rgba(255,255,255,0.85)（估算值）
- 内部 Row 之间以细线（约 0.5 pt #E5E0EA）分隔（估算值）
- Card 上下之间间距（Section间）：约 8–12 pt（估算值）

### 设置行（SettingRow）
- 高度：约 54 pt（估算值）
- 内部左 Padding：约 16 pt（估算值）
- 内部右 Padding：约 16 pt（估算值）
- Icon 尺寸：约 22×22 pt（估算值），颜色与主题相关（粉色/玫瑰色）
- Icon 右侧间距：约 14 pt（估算值）
- 标签文字：约 15–16 pt Regular/Medium（估算值）
- 右侧辅助内容区域：副文字 + chevron / Toggle / Segment Picker

### 主题 Segment Picker（行内）
- 宽度：约 180 pt（估算值）
- 高度：约 34 pt（估算值）
- 3个选项：浅色/深色/自动，均分
- 选中态（浅色）：白色背景，带轻微阴影（估算值）
- 圆角：约 10 pt（估算值）
- 字号：约 13 pt（估算值）

### 字体大小 Slider（行内）
- 宽度：从小A图标到大A图标之间，约 220 pt（估算值）
- Track 高度：约 4 pt（估算值）
- Thumb 直径：约 22 pt（估算值），粉色填充
- 当前位置：约在轨道60%处（估算值）
- 小A字号：约 11 pt；大A字号：约 17 pt（估算值）

### Toggle（积极提醒）
- 宽度：约 51 pt，高度约 31 pt（iOS 标准）（估算值）
- 当前状态：ON（粉色 track + 白色 thumb）
- Track 颜色（ON）：#FFB7C5 → 渐变 #FF85A1（估算值）

### 页面总高度（估算）
- 状态栏 + 导航栏：~88 pt
- Profile 卡区：~96 pt + 16 pt margin top
- 会员组：section label ~18 pt + 16 pt gap + card ~108 pt
- 外观组：section label ~18 pt + gap + card ~108 pt
- 通知组：section label ~18 pt + gap + card ~108 pt
- 隐私组：section label ~18 pt + gap + card ~162 pt
- 关于组：section label ~18 pt + gap + card ~162 pt
- 底部 padding：~40 pt
- 总计：约 1200 pt（超出 844 pt，需滚动）（估算值）

---

## Padding / Margin / Gap 规范

| 位置 | 数值（估算值） |
|------|--------------|
| 页面水平左右 margin | 16 pt |
| ScrollView 顶部 padding（导航栏下方） | 16 pt |
| ScrollView 底部 padding | 40 pt |
| 卡片之间 vertical gap | 8–12 pt |
| Section Label 与下方卡片 gap | 6–8 pt |
| Section Label 与上方卡片 gap | 16 pt |
| 卡片内部行 height | 54 pt |
| 卡片内部左右 padding | 16 pt |
| Row 内 Icon 与文字 gap | 14 pt |
| Row 内 Divider 左 inset（从文字起始位置） | 52 pt（估算值） |

---

## 滚动区域
- 整个 ScrollView 区域可垂直滚动
- 无水平滚动
- ScrollView 起始：导航栏底部（~88 pt）
- 无固定底部 Tab 栏（本页为二级页，无 Tab Bar）
- iOS 弹性滚动（rubber-band）
- 无分页（pagingEnabled = false）

---

## Z-index 层级

| 层级 | 内容 |
|------|------|
| z=0 | 背景渐变 + 光晕装饰（最底层） |
| z=1 | ScrollView 内容（卡片等） |
| z=10 | NavigationBar（导航栏，固定于顶部） |
| z=20 | StatusBar（系统层，始终最上） |

---

## 背景层级
- 全屏渐变：从顶部浅粉色 → 中部浅薰衣草紫 → 底部紫粉色
- 底部左下角：光晕圆形装饰（模糊紫色），约 200 pt 直径（估算值）
- 整体背景作为 Page 最底层，不随 ScrollView 滚动（固定背景）
