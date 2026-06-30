# 07 组件树（Component Tree）

## 说明

以下为分镜图所涉及的完整组件树（ASCII 树形结构）。由于本资产为设计文档（4帧分镜），组件树分为两层：
1. **设计文档层**：画布级结构（非运行时）
2. **运行时组件层**：每帧内部实际的 UI 组件

---

## 设计文档层（画布级）

```
StoryboardCanvas（画布 1536×1024）
├── CanvasTitle                          "yuoyuo · Motion"
│
├── StoryboardFrame[1]                   帧①：气泡绽放
│   ├── DeviceFrame                      iPhone 14 框
│   ├── StoryboardArrow[1→2]             → 箭头 + "300ms"
│   └── MotionAnnotation[1]              ① 气泡绽放（300ms 缓出）
│
├── StoryboardFrame[2]                   帧②：情绪球脉冲
│   ├── DeviceFrame
│   ├── StoryboardArrow[2→3]             → 箭头 + "1200ms"
│   └── MotionAnnotation[2]              ② 情绪球脉冲（1200ms 无限，缓动）
│
├── StoryboardFrame[3]                   帧③：语音波
│   ├── DeviceFrame
│   ├── StoryboardArrow[3→4]             → 箭头 + "400ms"
│   └── MotionAnnotation[3]              ③ 语音波（实时）
│
└── StoryboardFrame[4]                   帧④：页面过渡
    ├── DeviceFrame（双层叠加）
    └── MotionAnnotation[4]              ④ 页面过渡（Apple Sheet 风格，400ms）
```

---

## 运行时组件层 — 帧①（气泡绽放，聊天页标准态）

```
ChatScreen
├── StatusBar                            状态栏（9:41 / 信号/WiFi/电量）
│
├── ChatNavBar                           导航栏
│   ├── NavBackButton                    < 返回按钮
│   ├── NavCenter                        中央区域
│   │   ├── EmotionOrb（size=sm）        情绪球（正常态 ~36px）
│   │   ├── NavTitle                     "悠悠"
│   │   └── NavSubtitle                  "在线"
│   └── NavMenuButton                    ··· 菜单
│
├── MessageList（ScrollView）            消息列表（可滚动）
│   ├── AIMessageBubble[1]               AI 消息①
│   │   ├── AIAvatar                     圆形头像（~40px）
│   │   └── BubbleContent               "今天的天气很舒服呢..."
│   │       ├── MessageText             正文文字
│   │       └── Timestamp              "09:30"
│   │
│   ├── UserMessageBubble[1]             用户消息①
│   │   └── BubbleContent               "是呀！很适合散步☁️"
│   │       ├── MessageText
│   │       ├── ReadReceipt             ✓
│   │       └── Timestamp              "09:31"
│   │
│   └── AIMessageBubble[2]               AI 新消息（动效触发者）★
│       ├── AIAvatar
│       └── BubbleContent               "要一起去公园走走吗？🌸"
│           ├── MessageText
│           └── Timestamp              "09:31"
│               └── [BubbleBloomAnimation]  ← 气泡绽放动效附着点
│
└── InputBar                             输入栏
    ├── MicButton                        🎤 麦克风图标
    ├── InputField                       输入框
    │   └── PlaceholderText             "输入消息..."
    ├── AddButton                        + 圆形按钮
    └── HomeIndicator                    底部 Home Bar（34px Safe Area）
```

---

## 运行时组件层 — 帧②（情绪球脉冲强调态）

```
ChatScreen（情绪球动效强调帧）
├── StatusBar
│
├── ChatNavBar
│   ├── NavBackButton
│   ├── NavCenter
│   │   ├── EmotionOrb（size=lg，动效态）  ← 脉冲动效强调展示（~80px）
│   │   │   ├── OrbCore（白色核心）
│   │   │   ├── OrbGradientLayer（渐变层）
│   │   │   └── OrbGlowLayer（外发光层）
│   │   │       └── [PulseAnimation]     scale 1.0↔1.06，1200ms infinite
│   │   ├── NavTitle                     "悠悠"
│   │   └── NavSubtitle                  "在线"
│   └── NavMenuButton
│
├── MessageList（ScrollView）
│   ├── AIMessageBubble[1]
│   │   ├── AIAvatar
│   │   └── BubbleContent               "今天的天气很舒服呢..."
│   ├── UserMessageBubble[1]
│   │   └── BubbleContent               "是呀！很适合散步☁️"
│   └── AIMessageBubble[2]               "要一起去公园走走吗？🌸"
│
└── InputBar
    ├── MicButton
    ├── InputField
    │   └── PlaceholderText
    ├── AddButton
    └── HomeIndicator
```

---

## 运行时组件层 — 帧③（语音波实时态）

```
ChatScreen（语音播放中）
├── StatusBar
│
├── ChatNavBar
│   ├── NavBackButton
│   ├── NavCenter
│   │   ├── EmotionOrb（size=sm，正常态）
│   │   ├── NavTitle
│   │   └── NavSubtitle
│   └── NavMenuButton
│
├── MessageList（ScrollView）
│   ├── AIMessageBubble[1]
│   │   ├── AIAvatar
│   │   └── BubbleContent               "今天的天气很舒服呢..."
│   ├── UserMessageBubble[1]
│   │   └── BubbleContent               "是呀！很适合散步"
│   └── [最新消息区域]                    语音播放中（暂无新气泡）
│
├── VoiceWaveContainer                   语音波容器（InputBar 上方）
│   └── VoiceWaveDots                   5 个实时波点
│       ├── WaveDot[1]                  粉色 #FFB7C5
│       ├── WaveDot[2]
│       ├── WaveDot[3]（中心，振幅最高）
│       ├── WaveDot[4]
│       └── WaveDot[5]                  薰衣草 #C8B6FF
│           └── [VoiceWaveAnimation]    实时 audioLevel 驱动
│
└── InputBar
    ├── MicButton（激活态？设计稿未定义）
    ├── InputField
    ├── AddButton
    └── HomeIndicator
```

---

## 运行时组件层 — 帧④（页面过渡，Apple Sheet 风格）

```
TransitionContainer（z-index 层叠容器）
│
├── [Layer 0] HomeScreen（底层，过渡中状态）
│   │   [transform: translateY(8px) scale(0.99) brightness(0.92)]
│   │
│   ├── StatusBar
│   ├── HomeNavBar
│   │   ├── HomeTitle                   "yuoyuo"
│   │   └── HomeMenuButton             ···
│   ├── HomeContent
│   │   ├── WelcomeGreeting            "早上好，今天想和悠悠聊什么呢？"
│   │   ├── ContinueChatCard           "继续聊天"卡片
│   │   │   ├── CardTitle             "继续聊天"
│   │   │   └── CardSubtitle          "上次聊到：散步和云朵🌿"
│   │   ├── RecentSection              "最近对话"区域
│   │   │   └── ConversationItem[]    对话列表项（含头像缩略图）
│   │   └── [DimOverlay]              亮度降至 0.92 的遮罩层
│   └── HomeTabBar
│
└── [Layer 10] ChatScreen（顶层，Sheet 滑入态）
    │   [transform: translateY(0) — 已完成滑入]
    │
    ├── DragHandle                      顶部拖拽手柄指示器
    ├── StatusBar
    ├── ChatNavBar
    │   ├── NavBackButton
    │   ├── NavCenter
    │   │   ├── EmotionOrb（size=sm）
    │   │   ├── NavTitle               "悠悠"
    │   │   └── NavSubtitle            "在线"
    │   └── NavMenuButton
    ├── MessageList（ScrollView）
    │   ├── AIMessageBubble[1]
    │   │   ├── AIAvatar
    │   │   └── BubbleContent         "今天的天气很舒服呢..."
    │   ├── UserMessageBubble[1]
    │   │   └── BubbleContent         "是呀！很适合散步"
    │   └── AIMessageBubble[2]
    │       └── BubbleContent         "要一起去公园走走吗？🌸"
    └── InputBar
        ├── MicButton
        ├── InputField
        ├── AddButton
        └── HomeIndicator
```

---

## 共享组件汇总

```
SharedComponents（跨帧复用）
├── EmotionOrb                  情绪球（size: sm | lg）
├── AIMessageBubble             AI 消息气泡
│   ├── AIAvatar               圆形头像
│   ├── MessageText            消息文字
│   └── Timestamp              时间戳
├── UserMessageBubble           用户消息气泡
│   ├── MessageText
│   ├── ReadReceipt            已读回执 ✓
│   └── Timestamp
├── InputBar                    输入栏
│   ├── MicButton
│   ├── InputField
│   └── AddButton
├── ChatNavBar                  聊天页导航栏
├── StatusBar                   系统状态栏
└── VoiceWaveDots               语音波点组件
```
