# 07 Component Tree — 聊天页 Chat（浅色模式）

## ASCII 组件树（从 Page 根节点开始）

```
Page（聊天页，390×844 pt，浅色模式）
│
├── BackgroundLayer（Z0，绝对定位，全屏，pointer-events: none）
│   └── BackgroundImage（/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png，cover）
│
├── StatusBar（Z1，fixed top，47pt 高，系统原生）
│   ├── TimeLabel（"9:41"，左侧，15pt，font-weight 600）
│   └── SystemIcons（右侧，信号+WiFi+电池）
│       ├── SignalIcon
│       ├── WifiIcon
│       └── BatteryIcon
│
├── ChatHeader（Z2，fixed top，90pt from top，80pt 高）
│   │   [背景：rgba(255,255,255,0.55)，blur 20pt，底圆角 24pt]
│   ├── BackButton（左侧，44×44pt 触摸区）
│   │   └── ChevronLeftIcon（12×20pt，#3A3A4A）
│   ├── CharacterBlock（Flex Row，align-center，gap 10pt）
│   │   ├── CharacterAvatar（48×48pt，圆形裁切）
│   │   │   └── AvatarImageOrBlankPlaceholder（真实头像优先，否则空白占位头像组件）
│   │   └── CharacterInfo（Flex Column，gap 2pt）
│   │       ├── CharacterName（"小屿"，17pt，font-weight 600，#3A3A4A）
│   │       └── OnlineStatusRow（Flex Row，align-center，gap 4pt）
│   │           ├── OnlineDot（6×6pt 圆形，#5FC8E8）
│   │           └── OnlineLabel（"温柔在线"，13pt，#888888）
│   └── MoreButton（右侧，44×44pt 触摸区）
│       └── EllipsisIcon（水平三点，#3A3A4A）
│
├── MessageScrollArea（Z3，可滚动，top 紧接 Header，bottom 紧接 Composer）
│   │   [overflow-y: scroll，scrollbar: hidden，padding 16pt 水平]
│   │
│   ├── DateSeparator（水平居中）
│   │   └── DateLabel（"今天 · 上午 9:41"，12pt，#999999，居中）
│   │
│   ├── AITextBubble_1（左对齐，align-self: flex-start）
│   │   │   [背景：rgba(255,255,255,0.75)，圆角：20/20/20/6pt]
│   │   └── MessageText（"早上好，昨晚睡得怎么样？"，16pt，#3A3A4A）
│   │
│   ├── UserTextBubble_1（右对齐，align-self: flex-end）
│   │   │   [背景：#A7C7E7，圆角：6/20/20/20pt]
│   │   └── MessageText（"做了个奇怪的梦。"，16pt，#FFFFFF）
│   │
│   ├── AITextBubble_2（左对齐，align-self: flex-start）
│   │   │   [背景：rgba(255,255,255,0.75)，圆角：20/20/20/6pt]
│   │   └── MessageText（"讲给我听呀～我陪着你。"，16pt，#3A3A4A）
│   │
│   ├── AIVoiceBubble（左对齐，align-self: flex-start，约 300pt 宽）
│   │   │   [背景：rgba(255,255,255,0.75)，圆角：20/20/20/6pt]
│   │   ├── VoiceMainRow（Flex Row，align-center，gap 10pt）
│   │   │   ├── PlayButton（32×32pt 圆形触摸区）
│   │   │   │   └── PlayIcon（三角形，14pt，#FFB7C5）
│   │   │   ├── WaveformVisualizer（约 170×32pt）
│   │   │   │   └── WaveformBars（约 20-25 条，渐变色 #FFB7C5→#C8B6FF）
│   │   │   └── DurationLabel（"0:18"，13pt，#999999）
│   │   └── VoiceCaptionRow（水平居中）
│   │       └── CaptionText（"AI朗读 · 可点击播放"，12pt，#AAAAAA）
│   │
│   ├── UserTextBubble_2（右对齐，align-self: flex-end）
│   │   │   [背景：#A7C7E7，圆角：6/20/20/20pt]
│   │   └── MessageText（"好。"，16pt，#FFFFFF）
│   │
│   └── TypingIndicator（左对齐，align-self: flex-start）
│       │   [背景：rgba(255,255,255,0.75)，圆角：20/20/20/6pt，约 72×48pt]
│       ├── TypingDot_1（10×10pt 圆，#FFB7C5，动画 delay 0ms）
│       ├── TypingDot_2（10×10pt 圆，#FFB7C5，动画 delay 150ms）
│       └── TypingDot_3（10×10pt 圆，#FFB7C5，动画 delay 300ms）
│
├── ChatComposer（Z4，fixed bottom，约 64pt 高）
│   │   [背景：rgba(255,255,255,0.65)，blur 24pt，圆角 32pt（胶囊形）]
│   │   [bottom: 46pt（含 Home Indicator 区域），左右间距各 16pt]
│   ├── AttachButton（"+"，36×36pt 圆形，图标 #BBBBBB）
│   │   └── PlusIcon（约 20pt，#BBBBBB）
│   ├── TextInput（弹性宽度，flex: 1）
│   │   └── PlaceholderText（"想和小屿说点什么..."，15pt，#BBBBBB）
│   └── SendButton（40×40pt 圆形，#FFB7C5 背景）
│       └── SendIcon（纸飞机，18pt，#FFFFFF，右上 45° 倾斜）
│
└── HomeIndicator（Z5，系统原生，fixed bottom）
    └── HomeBar（134×5pt，#3A3A4A，圆角 full，底边距 8pt，水平居中）
```

---

## 组件层级关系说明

| 层级 | 组件 | 定位方式 | Z-index |
|------|------|---------|---------|
| Z0 | BackgroundLayer | absolute，全屏 | 0 |
| Z1 | StatusBar | fixed top | 1 |
| Z2 | ChatHeader | fixed top（StatusBar 之下） | 2 |
| Z3 | MessageScrollArea | relative，可滚动 | 3 |
| Z4 | ChatComposer | fixed bottom | 4 |
| Z5 | HomeIndicator | fixed bottom（最高层） | 5 |

---

## 消息列表内部组件顺序（由上到下，可滚动内容）

1. `DateSeparator` — 时间分隔符
2. `AITextBubble_1` — AI 文字消息（早上好…）
3. `UserTextBubble_1` — 用户消息（做了个奇怪的梦）
4. `AITextBubble_2` — AI 文字消息（讲给我听呀…）
5. `AIVoiceBubble` — AI 语音消息（0:18 语音播放器）
6. `UserTextBubble_2` — 用户消息（好。）
7. `TypingIndicator` — AI 打字中指示器（3个粉色圆点）

---

## 注意事项

- `MessageScrollArea` 是唯一可滚动容器
- `ChatHeader` 和 `ChatComposer` 均为 `position: fixed`，不随列表滚动
- `BackgroundLayer` 使用 `pointer-events: none`，不响应用户触摸事件
- `HomeIndicator` 为系统原生控件，App 不应自定义其外观
- `StatusBar` 为系统原生控件，使用深色文字（light content mode）匹配浅色背景
