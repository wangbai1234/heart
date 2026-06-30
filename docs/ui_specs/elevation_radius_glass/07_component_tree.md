# 07 组件树 — Shadow / Radius / Glass Sample

## ASCII 组件树（完整）

```
ReferenceCanvas [1024×1024]
│
├── PageBackground [z:0, 1024×1024]
│   └── CherryGlowOverlay [Radial Gradient, rgba(255,183,197,0.45), 右上角光晕]
│
├── MainContainerCard [z:1, 约940×920, radius.xl(32px), shadow.sheet]
│   │
│   ├── PageTitle [z:2, 左对齐]
│   │   └── Text "yuoyuo · 设计令牌参考" [28–32px, SemiBold, #3A3A4A]
│   │
│   ├── RadiusSection [z:2, Section 1]
│   │   │
│   │   ├── SectionHeading
│   │   │   ├── DotIcon [●, #FFB7C5, 约12px diameter]
│   │   │   └── Text "圆角半径（Radius）" [18–20px, Medium, #3A3A4A]
│   │   │
│   │   └── RadiusSwatchRow [Flex Row, gap≈16px]
│   │       │
│   │       ├── RadiusSwatch[radius=4px]
│   │       │   ├── WhiteBlock [约140×140px, border-radius:4px, shadow.card]
│   │       │   └── SwatchLabel "4px" [14px, Medium, #3A3A4A]
│   │       │
│   │       ├── RadiusSwatch[radius=8px]
│   │       │   ├── WhiteBlock [约140×140px, border-radius:8px, shadow.card]
│   │       │   └── SwatchLabel "8px" [14px, Medium, #3A3A4A]
│   │       │
│   │       ├── RadiusSwatch[radius=16px]
│   │       │   ├── WhiteBlock [约140×140px, border-radius:16px, shadow.card]
│   │       │   └── SwatchLabel "16px" [14px, Medium, #3A3A4A]
│   │       │
│   │       ├── RadiusSwatch[radius=24px]
│   │       │   ├── WhiteBlock [约140×140px, border-radius:24px, shadow.card]
│   │       │   └── SwatchLabel "24px" [14px, Medium, #3A3A4A]
│   │       │
│   │       └── RadiusSwatch[radius=32px]
│   │           ├── WhiteBlock [约140×140px, border-radius:32px, shadow.card]
│   │           └── SwatchLabel "32px" [14px, Medium, #3A3A4A]
│   │
│   ├── ElevationSection [z:2, Section 2]
│   │   │
│   │   ├── SectionHeading
│   │   │   ├── DotIcon [●, #FFB7C5, 约12px diameter]
│   │   │   └── Text "高度（Elevation）" [18–20px, Medium, #3A3A4A]
│   │   │
│   │   └── ElevationSwatchRow [Flex Row, gap≈16px]
│   │       │
│   │       ├── ElevationSwatch[level=0]
│   │       │   ├── WhiteBlock [约140×140px, radius:16px, shadow:none]
│   │       │   ├── SwatchLabel "平面 (0)" [14px, Medium, #3A3A4A]
│   │       │   └── SwatchDescription "无阴影" [12px, Regular, rgba(58,58,74,0.60)]
│   │       │
│   │       ├── ElevationSwatch[level=1, blur=6px, opacity=0.04]
│   │       │   ├── WhiteBlock [约140×140px, radius:16px, shadow:0 2px 6px rgba(0,0,0,0.04)]
│   │       │   ├── SwatchLabel "柔和 (6/0.04)" [14px, Medium, #3A3A4A]
│   │       │   └── SwatchDescription "阴影模糊 6px / 不透明度 0.04" [12px, Regular, rgba(58,58,74,0.60)]
│   │       │
│   │       ├── ElevationSwatch[level=2, blur=12px, opacity=0.06]
│   │       │   ├── WhiteBlock [约140×140px, radius:16px, shadow:0 4px 12px rgba(0,0,0,0.06)]
│   │       │   ├── SwatchLabel "卡片 (12/0.06)" [14px, Medium, #3A3A4A]
│   │       │   └── SwatchDescription "阴影模糊 12px / 不透明度 0.06" [12px, Regular, rgba(58,58,74,0.60)]
│   │       │
│   │       ├── ElevationSwatch[level=3, blur=24px, opacity=0.08]
│   │       │   ├── WhiteBlock [约140×140px, radius:16px, shadow:0 8px 24px rgba(0,0,0,0.08)]
│   │       │   ├── SwatchLabel "薄片 (24/0.08)" [14px, Medium, #3A3A4A]
│   │       │   └── SwatchDescription "阴影模糊 24px / 不透明度 0.08" [12px, Regular, rgba(58,58,74,0.60)]
│   │       │
│   │       └── ElevationSwatch[level=4, blur=40px, opacity=0.10]
│   │           ├── WhiteBlock [约140×140px, radius:16px, shadow:0 12px 40px rgba(0,0,0,0.10)]
│   │           ├── SwatchLabel "模态 (40/0.10)" [14px, Medium, #3A3A4A]
│   │           └── SwatchDescription "阴影模糊 40px / 不透明度 0.10" [12px, Regular, rgba(58,58,74,0.60)]
│   │
│   └── GlassSection [z:2, Section 3]
│       │
│       ├── SectionHeading
│       │   ├── DotIcon [●, #FFB7C5, 约12px diameter]
│       │   └── Text "玻璃效果（Glassmorphism）" [18–20px, Medium, #3A3A4A]
│       │
│       └── IllustrationBackdrop [约840×200px, radius:20px, overflow:hidden]
│           │
│           ├── IllustrationImage [sakura_sky_bg, 铺满容器]
│           │   └── [内容: 蓝天 + 白云 + 樱花树 + 飘落花瓣]
│           │
│           └── GlassCardRow [Flex Row, gap≈16px, padding≈16px, z:+1 相对于插画]
│               │
│               ├── GlassCard[variant=glass-35]
│               │   ├── GlassLayer [rgba(255,255,255,0.35), backdrop-filter:blur(16px), radius:16px]
│               │   └── [空内容 — 纯样式展示]
│               │
│               ├── GlassCard[variant=glass-55]
│               │   ├── GlassLayer [rgba(255,255,255,0.55), backdrop-filter:blur(16px), radius:16px]
│               │   └── [空内容 — 纯样式展示]
│               │
│               ├── GlassCard[variant=glass-75]
│               │   ├── GlassLayer [rgba(255,255,255,0.75), backdrop-filter:blur(16px), radius:16px]
│               │   └── [空内容 — 纯样式展示]
│               │
│               └── GlassCard[variant=glass-tinted]
│                   ├── GlassLayer [rgba(255,255,255,0.55) + 色调叠加, backdrop-filter:blur(16px), radius:16px]
│                   └── [空内容 — 纯样式展示]
│
└── GlassLabelGroup [z:2, 在 MainContainerCard 内，IllustrationBackdrop 正下方]
    ├── GlassSwatchLabel[variant=glass-35]
    │   ├── SwatchLabel "玻璃 35%" [14px, Medium, #3A3A4A]
    │   ├── SwatchDescription "白色 35%" [12px, Regular, rgba(58,58,74,0.60)]
    │   └── SwatchDescription "背景模糊 16px" [12px, Regular, rgba(58,58,74,0.60)]
    │
    ├── GlassSwatchLabel[variant=glass-55]
    │   ├── SwatchLabel "玻璃 55%" [14px, Medium, #3A3A4A]
    │   ├── SwatchDescription "白色 55%" [12px, Regular, rgba(58,58,74,0.60)]
    │   └── SwatchDescription "背景模糊 16px" [12px, Regular, rgba(58,58,74,0.60)]
    │
    ├── GlassSwatchLabel[variant=glass-75]
    │   ├── SwatchLabel "玻璃 75%" [14px, Medium, #3A3A4A]
    │   ├── SwatchDescription "白色 75%" [12px, Regular, rgba(58,58,74,0.60)]
    │   └── SwatchDescription "背景模糊 16px" [12px, Regular, rgba(58,58,74,0.60)]
    │
    └── GlassSwatchLabel[variant=glass-tinted]
        ├── SwatchLabel "玻璃着色" [14px, Medium, #3A3A4A]
        ├── SwatchDescription "白色 55% + 色调" [12px, Regular, rgba(58,58,74,0.60)]
        └── SwatchDescription "背景模糊 16px" [12px, Regular, rgba(58,58,74,0.60)]

BrandFooter [z:2, 位于 MainContainerCard 外/下方，画布底部居中]
├── HeartIcon [♥, #FFB7C5, 约14px]
└── Text "yuoyuo · 温柔治愈的陪伴体验" [13–14px, Regular, #3A3A4A]
```

---

## 层级深度统计

| 层级深度 | 节点数 | 说明 |
|---------|--------|------|
| 深度 1 | 3 | 背景层、主容器、底部署名 |
| 深度 2 | 5 | 标题、3个Section、光晕 |
| 深度 3 | 约 12 | SectionHeading、SwatchRow等 |
| 深度 4 | 约 28 | 各 Swatch、GlassCard、标签 |
| 深度 5 | 约 40 | 具体文字、图层、描述 |

---

## 可复用组件标记

| 组件 | 可复用 | 用于 |
|------|--------|------|
| `SectionHeading` | ✅ | 所有 Token 参考 Section |
| `DotIcon` | ✅ | 品牌装饰点 |
| `RadiusSwatch` | ✅ | 圆角展示 |
| `ElevationSwatch` | ✅ | 阴影展示 |
| `GlassCard` | ✅ ⭐核心 | App 中所有玻璃覆层 |
| `IllustrationBackdrop` | ✅ | 带插画背景的容器 |
| `SwatchLabel` | ✅ | Token 标注 |
| `SwatchDescription` | ✅ | Token 副描述 |
| `BrandFooter` | ✅ | 所有 Phase 1 参考图 |
