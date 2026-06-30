# 07 组件树 — Splash Screen（启动屏）

> 完整 ASCII 树形结构，覆盖所有可见元素及其层级关系。坐标和尺寸标注为画布坐标（1024×1536px），标有（估算值）。

---

## 完整组件树

```
SplashScreen [position: fixed, 1024×1536px, z:0]
│
├── Layer: BackgroundStack [position: absolute, inset: 0, z: 0]
│   │
│   ├── SkyGradientBackground [position: absolute, inset: 0]
│   │   ├── type: CSS linear-gradient 180°
│   │   ├── stop[0]: #FCEACB @ 0%（估算值）
│   │   ├── stop[1]: #F8D0C0 @ 15%（估算值）
│   │   ├── stop[2]: #F5C0CF @ 40%（估算值）
│   │   ├── stop[3]: #EDB8D8 @ 70%（估算值）
│   │   └── stop[4]: #D9B8E8 @ 100%（估算值）
│   │
│   └── TopRightGlow [position: absolute, top:0, right:0, z: 2]
│       ├── type: CSS radial-gradient
│       ├── center: right top（估算值）
│       ├── radius: ≈300px（估算值）
│       ├── color: rgba(255,253,230,0.85)→transparent（估算值）
│       └── blend-mode: normal
│
├── Layer: CloudDecorations [position: absolute, inset: 0, z: 1]
│   │
│   ├── Cloud_01 [position: absolute, top:~150px, left:0, z:1]
│   │   ├── size: ≈250×120px（估算值）
│   │   ├── opacity: 0.7（估算值）
│   │   ├── blur: 10px（估算值）
│   │   └── color: rgba(255,240,245,0.7)（估算值）
│   │
│   ├── Cloud_02 [position: absolute, top:~220px, left:~50px, z:1]
│   │   ├── size: ≈180×80px（估算值）
│   │   ├── opacity: 0.5（估算值）
│   │   └── blur: 8px（估算值）
│   │
│   ├── Cloud_03 [position: absolute, top:~80px, left:~200px, z:1]
│   │   ├── size: ≈150×70px（估算值）
│   │   ├── opacity: 0.6（估算值）
│   │   └── blur: 12px（估算值）
│   │
│   ├── Cloud_04 [position: absolute, top:~650px, right:~0px, z:1]
│   │   ├── size: ≈130×60px（估算值）
│   │   ├── opacity: 0.45（估算值）
│   │   └── blur: 8px（估算值）
│   │
│   ├── Cloud_05 [position: absolute, top:~950px, left:0, z:1]
│   │   ├── size: ≈220×90px（估算值）
│   │   ├── opacity: 0.5（估算值）
│   │   └── blur: 14px（估算值）
│   │
│   ├── Cloud_06 [position: absolute, top:~1200px, left:0, z:1]
│   │   ├── size: ≈300×100px（估算值）
│   │   ├── opacity: 0.55（估算值）
│   │   └── blur: 16px（估算值）
│   │
│   ├── Cloud_07 [position: absolute, top:~1150px, right:~0px, z:1]
│   │   ├── size: ≈280×120px（估算值）
│   │   ├── opacity: 0.65（估算值）
│   │   └── blur: 12px（估算值）
│   │
│   └── Cloud_08 [position: absolute, top:~1350px, left:~100px, z:1]
│       ├── size: ≈500×150px（估算值）
│       ├── opacity: 0.6（估算值）
│       └── blur: 20px（估算值）
│
├── Layer: ContentStack [
│   │   position: absolute,
│   │   top: 50%, left: 50%,
│   │   transform: translate(-50%, -50%),（视觉重心略偏上）
│   │   display: flex,
│   │   flex-direction: column,
│   │   align-items: center,
│   │   z: 10
│   │ ]
│   │
│   ├── GemIcon [position: relative, z: 10]
│   │   ├── size: ≈420×400px（估算值）
│   │   ├── margin-bottom: ≈58px（估算值）
│   │   │
│   │   ├── Layer: GemBase [渐变填充层]
│   │   │   ├── shape: 心形 + 气泡尾部
│   │   │   ├── gradient: 135°, #FFB7C5 → #C8B6FF → #A7C7E7（估算值）
│   │   │   └── border: 2px solid rgba(255,255,255,0.6)（估算值）
│   │   │
│   │   ├── Layer: GemHighlight [高光层]
│   │   │   ├── shape: 椭圆形，位于左上角
│   │   │   ├── size: ≈160×120px（估算值）
│   │   │   ├── color: rgba(255,255,255,0.9)→rgba(255,255,255,0)
│   │   │   └── gradient: 120°
│   │   │
│   │   ├── Layer: GemInnerGlow [内部光晕层]
│   │   │   ├── type: radial gradient
│   │   │   ├── color: rgba(255,255,255,0.3)（估算值）
│   │   │   └── blur: 20px（估算值）
│   │   │
│   │   ├── Layer: SparkleParticles [星光粒子层]
│   │   │   ├── Sparkle_01 [四芒星, ≈25px, 白色]（估算值）
│   │   │   ├── Sparkle_02 [四芒星, ≈18px, 白色]（估算值）
│   │   │   ├── Sparkle_03 [四芒星, ≈15px, 白色]（估算值）
│   │   │   └── （约2～3个更小的粒子，估算值）
│   │   │
│   │   └── Layer: GemDropShadow [外部投影层]
│   │       ├── color: rgba(200,160,210,0.35)（估算值）
│   │       ├── blur: 60px（估算值）
│   │       ├── offset: (0, 20px)（估算值）
│   │       └── spread: 0
│   │
│   ├── AppWordmark [position: relative, z: 10]
│   │   ├── content: "yuoyuo"
│   │   ├── font: SF Pro Rounded Bold
│   │   ├── size: ≈96px（画布，估算值）
│   │   ├── color: #3A3A4A
│   │   ├── letter-spacing: -0.02em（估算值）
│   │   ├── text-align: center
│   │   └── margin-bottom: ≈30px（估算值）
│   │
│   └── AppTagline [position: relative, z: 10]
│       ├── content: "陪你聊聊吧"
│       ├── font: PingFang SC Regular
│       ├── size: ≈48px（画布，估算值）
│       ├── color: #5A5A6A（估算值）
│       ├── letter-spacing: 0.12em（估算值）
│       └── text-align: center
│
└── Layer: BottomIndicator [
        position: absolute,
        bottom: ≈86px（估算值）,
        left: 50%,
        transform: translateX(-50%),
        display: flex,
        flex-direction: row,
        align-items: center,
        gap: ≈12px（估算值）,
        z: 20
      ]
    │
    ├── Dot_Left [circle]
    │   ├── diameter: ≈12px（估算值）
    │   ├── color: #F0A0B8（估算值）
    │   ├── opacity: 0.6（估算值）
    │   └── border-radius: 50%
    │
    ├── Dot_Center [circle, active state]
    │   ├── diameter: ≈18px（估算值）
    │   ├── color: #E87A9A（估算值）
    │   ├── opacity: 1.0
    │   └── border-radius: 50%
    │
    └── Dot_Right [circle]
        ├── diameter: ≈12px（估算值）
        ├── color: #F0A0B8（估算值）
        ├── opacity: 0.6（估算值）
        └── border-radius: 50%
```

---

## 层级关系图（Z轴视图）

```
↑ 高（前景）
│
z:20  BottomIndicator（三点指示器）
z:10  ContentStack（宝石图标 + 字标 + tagline）
z:2   TopRightGlow（顶部光晕）
z:1   CloudDecorations（云朵群）
z:0   SkyGradientBackground（天空渐变背景）
│
↓ 低（背景）
```

---

## 渲染顺序（Painter's Algorithm）

```
1. SkyGradientBackground    ← 最先绘制
2. Cloud_01 ～ Cloud_08     ← 按编号顺序（从远到近）
3. TopRightGlow             ← 叠加在背景上
4. GemIcon                  ← 核心视觉元素
5. AppWordmark              ← 文字层
6. AppTagline               ← 文字层
7. BreathingDots            ← 最后绘制（确保在最顶层）
```

---

## 节点数量统计

| 组件类别 | 数量 |
|----------|------|
| 背景层节点 | 2（渐变 + 光晕）|
| 云朵节点 | 8（估算值，实际可能更多）|
| 宝石图标内部层 | 5（基色 + 高光 + 内光 + 粒子 + 投影）|
| 文字节点 | 2（字标 + tagline）|
| 指示器节点 | 3（左中右三点）|
| **总计** | **约 20 个节点** |
