# 07 组件树（Component Tree）— 颜色系统色板

> 完整 ASCII 树形结构，覆盖画布所有可见元素。

---

## 完整组件树

```
PaletteCanvas [1536×1024px, bg:#FFF8F3]
├── PageHeader [水平居中, padding-top:~40px]
│   └── PageTitle "yuoyuo · 颜色系统"
│       ├── BrandWordmark "yuoyuo" [SF Pro Rounded, ~38px, #3A3A4A]
│       ├── Separator "·" [~38px, #3A3A4A]
│       └── TitleText "颜色系统" [PingFang SC, ~38px, #3A3A4A]
│
├── ColorGridSection [Flex Row, 5列, padding:~60px 横向]
│   │
│   ├── ColorColumn__Primary [主色（樱花粉）]
│   │   ├── ColorColumnHeader
│   │   │   ├── ColumnName "主色（樱花粉）" [PingFang SC, ~16px, #3A3A4A]
│   │   │   └── ColumnHex "#FFB7C5" [Mono, ~14px, #7A7873]
│   │   └── ColorScaleList [Flex Column, gap:~10px]
│   │       ├── ColorScaleRow [step=50]
│   │       │   ├── StepLabel "50" [~15px, #7A7873]
│   │       │   ├── ColorSwatch [bg:#FFF1F3, radius:~14px, ~128×36px]
│   │       │   └── HexLabel "#FFF1F3" [Mono, ~13px, #3A3A4A]
│   │       ├── ColorScaleRow [step=100]
│   │       │   ├── StepLabel "100"
│   │       │   ├── ColorSwatch [bg:#FFE0E6]
│   │       │   └── HexLabel "#FFE0E6"
│   │       ├── ColorScaleRow [step=200]
│   │       │   ├── StepLabel "200"
│   │       │   ├── ColorSwatch [bg:#FFC7D2]
│   │       │   └── HexLabel "#FFC7D2"
│   │       ├── ColorScaleRow [step=300]
│   │       │   ├── StepLabel "300"
│   │       │   ├── ColorSwatch [bg:#FFADC0]
│   │       │   └── HexLabel "#FFADC0"
│   │       ├── ColorScaleRow [step=400, isBase=true] ★品牌主色
│   │       │   ├── BaseBadge [bg:#FFB7C5, text:"400", white, pill]
│   │       │   ├── ColorSwatch [bg:#FFB7C5]
│   │       │   └── HexLabel "#FFB7C5"
│   │       ├── ColorScaleRow [step=500]
│   │       │   ├── StepLabel "500"
│   │       │   ├── ColorSwatch [bg:#FF95AA]
│   │       │   └── HexLabel "#FF95AA"
│   │       ├── ColorScaleRow [step=600]
│   │       │   ├── StepLabel "600"
│   │       │   ├── ColorSwatch [bg:#FF7691]
│   │       │   └── HexLabel "#FF7691"
│   │       ├── ColorScaleRow [step=700]
│   │       │   ├── StepLabel "700"
│   │       │   ├── ColorSwatch [bg:#FF5B7D]
│   │       │   └── HexLabel "#FF5B7D"
│   │       ├── ColorScaleRow [step=800]
│   │       │   ├── StepLabel "800"
│   │       │   ├── ColorSwatch [bg:#FF4369]
│   │       │   └── HexLabel "#FF4369"
│   │       └── ColorScaleRow [step=900]
│   │           ├── StepLabel "900"
│   │           ├── ColorSwatch [bg:#E7335A]
│   │           └── HexLabel "#E7335A"
│   │
│   ├── ColorColumn__Secondary [辅色（梦幻天蓝）]
│   │   ├── ColorColumnHeader
│   │   │   ├── ColumnName "辅色（梦幻天蓝）" [PingFang SC]
│   │   │   └── ColumnHex "#A7C7E7"
│   │   └── ColorScaleList
│   │       ├── ColorScaleRow [step=50,  hex=#EEF6FF]
│   │       ├── ColorScaleRow [step=100, hex=#DDEBFA]
│   │       ├── ColorScaleRow [step=200, hex=#C7DEF5]
│   │       ├── ColorScaleRow [step=300, hex=#B1D1F0]
│   │       ├── ColorScaleRow [step=400, isBase=true, hex=#A7C7E7] ★
│   │       │   └── BaseBadge [bg:#A7C7E7, text:"400"]
│   │       ├── ColorScaleRow [step=500, hex=#8EB9E0]
│   │       ├── ColorScaleRow [step=600, hex=#6FA9D8]
│   │       ├── ColorScaleRow [step=700, hex=#5394CF]
│   │       ├── ColorScaleRow [step=800, hex=#3E80C6]
│   │       └── ColorScaleRow [step=900, hex=#2D6AAC]
│   │
│   ├── ColorColumn__Accent [点缀色（薰衣草草雾）]
│   │   ├── ColorColumnHeader
│   │   │   ├── ColumnName "点缀色（薰衣草草雾）" [PingFang SC]
│   │   │   └── ColumnHex "#C8B6FF"
│   │   └── ColorScaleList
│   │       ├── ColorScaleRow [step=50,  hex=#F3F0FF]
│   │       ├── ColorScaleRow [step=100, hex=#E8E2FF]
│   │       ├── ColorScaleRow [step=200, hex=#D9D0FF]
│   │       ├── ColorScaleRow [step=300, hex=#CBBEFF]
│   │       ├── ColorScaleRow [step=400, isBase=true, hex=#C8B6FF] ★
│   │       │   └── BaseBadge [bg:#C8B6FF, text:"400"]
│   │       ├── ColorScaleRow [step=500, hex=#B5A2FF]
│   │       ├── ColorScaleRow [step=600, hex=#9F8BFF]
│   │       ├── ColorScaleRow [step=700, hex=#8772F7]
│   │       ├── ColorScaleRow [step=800, hex=#6F5CE6]
│   │       └── ColorScaleRow [step=900, hex=#5747C2]
│   │
│   ├── ColorColumn__Surface [表面/中性（暖奶油→炭灰）]
│   │   ├── ColorColumnHeader
│   │   │   └── ColumnName "表面/中性（暖奶油→炭灰）" [PingFang SC]
│   │   └── ColorScaleList
│   │       ├── ColorScaleRow [step=50,  hex=#FFF8F3]
│   │       ├── ColorScaleRow [step=100, hex=#FFF2E8]
│   │       ├── ColorScaleRow [step=200, hex=#FDE8DA]
│   │       ├── ColorScaleRow [step=300, hex=#FADEC8]
│   │       ├── ColorScaleRow [step=400, hex=#F6D5B4]
│   │       ├── ColorScaleRow [step=500, hex=#EED0A0]
│   │       ├── ColorScaleRow [step=600, hex=#D8CAA8]
│   │       ├── ColorScaleRow [step=700, hex=#B6B1A2]
│   │       ├── ColorScaleRow [step=800, hex=#7A7873]
│   │       └── ColorScaleRow [step=900, hex=#3A3A4A]
│   │
│   └── ColorColumn__Semantic [语义色（状态提示）]
│       ├── ColumnLabel "语义色（状态提示）" [PingFang SC]
│       └── SemanticCardList [Flex Column, gap:~12px]
│           ├── SemanticColorCard [type=success]
│           │   ├── CardBackground [bg:#B6E2C7, radius:~16px]
│           │   ├── SemanticIcon [circle, 成功绿, ✓图标, ~30px]
│           │   └── CardTextGroup [Flex Column]
│           │       ├── SemanticName "成功 / Success" [PingFang SC, ~15px, #3A3A4A]
│           │       └── SemanticHex "#B6E2C7" [Mono, ~13px, #7A7873]
│           ├── SemanticColorCard [type=warning]
│           │   ├── CardBackground [bg:#FFD3A5, radius:~16px]
│           │   ├── SemanticIcon [circle, 警告橙, !图标, ~30px]
│           │   └── CardTextGroup
│           │       ├── SemanticName "警告 / Warning"
│           │       └── SemanticHex "#FFD3A5"
│           ├── SemanticColorCard [type=error]
│           │   ├── CardBackground [bg:#F4A6A6, radius:~16px]
│           │   ├── SemanticIcon [circle, 错误红, ✕图标, ~30px]
│           │   └── CardTextGroup
│           │       ├── SemanticName "错误 / Error"
│           │       └── SemanticHex "#F4A6A6"
│           └── SemanticColorCard [type=info]
│               ├── CardBackground [bg:#B6C7F4, radius:~16px]
│               ├── SemanticIcon [circle, 信息蓝, i图标, ~30px]
│               └── CardTextGroup
│                   ├── SemanticName "信息 / Info"
│                   └── SemanticHex "#B6C7F4"
│
├── GlassOverlaySection [Flex Column, padding:~60px 横向]
│   ├── GlassSectionTitle
│   │   └── TitleText "玻璃叠加（Glass Overlay）— 用于磨砂玻璃表面"
│   │       [PingFang SC, ~20px, #3A3A4A]
│   └── GlassCardRow [Flex Row, 4列等宽, gap:~28px]
│       ├── GlassOverlayCard [opacity=35%]
│       │   ├── CardBackground [渐变底层, radius:~22px]
│       │   ├── GlassLayer [rgba(255,255,255,.35), backdrop-filter:blur]
│       │   └── CardCaption [Flex Column, 居中, 卡片下方]
│       │       ├── OpacityLabel "35% 白色叠加" [PingFang SC, ~15px, #7A7873]
│       │       └── RgbaValue "rgba(255,255,255,.35)" [Mono, ~13px, #B6B1A2]
│       ├── GlassOverlayCard [opacity=55%]
│       │   ├── CardBackground [渐变底层, radius:~22px]
│       │   ├── GlassLayer [rgba(255,255,255,.55), backdrop-filter:blur]
│       │   └── CardCaption
│       │       ├── OpacityLabel "55% 白色叠加"
│       │       └── RgbaValue "rgba(255,255,255,.55)"
│       ├── GlassOverlayCard [opacity=75%]
│       │   ├── CardBackground [渐变底层, radius:~22px]
│       │   ├── GlassLayer [rgba(255,255,255,.75), backdrop-filter:blur]
│       │   └── CardCaption
│       │       ├── OpacityLabel "75% 白色叠加"
│       │       └── RgbaValue "rgba(255,255,255,.75)"
│       └── GlassOverlayCard [opacity=90%]
│           ├── CardBackground [渐变底层, radius:~22px]
│           ├── GlassLayer [rgba(255,255,255,.90), backdrop-filter:blur]
│           └── CardCaption
│               ├── OpacityLabel "90% 白色叠加"
│               └── RgbaValue "rgba(255,255,255,.90)"
│
└── PageFooter [水平居中, padding-bottom:~32px]
    └── FooterBrand [Flex Row, gap:~8px, align-items:center]
        ├── HeartIcon [♥, fill:#FFB7C5, ~17px]
        └── BrandWordmark "yuoyuo" [SF Pro Rounded, ~17px, #3A3A4A]
```

---

## 组件树说明

### 层级关系

```
PaletteCanvas
  ↳ PageHeader          (层级 1)
  ↳ ColorGridSection    (层级 1)
      ↳ ColorColumn × 5 (层级 2)
          ↳ ColorColumnHeader (层级 3)
          ↳ ColorScaleList    (层级 3)
              ↳ ColorScaleRow × 9 (层级 4)
                  ↳ StepLabel / BaseBadge / ColorSwatch / HexLabel (层级 5)
          ↳ SemanticCardList  (层级 3，仅语义色列）
              ↳ SemanticColorCard × 4 (层级 4)
                  ↳ CardBackground / SemanticIcon / CardTextGroup (层级 5)
  ↳ GlassOverlaySection (层级 1)
      ↳ GlassSectionTitle    (层级 2)
      ↳ GlassCardRow         (层级 2)
          ↳ GlassOverlayCard × 4 (层级 3)
              ↳ CardBackground / GlassLayer / CardCaption (层级 4)
  ↳ PageFooter          (层级 1)
      ↳ FooterBrand           (层级 2)
          ↳ HeartIcon / BrandWordmark (层级 3)
```

### 可见元素总数（估算）

| 元素类型 | 数量 |
|---------|------|
| 色阶行（ColorScaleRow） | 约 45 行（4列×9阶 + 表面色列×9） |
| 色块（ColorSwatch） | 约 45 个 |
| 品牌徽标（BaseBadge） | 3 个（主/辅/点缀各1） |
| 语义色卡片 | 4 个 |
| 玻璃叠加卡片 | 4 个 |
| 文字节点（标题+标签+HEX） | 约 100+ 个 |
| 图标 | 5 个（4语义图标+1爱心） |
