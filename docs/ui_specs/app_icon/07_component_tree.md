# 07 组件树 — App Icon（多色版 + 单色版）

## 完整组件树（ASCII 树形结构）

```
AppIcon_展示画布 [1024×1024 px]
│
├── CanvasBackground [1024×1024 px]
│   └── 填充：#FAE8D8（暖米杏色，估算值）
│
├── LeftPanel_全色渐变版 [512×1024 px, x:0–512]
│   │
│   ├── AmbientGlow_全色版 [≈600×250 px, Z-1]
│   │   ├── 颜色：rgba(200,182,255,0.45) + rgba(255,183,197,0.35)
│   │   ├── 形态：扁椭圆径向渐变
│   │   ├── Blur：80 px（估算值）
│   │   └── 位置：图标底部边缘向下扩散
│   │
│   └── IconGroup_全色版 [≈380×420 px, 中心约 x:240,y:480]
│       │
│       ├── GradientFill [Z-2]
│       │   ├── 类型：线性渐变 135°
│       │   ├── 起点：#FFB7C5（粉红）
│       │   ├── 中点：#C8B6FF（薰衣草，≈45%）
│       │   ├── 终点：#A7C7E7（天蓝）
│       │   └── Clip Mask：IconShapePath
│       │
│       ├── InnerCloudTexture [≈200×100 px, Z-3]
│       │   ├── 位置：图标内部左下象限
│       │   ├── 多层白色椭圆叠加
│       │   ├── Blur：12 px（估算值）
│       │   └── Opacity：60%（估算值）
│       │
│       ├── SparkleDecoration_1 [≈10×10 px, Z-4]
│       │   ├── 形态：4 角星形或十字光点
│       │   ├── 颜色：rgba(255,255,255,0.85)
│       │   └── 位置：图标右上区域（估算值）
│       │
│       ├── SparkleDecoration_2 [≈6×6 px, Z-4]
│       │   ├── 颜色：rgba(255,255,255,0.85)
│       │   └── 位置：图标中部右侧（估算值）
│       │
│       ├── SparkleDecoration_3 [≈4×4 px, Z-4]
│       │   ├── 颜色：rgba(255,255,255,0.85)
│       │   └── 位置：图标中部偏上（估算值）
│       │
│       ├── GlassEdgeStroke [Z-5]
│       │   ├── 描边宽度：3–5 px（估算值）
│       │   ├── 顶部颜色：rgba(255,255,255,0.70)
│       │   ├── 底部颜色：rgba(200,185,200,0.40)
│       │   ├── 类型：内描边（Inside Stroke）
│       │   └── 路径：跟随 IconShapePath
│       │
│       └── SpecularHighlight [≈160×70 px, Z-6]
│           ├── 形态：倾斜椭圆（≈30°）
│           ├── 颜色：中心 rgba(255,255,255,0.80) → 边缘透明
│           ├── 类型：径向渐变
│           └── 位置：图标顶部左侧（估算值）
│
└── RightPanel_单色版 [512×1024 px, x:512–1024]
    │
    ├── DropShadow_单色版 [Z-1]
    │   ├── 颜色：rgba(180,160,160,0.25)
    │   ├── Offset：x:0, y:+20 px（估算值）
    │   └── Blur：30 px（估算值）
    │
    └── IconGroup_单色版 [≈370×410 px, 中心约 x:770,y:470]
        │
        ├── MonoFill [Z-2]
        │   ├── 类型：线性渐变 135°
        │   ├── 起点：#E8E0E8（浅米紫，估算值）
        │   ├── 终点：#C0B8C8（暖灰紫，估算值）
        │   └── Clip Mask：IconShapePath（同一路径）
        │
        ├── InnerCloudTexture_mono [≈180×90 px, Z-3]
        │   ├── 位置：图标内部左下象限（同全色版）
        │   ├── 多层浅灰椭圆叠加
        │   ├── Blur：12 px（估算值）
        │   └── Opacity：45%（估算值）
        │
        ├── SparkleDecoration_mono_1 [≈10×10 px, Z-4]
        │   ├── 颜色：rgba(255,255,255,0.80)
        │   └── 位置：图标右上区域（估算值）
        │
        ├── SparkleDecoration_mono_2 [≈6×6 px, Z-4]
        │   ├── 颜色：rgba(255,255,255,0.80)
        │   └── 位置：图标中部右侧（估算值）
        │
        ├── SparkleDecoration_mono_3 [≈4×4 px, Z-4]
        │   ├── 颜色：rgba(255,255,255,0.80)
        │   └── 位置：图标中部偏上（估算值）
        │
        ├── GlassEdgeStroke_mono [Z-5]
        │   ├── 描边宽度：3–5 px（估算值）
        │   ├── 顶部颜色：rgba(255,255,255,0.65)
        │   ├── 底部颜色：rgba(200,185,200,0.50)
        │   └── 路径：跟随 IconShapePath
        │
        └── SpecularHighlight_mono [≈160×70 px, Z-6]
            ├── 形态：倾斜椭圆（≈30°）
            ├── 颜色：中心 rgba(255,255,255,0.70) → 边缘透明（饱和度低于全色版）
            ├── 类型：径向渐变
            └── 位置：图标顶部左侧（估算值）
```

---

## IconShapePath 内部结构（两版本共享）

```
IconShapePath [复合路径，单一闭合贝塞尔曲线]
│
├── 顶部区域
│   ├── 左峰（Left Lobe）
│   │   └── 外侧弧线 → 内侧凹入曲线
│   ├── 顶部中央凹谷（Top Valley）
│   │   └── 向内凹入，呈平滑 V 形
│   └── 右峰（Right Lobe）
│       └── 略高于左峰，外侧弧线
│
├── 主体区域（Body）
│   ├── 左侧圆弧（向左外凸）
│   ├── 右侧圆弧（向右外凸）
│   └── 最宽截面（约距顶部 50% 处）
│
├── 收拢区域（Taper）
│   ├── 从主体最宽处向右下角收拢
│   └── 右下尖点（Bottom Right Tip）
│
└── 气泡尾巴（Chat Bubble Tail）
    ├── 从左下方向外延伸
    ├── 弯曲轨迹（向左下弯曲再向右弯回）
    └── 末端圆润（Radius ≈ 12 px，估算值）
```

---

## 图层层级总览（Z-index）

```
Z-6  SpecularHighlight（顶部高光椭圆）
Z-5  GlassEdgeStroke（边缘玻璃描边）
Z-4  SparkleDecoration × 3（星光点缀）
Z-3  InnerCloudTexture（内部云朵纹理）
Z-2  GradientFill / MonoFill（主体填充）
Z-1  AmbientGlow / DropShadow（外发光/投影）
Z-0  CanvasBackground（展示画布底色）
```

---

## 组件数量统计

| 类型 | 数量 |
|------|------|
| 容器/分区 | 3（画布 + 左面板 + 右面板） |
| 共享路径 | 1（IconShapePath） |
| 填充层 | 2（GradientFill + MonoFill） |
| 纹理/装饰 | 8（云朵×2 + 星光×6） |
| 效果层 | 6（高光×2 + 描边×2 + 发光×1 + 投影×1） |
| **合计** | **22 个可见图层** |
