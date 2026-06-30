# 07 Component Tree — 首次引导 FirstVisitGuide

## 总览：三屏拼版结构

```
MockupCanvas (1536 × 1024)
├── CanvasBackground                          # 画布底色 #FEF0F0
│
├── PhoneFrame_Step1 (拼版帧，非App UI)
│   └── OnboardingPage_Step1
│       ├── PageBackground_Step1
│       │   ├── LinearGradient_bg             # 线性渐变 #E8D8F5→#F9D0E0→#FDE8C8
│       │   └── BokehLayer                    # 散射光斑装饰
│       │       ├── BokehCircle_1             # 粉色光斑
│       │       ├── BokehCircle_2             # 紫色光斑
│       │       └── BokehCircle_N             # ...更多光斑
│       │
│       ├── StatusBar                         # 系统状态栏 h=47px
│       │   ├── TimeLabel ("9:41")
│       │   └── SystemIcons
│       │       ├── CellularIcon              # 蜂窝信号
│       │       ├── WiFiIcon                  # WiFi信号
│       │       └── BatteryIcon               # 电池状态
│       │
│       ├── IllustrationArea                  # 插画区 h≈440px
│       │   ├── IllustrationBackground_Step1  # 云海背景图
│       │   │   ├── DreamSkyImage             # 粉紫天空 + 云朵
│       │   │   └── GoldenLightRay            # 中央金光
│       │   ├── CrystalHeart_Large            # 水晶心主插画
│       │   │   ├── HeartBody                 # 心形水晶体
│       │   │   └── HeartGlow                 # 粉色发光光晕
│       │   └── IllustrationFadeMask          # 底部渐变淡出遮罩
│       │
│       └── ContentArea                       # 内容区 h≈350px
│           ├── TitleText_Step1               # "我是yuoyuo，独属于你的虚拟宇宙。"
│           ├── SubtitleText_Step1            # "我会记得你说过的话，理解你的情绪。"
│           ├── PaginationDots                # 分页点组 (● ○ ○)
│           │   ├── Dot_1_Active              # 激活点 #FFB7C5 d=8px
│           │   ├── Dot_2_Inactive            # 非激活 透明粉 d=6px
│           │   └── Dot_3_Inactive            # 非激活 透明粉 d=6px
│           └── GhostButton_Next              # "下一步"
│               └── ButtonLabel               # 文字"下一步"
│
├── PhoneFrame_Step2 (拼版帧，非App UI)
│   └── OnboardingPage_Step2
│       ├── PageBackground_Step2
│       │   ├── LinearGradient_bg             # 同Step1（微调色调）
│       │   └── BokehLayer
│       │       ├── BokehCircle_1
│       │       └── BokehCircle_N
│       │
│       ├── StatusBar                         # 同Step1
│       │   ├── TimeLabel ("9:41")
│       │   └── SystemIcons
│       │       ├── CellularIcon
│       │       ├── WiFiIcon
│       │       └── BatteryIcon
│       │
│       ├── IllustrationArea                  # 插画区 h≈440px
│       │   ├── IllustrationBackground_Step2  # 朦胧粉紫渐变背景
│       │   ├── GlassBellPendant              # 玻璃罩吊坠插画
│       │   │   ├── NecklaceChain             # 顶部链条（粉色金属链）
│       │   │   ├── GlassDome                 # 玻璃钟罩（透明折射）
│       │   │   └── MiniaturaScene            # 罩内微场景
│       │   │       ├── PinkSofa              # 粉色沙发
│       │   │       ├── TableLamp             # 台灯（暖光）
│       │   │       └── SmallPlant            # 小植物
│       │   └── IllustrationFadeMask          # 底部渐变淡出遮罩
│       │
│       └── ContentArea
│           ├── TitleText_Step2               # "你的对话只属于你。"
│           ├── SubtitleText_Step2            # "数据加密存储，注销即记忆全部消散。"
│           ├── PaginationDots                # 分页点组 (○ ● ○)
│           │   ├── Dot_1_Inactive
│           │   ├── Dot_2_Active              # 激活点
│           │   └── Dot_3_Inactive
│           └── GhostButton_Next              # "下一步"
│               └── ButtonLabel
│
└── PhoneFrame_Step3 (拼版帧，非App UI)
    └── OnboardingPage_Step3
        ├── PageBackground_Step3
        │   ├── LinearGradient_bg             # 同Step1（微调色调）
        │   └── BokehLayer
        │       ├── BokehCircle_1
        │       └── BokehCircle_N
        │
        ├── StatusBar                         # 同Step1
        │   ├── TimeLabel ("9:41")
        │   └── SystemIcons
        │       ├── CellularIcon
        │       ├── WiFiIcon
        │       └── BatteryIcon
        │
        ├── IllustrationArea                  # 插画区 h≈440px
        │   ├── IllustrationBackground_Step3  # 粉紫背景，含花瓣
        │   │   └── PetalDecors               # 散落花瓣装饰
        │   │       ├── Petal_1
        │   │       ├── Petal_2
        │   │       └── Petal_N
        │   ├── GiftBox                       # 礼盒主插画（偏左）
        │   │   ├── BoxBody                   # 粉色礼盒盒体
        │   │   ├── Ribbon                    # 粉色丝带
        │   │   └── Bow                       # 白色蝴蝶结
        │   ├── CrystalHeart_Small            # 水晶心小版（右下角叠压）
        │   └── IllustrationFadeMask          # 底部渐变淡出遮罩
        │
        └── ContentArea
            ├── TitleText_Step3               # "在爱赞助发电即可解锁会员。"
            ├── SubtitleText_Step3            # "支持微信/支付宝；赞助后领取兑换码..."（2行）
            ├── PaginationDots                # 分页点组 (○ ○ ●)
            │   ├── Dot_1_Inactive
            │   ├── Dot_2_Inactive
            │   └── Dot_3_Active              # 激活点
            ├── PrimaryButton_Start           # "开始体验"（实心粉色渐变）
            │   └── ButtonLabel               # 白色文字"开始体验"
            └── TextLinkButton_Redeem         # "我有兑换码 →"（文字链接）
                ├── LinkText                  # "我有兑换码"
                └── ArrowIcon                 # "→"

```

---

## 拼版底部标签（设计文件专用，非App UI）

```
CanvasCanvas (1536 × 1024) 底部区域
├── MockupLabel_Step1   # "步骤 1 — 认识 yuoyuo"（居中于PhoneFrame_Step1下方）
├── MockupLabel_Step2   # "步骤 2 — 你的隐私安全"（居中于PhoneFrame_Step2下方）
└── MockupLabel_Step3   # "步骤 3 — 解锁完整体验"（居中于PhoneFrame_Step3下方）
```

---

## 层级注释

| 组件 | z-index | 说明 |
|------|---------|------|
| PageBackground | 0 | 最底层，绝对定位 |
| IllustrationArea | 1 | 插画层 |
| IllustrationFadeMask | 2 | 渐变遮罩，叠压插画底部 |
| ContentArea | 3 | 内容层，位于插画之上 |
| StatusBar | 10 | 最顶层，系统级 |

---

## 组件复用说明

以下组件在三屏中结构完全相同，仅内容不同，应使用同一组件通过 props 控制：

| 组件 | 复用方式 |
|------|----------|
| `StatusBar` | 完全相同，不区分屏幕 |
| `PageBackground` | 通过 `variant` prop 微调渐变色（step1/step2/step3） |
| `IllustrationFadeMask` | 完全相同 |
| `PaginationDots` | `activeIndex` prop 控制激活状态 |
| `GhostButton` | `label` prop = "下一步"，`onPress` 绑定不同handler |
| `TitleText` | `content` prop 传入各屏文案 |
| `SubtitleText` | `content` prop 传入各屏文案 |
