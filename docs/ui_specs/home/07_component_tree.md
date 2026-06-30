# 07 Component Tree — 首页 Home

完整 ASCII 组件树，从 Page 根节点开始，覆盖所有可见元素（含装饰性元素）。

```
Page (390 × 844 pt, 全局奶油粉背景 #FFF0F3)
│
├── Background (z-0)
│   └── SolidFill (#FFF0F3, 全屏覆盖)
│
├── StatusBar (z-20, 高度 47pt, iOS 系统原生)
│   ├── TimeLabel ("9:41", 左对齐, #3A3A4A)
│   └── SystemIcons (右对齐, 信号+WiFi+电池)
│
├── ScrollView (z-1, y-start: 47pt, y-end: ~761pt, 可垂直滚动)
│   │
│   ├── AppBar (高度 ~56pt, px-20-left px-16-right)
│   │   ├── AppNameLabel ("yuoyuo", SF Pro Rounded Bold ~26pt, #3A3A4A)
│   │   └── UserAvatarButton (圆形 ~40pt, 点击→个人中心)
│   │       └── AvatarImage (角色插图, 圆形裁剪, 有粉色 glow)
│   │
│   ├── HeroCard (358×~280pt, 圆角 24pt, mx-16pt, 云彩背景)
│   │   ├── CloudBackgroundImage (充满卡片, 粉紫云彩渐变插图)
│   │   │   ├── SkyGradientLayer (多色渐变底层: 暖黄→粉→浅紫)
│   │   │   ├── SunGlowDecoration (右上角白色圆形光源)
│   │   │   ├── CloudDecoration_Left (左侧白色云朵)
│   │   │   └── CloudDecoration_Right (右侧白色云朵)
│   │   │
│   │   ├── HeartOrb (心形宝珠, ~120×130pt, 水平居中, 距顶 ~28pt)
│   │   │   ├── OrbBody (心形渐变: 粉→蓝紫, 玻璃质感)
│   │   │   ├── OrbHighlight_Primary (左上椭圆高光, rgba白 80%)
│   │   │   ├── OrbHighlight_Secondary (右下次高光, rgba白 40%)
│   │   │   └── OrbGlowAura (外发光光晕, 紫色径向, blur ~40pt)
│   │   │
│   │   ├── CardInfoOverlay (信息区, 卡片下半部, 玻璃叠加层)
│   │   │   ├── GlassBlurLayer (backdrop-filter blur ~16pt, rgba白 60%)
│   │   │   ├── CompanionNameLabel ("神无月凛", ~22pt SemiBold, #3A3A4A, 居中)
│   │   │   ├── CompanionStatusLabel ("刚刚和你聊过 · 心情：温柔", ~13pt, #8E8E9A, 居中)
│   │   │   └── StartChatButton (右下角, ~120×38pt, 圆角 16pt)
│   │   │       ├── ButtonBackground (rgba白 85%, 圆角 16pt)
│   │   │       └── ButtonLabel ("开始聊天 →", ~15pt Medium, #FF7A9A)
│   │   │
│   │   └── CardShadow (阴影层, 粉色 blur ~20pt, 卡片外部)
│   │
│   ├── QuickActionsRow (高度 ~90pt, mx-16pt, mt-~16pt)
│   │   ├── QuickActionTile_Member (兑换会员, ~111×90pt, 圆角 16pt)
│   │   │   ├── TileBackground (rgba白 80%, 毛玻璃, 边框 rgba粉 20%)
│   │   │   ├── GiftIcon (~32×32pt, 礼品盒线性图标, #FFB7C5)
│   │   │   └── TileLabel ("兑换会员", ~13pt Regular, #3A3A4A)
│   │   │
│   │   ├── QuickActionTile_Character (切换角色, ~111×90pt, 圆角 16pt)
│   │   │   ├── TileBackground (rgba白 80%, 毛玻璃, 边框 rgba粉 20%)
│   │   │   ├── CharacterIcon (~32×32pt, 人形轮廓线性图标, #C8B6FF)
│   │   │   └── TileLabel ("切换角色", ~13pt Regular, #3A3A4A)
│   │   │
│   │   └── QuickActionTile_Settings (设置, ~111×90pt, 圆角 16pt)
│   │       ├── TileBackground (rgba白 80%, 毛玻璃, 边框 rgba粉 20%)
│   │       ├── GearIcon (~32×32pt, 齿轮线性图标, #A7C7E7)
│   │       └── TileLabel ("设置", ~13pt Regular, #3A3A4A)
│   │
│   ├── RecentSection (mt-~20pt)
│   │   │
│   │   ├── SectionHeader (高度 ~36pt, 全宽)
│   │   │   ├── SectionTitleLabel ("最近的......", ~16pt Bold, #3A3A4A, px-20-left)
│   │   │   └── ViewAllLink ("查看全部 >", ~13pt Regular, #8E8E9A, px-16-right)
│   │   │
│   │   ├── ConversationListItem_1 (神无月凛, 高度 ~80pt)
│   │   │   ├── ItemBackground (透明, Pressed时 rgba粉 12%)
│   │   │   ├── CharacterAvatar_Shenwuyuelin (~56×56pt, 圆形)
│   │   │   │   ├── AvatarImage (黑紫发动漫少女)
│   │   │   │   └── AvatarBorder (1.5pt 粉紫描边)
│   │   │   ├── TextBlock (flex-1, ml-~14pt)
│   │   │   │   ├── NameLabel ("神无月凛", ~16pt SemiBold, #3A3A4A)
│   │   │   │   ├── PreviewLine1 ("今天过得怎么样呀?", ~14pt Regular, #8E8E9A)
│   │   │   │   └── PreviewLine2 ("有没有遇到什么开心的事~", ~14pt Regular, #8E8E9A)
│   │   │   └── MetaInfo (右对齐)
│   │   │       ├── TimeLabel ("22:18", ~13pt Regular, #8E8E9A)
│   │   │       └── UnreadDot (~8pt 圆形, #FFB7C5)
│   │   │
│   │   └── ConversationListItem_2 (桃乐丝, 高度 ~80pt)
│   │       ├── ItemBackground (透明, Pressed时 rgba粉 12%)
│   │       ├── CharacterAvatar_Taoles (~56×56pt, 圆形)
│   │       │   ├── AvatarImage (银灰发动漫少女)
│   │       │   └── AvatarBorder (1.5pt 粉紫描边)
│   │       ├── TextBlock (flex-1, ml-~14pt)
│   │       │   ├── NameLabel ("桃乐丝", ~16pt SemiBold, #3A3A4A)
│   │       │   ├── PreviewLine1 ("晚安呀, 记得多喝水, 明天见~", ~14pt Regular, #8E8E9A)
│   │       │   └── PreviewLine2 ("我会在这里等你哦。", ~14pt Regular, #8E8E9A)
│   │       └── MetaInfo (右对齐)
│   │           ├── TimeLabel ("昨天", ~13pt Regular, #8E8E9A)
│   │           └── UnreadDot (~8pt 圆形, #FFB7C5)
│   │
│   └── ScrollViewPadding (底部留白, 高度约 83pt 对应 Tab Bar 高度)
│
└── BottomTabBar (z-10, 固定底部, 高度 83pt, blur 背景)
    ├── TabBarBackground (rgba(255,248,243,0.92), backdrop-filter blur ~20pt)
    ├── TabBarTopBorder (0.5pt, rgba(0,0,0,0.08))
    │
    ├── TabItem_Home (Active, 宽 ~97.5pt)
    │   ├── HomeIcon (~24×24pt, #FFB7C5, 房屋图标)
    │   ├── TabLabel ("首页", ~10pt, #FFB7C5)
    │   └── ActiveIndicatorDot (~4pt 圆, #FFB7C5, 图标正下方)
    │
    ├── TabItem_Chat (Inactive, 宽 ~97.5pt)
    │   ├── ChatIcon (~24×24pt, #ADADB8, 气泡图标)
    │   └── TabLabel ("聊天", ~10pt, #ADADB8)
    │
    ├── TabItem_Character (Inactive, 宽 ~97.5pt)
    │   ├── CharacterIcon (~24×24pt, #ADADB8, 人形图标)
    │   └── TabLabel ("角色", ~10pt, #ADADB8)
    │
    └── TabItem_Settings (Inactive, 宽 ~97.5pt)
        ├── SettingsIcon (~24×24pt, #ADADB8, 齿轮图标)
        └── TabLabel ("设置", ~10pt, #ADADB8)
```

---

## 节点说明

| 图例 | 含义 |
|------|------|
| `(估算值)` 或 `~` 前缀 | 尺寸/间距为从设计稿视觉估算，非精确测量值 |
| `z-N` | Z 轴层级编号 |
| `mx-Npt` | 水平外边距 N pt |
| `mt-Npt` | 上外边距 N pt |
| `px-N-left/right` | 单侧内边距 |
| `rgba白 N%` | rgba(255,255,255,N%) |
| `rgba粉 N%` | rgba(255,183,197,N%) |
