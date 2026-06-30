# 07 组件树 — Style Tile（视觉总谱）

> 完整 ASCII 树形结构，覆盖 PNG 中所有可见元素。
> 括号内为组件名建议；带 * 号为可复用组件。

---

## 完整组件树

```
StyleTileCanvas（画布根节点）
│
├── BackgroundLayer（背景层，z=0）
│   ├── GradientBackground（暖粉渐变底色 #FFF8F3 → #FFD6DD）
│   └── DecorationParticles（装饰粒子层）
│       ├── SakuraPetal × 4（樱花花瓣，右上角散落）
│       └── SparklePoint × 5（四角星 / 圆点，右上角区域）
│
├── AppLogo *（"yuoyuo" 品牌文字，左上角，z=15）
│
├── ContentGrid（2列卡片网格，z=10）
│   │
│   ├── ─── Row 1 ──────────────────────────────────────────
│   │
│   ├── SectionCard [1. 调色板]（左上卡片）
│   │   ├── SectionLabel（"1. 调色板" 标题文字）
│   │   └── ColorSwatchRow（颜色椭圆横排容器）
│   │       ├── ColorSwatch * [cherry-pink]（#FFB7C5，宽~70px × 高~90px）
│   │       │   └── HexLabel（"#FFB7C5"）
│   │       ├── ColorSwatch * [sky-blue]（#A7C7E7）
│   │       │   └── HexLabel（"#A7C7E7"）
│   │       ├── ColorSwatch * [lavender]（#C8B6FF）
│   │       │   └── HexLabel（"#C8B6FF"）
│   │       ├── ColorSwatch * [cream]（#FFF8F3）
│   │       │   └── HexLabel（"#FFF8F3"）
│   │       ├── ColorSwatch * [charcoal]（#3A3A4A）
│   │       │   └── HexLabel（"#3A3A4A"）
│   │       └── ColorSwatch * [glass]（rgba(255,255,255,.55)，带边框）
│   │           └── HexLabel（"rgba(255,\n255,255,.55)"）
│   │
│   ├── SectionCard [2. 字体]（右上卡片）
│   │   ├── SectionLabel（"2. 字体" 标题文字）
│   │   └── TypographyShowcase
│   │       ├── TypeRow [display-chinese]
│   │       │   └── Text（"你今天还好吗"，~40px Bold，PingFang SC）
│   │       ├── TypeRow [body-chinese]
│   │       │   ├── Text（"你今天还好吗"，~16px Regular）
│   │       │   └── TextMeta（"PingFang SC Regular"，~13px，secondary color）
│   │       ├── TypeRow [title-latin]
│   │       │   └── Text（"Hello, yuoyuo."，~20px Bold，SF Pro Rounded）
│   │       └── TypeRow [body-latin]
│   │           └── TextMeta（"SF Pro Rounded"，~13px，secondary color）
│   │
│   ├── ─── Row 2 ──────────────────────────────────────────
│   │
│   ├── SectionCard [3. 气泡]（左中卡片）
│   │   ├── SectionLabel（"3. 气泡" 标题文字）
│   │   ├── BubblePairContainer（气泡对容器）
│   │   │   ├── ChatBubbleAI *（AI 左侧气泡，白色半透明背景）
│   │   │   │   ├── SenderName（"yuoyuo"，粉色，~12px SemiBold）
│   │   │   │   ├── MessageText（"早呀，今天也要开心地度过呢～✨"，~14px Regular）
│   │   │   │   └── Timestamp（"09:30"，~10px，secondary color）
│   │   │   └── ChatBubbleUser *（用户右侧气泡，天蓝背景）
│   │   │       ├── MessageText（"谢谢yuoyuo，你真是最好的陪伴！"，~14px Regular）
│   │   │       └── TimestampWithTick
│   │   │           ├── Timestamp（"09:32"，~10px）
│   │   │           └── CheckTick（"✓"，蓝色）
│   │   └── BubbleLabels（底部说明文字行）
│   │       ├── Label（"AI（左侧）"，~11px，secondary color）
│   │       └── Label（"用户（右侧）"，~11px，secondary color）
│   │
│   ├── SectionCard [4. 按钮]（右中卡片）
│   │   ├── SectionLabel（"4. 按钮" 标题文字）
│   │   └── ButtonStack（按钮竖向堆叠容器）
│   │       ├── ButtonPrimary *（"确认"，樱花粉渐变，胶囊形，~200×48px）
│   │       │   └── ButtonLabel（"确认"，白色，~16px SemiBold）
│   │       ├── ButtonSecondary *（"取消"，白色背景，胶囊形，~200×48px）
│   │       │   └── ButtonLabel（"取消"，charcoal，~16px Regular）
│   │       └── ButtonTextLink *（"了解更多"，薰衣草紫文字，无背景）
│   │           └── ButtonLabel（"了解更多"，#C8B6FF，~14px Regular）
│   │
│   ├── ─── Row 3 ──────────────────────────────────────────
│   │
│   ├── SectionCard [5. 卡片]（左下区块）
│   │   ├── SectionLabel（"5. 卡片" 标题文字）
│   │   └── CharacterCard *
│   │       ├── CharacterCardHeader（头像 + 基本信息横排）
│   │       │   ├── AvatarContainer（头像底盘圆形，~96px，淡粉白渐变）
│   │       │   │   └── CharacterAvatar *（二次元少女插画，~88px 圆形裁切）
│   │       │   └── CharacterInfo（信息列，flex-column）
│   │       │       ├── CharacterNameRow（名称 + 等级横排）
│   │       │       │   ├── CharacterName（"yuoyuo"，~18px SemiBold，ink）
│   │       │       │   └── LevelBadge *（"Lv.12"，粉底徽章，~12px，radius-sm）
│   │       │       ├── CharacterBio（"与你相遇，是最美好的奇迹。"，~13px，secondary）
│   │       │       └── StatsRow（统计数据横排）
│   │       │           ├── StatItem *（爱心图标 + "1250" + "陪伴天数"）
│   │       │           │   ├── StatIcon（HeartIcon *，#FFB7C5，~14px）
│   │       │           │   ├── StatNumber（"1250"，~16px Bold，ink）
│   │       │           │   └── StatLabel（"陪伴天数"，~11px，secondary）
│   │       │           └── StatItem *（星星图标 + "3560" + "温暖时刻"）
│   │       │               ├── StatIcon（StarIcon *，淡紫，~14px）
│   │       │               ├── StatNumber（"3560"，~16px Bold，ink）
│   │       │               └── StatLabel（"温暖时刻"，~11px，secondary）
│   │       └── CharacterMotto（"✨ 愿每一天都充满温柔与惊喜。"，~12px，底部横跨全宽）
│   │
│   └── SectionCard [6. 图标条]（右下区块）
│       ├── SectionLabel（"6. 图标条" 标题文字）
│       └── BottomNavBar *（底部导航图标条展示）
│           ├── NavTabItem *（首页）
│           │   ├── NavIcon（HomeIcon，outline，~24px，secondary color）
│           │   └── NavLabel（"首页"，~11px，secondary color）
│           ├── NavTabItem *（聊天）
│           │   ├── NavIcon（ChatIcon，outline，~24px）
│           │   └── NavLabel（"聊天"，~11px）
│           ├── NavTabItem *（麦克风，关闭）
│           │   ├── NavIcon（MicOffIcon，outline，~24px）
│           │   └── NavLabel（"麦克风\n（关闭）"，~11px）
│           ├── NavTabItem *（礼物，兑换）
│           │   ├── NavIcon（GiftIcon，outline，~24px）
│           │   └── NavLabel（"礼物\n（兑换）"，~11px）
│           ├── NavTabItem *（齿轮）
│           │   ├── NavIcon（SettingsIcon，outline，~24px）
│           │   └── NavLabel（"齿轮"，~11px）
│           └── NavTabItem *（个人资料）
│               ├── NavIcon（ProfileIcon，outline，~24px）
│               └── NavLabel（"个人资料"，~11px）
│
└── IllustrationBackground *（底部全宽梦幻插画，z=1）
    ├── CastleIllustration（城堡建筑背景，远景）
    ├── FlowerCluster（前景花朵群组，粉色 + 蓝紫色）
    └── ButterflyDecoration（蝴蝶装饰，约 2 只）
```

---

## 组件层级说明

| 层级 | 组件类型 | 说明 |
|------|----------|------|
| L0 | `StyleTileCanvas` | 根容器，仅用于此文档 |
| L1 | `BackgroundLayer` / `ContentGrid` / `IllustrationBackground` | 布局分区 |
| L2 | `SectionCard` / `AppLogo` | 可复用容器 |
| L3 | 各区块具体组件（`CharacterCard`, `BottomNavBar` 等）| 核心业务组件 |
| L4 | 原子组件（`ColorSwatch`, `NavIcon`, `StatItem` 等） | 最小复用单元 |

---

## 带 * 可复用组件汇总（按优先级）

```
P0 核心（立即实现）：
  AppLogo
  ChatBubbleAI
  ChatBubbleUser
  ButtonPrimary
  ButtonSecondary
  ButtonTextLink
  BottomNavBar / NavTabItem

P1 重要（第二阶段）：
  CharacterCard
  CharacterAvatar
  LevelBadge
  StatItem / StatIcon
  SectionCard

P2 支持（第三阶段）：
  ColorSwatch
  IllustrationBackground
  HeartIcon / StarIcon
  DecorationParticles
```
