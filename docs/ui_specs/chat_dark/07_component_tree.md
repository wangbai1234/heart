# 07 Component Tree — 聊天页 Chat（深色模式）

## ASCII 组件树

```
Page (ChatDarkScreen)
├── BackgroundLayer                         # 全屏背景层，Z-index: 0
│   └── BackgroundImage                     # /Users/wanglixun/heart/assets/backgrounds/暗色背景图.png
│
├── SafeArea                                # Safe Area 容器（top: 47pt, bottom: 34pt）
│   │
│   ├── StatusBar                           # 系统状态栏，Z-index: 20
│   │   ├── TimeLabel                       # "9:41" 时间文字
│   │   └── StatusIconGroup                 # 右侧系统图标组
│   │       ├── SignalIcon                  # 信号强度（4格满格）
│   │       ├── WifiIcon                    # WiFi（满格）
│   │       └── BatteryIcon                 # 电池（约3/4）
│   │
│   ├── ChatHeader                          # 聊天导航栏，Z-index: 10，fixed top
│   │   ├── HeaderBackground                # 毛玻璃背景 rgba(30,27,40,0.75) + blur(20px)
│   │   ├── BackButton                      # 返回按钮（左侧）
│   │   │   └── ChevronLeftIcon             # "<" 箭头图标，#FFFFFF
│   │   ├── AgentInfoGroup                  # 角色信息区（中左）
│   │   │   ├── AvatarWithGlow              # 圆形头像 + 粉色光晕
│   │   │   │   └── AvatarImageOrBlankPlaceholder
│   │   │   └── AgentNameStatus             # 名称 + 状态（垂直堆叠）
│   │   │       ├── NameLabel               # "小屿" 文字，SemiBold，#FFFFFF
│   │   │       └── StatusRow               # 在线状态行
│   │   │           ├── OnlineDot           # 蓝色圆点 #7EB8F7
│   │   │           └── StatusLabel         # "温柔在线" 文字，rgba(255,255,255,0.70)
│   │   └── MoreButton                      # 更多按钮（右侧）
│   │       └── ThreeDotsIcon               # "···" 图标，#FFFFFF
│   │
│   ├── MessageListScrollView               # 可滚动消息区，Z-index: 1
│   │   │                                   # Padding: 32px 左右
│   │   ├── TimestampDivider                # 时间戳分隔
│   │   │   └── TimestampLabel              # "今天 · 上午 9:41"，rgba(255,255,255,0.45)
│   │   │
│   │   ├── AITextBubble_01                 # AI 文字气泡（左对齐）
│   │   │   ├── BubbleBackground_01         # 气泡背景 rgba(45,40,65,0.90) + 粉色边缘光
│   │   │   └── MessageText_01             # "早上好，昨晚睡得怎么样？" #F0EEFF
│   │   │
│   │   ├── UserTextBubble_01               # 用户文字气泡（右对齐）
│   │   │   ├── BubbleBackground_02         # 靛蓝渐变背景 #3B5BDB → #2F4AC5
│   │   │   └── MessageText_02             # "做了个奇怪的梦。" #FFFFFF
│   │   │
│   │   ├── AITextBubble_02                 # AI 文字气泡（左对齐）
│   │   │   ├── BubbleBackground_03         # 同 AI 气泡背景
│   │   │   └── MessageText_03             # "讲给我听呀～我陪着你。" #F0EEFF
│   │   │
│   │   ├── AIVoiceBubble                   # AI 语音消息气泡（左对齐）
│   │   │   ├── BubbleBackground_04         # 同 AI 气泡背景（较宽）
│   │   │   ├── VoiceControlRow             # 第一行：播放控制
│   │   │   │   ├── PlayButton              # 播放按钮（圆形，粉色半透明背景）
│   │   │   │   │   └── PlayIcon            # 三角形播放图标，#FFB7C5
│   │   │   │   ├── WaveformVisualizer      # 语音波形（多彩竖条）
│   │   │   │   │   └── WaveformBars[]      # 约24-28条不等高竖条，粉→紫→蓝渐变
│   │   │   │   └── DurationLabel           # "0:18" 时长，rgba(255,255,255,0.60)
│   │   │   └── AIReadingHint               # 第二行提示
│   │   │       └── HintLabel               # "AI朗读 · 可点击播放"，rgba(255,255,255,0.45)
│   │   │
│   │   ├── UserTextBubble_02               # 用户文字气泡（右对齐）
│   │   │   ├── BubbleBackground_05         # 靛蓝渐变背景
│   │   │   └── MessageText_05             # "好。" #FFFFFF
│   │   │
│   │   └── TypingIndicatorBubble           # AI 输入中气泡（左对齐）
│   │       ├── BubbleBackground_06         # 同 AI 气泡背景（较小）
│   │       └── TypingDots                  # 三点动效
│   │           ├── Dot_01                  # 第一个粉色圆点 #FFB7C5
│   │           ├── Dot_02                  # 第二个粉色圆点（延迟120ms）
│   │           └── Dot_03                  # 第三个粉色圆点（延迟240ms）
│   │
│   └── ChatInputBar                        # 底部输入栏，Z-index: 10，fixed bottom
│       ├── InputBarBackground              # 毛玻璃背景 rgba(30,27,40,0.80) + blur(20px)
│       ├── PlusButton                      # "+"附加功能按钮（左侧）
│       │   ├── PlusButtonBg                # 圆形背景 rgba(255,255,255,0.12)
│       │   └── PlusIcon                    # "+"图标，#FFFFFF
│       ├── TextInput                       # 文字输入框（中间，flex:1）
│       │   ├── InputBackground             # 胶囊形背景 rgba(255,255,255,0.08)
│       │   └── PlaceholderText             # "想和小屿说点什么..." rgba(255,255,255,0.40)
│       └── SendButton                      # 发送按钮（右侧）
│           ├── SendButtonBg                # 圆形背景 #FFB7C5 + 粉色辉光
│           └── SendIcon                    # 纸飞机图标，#FFFFFF
│
└── HomeIndicator                           # 系统底部指示条（Safe Area bottom内）
    └── IndicatorBar                        # 白色短横线，rgba(255,255,255,0.30)
```

---

## 层级说明

| 层 | 组件 | Z-index | 性质 |
|---|------|---------|------|
| 背景层 | NebulaBackground | 0 | 静态/装饰 |
| 内容层 | MessageListScrollView | 1 | 可滚动 |
| 固定层 | ChatHeader | 10 | fixed top |
| 固定层 | ChatInputBar | 10 | fixed bottom |
| 系统层 | StatusBar | 20 | 系统接管 |
| 系统层 | HomeIndicator | 20 | 系统接管 |

---

## 消息气泡排列顺序（从上到下）

1. TimestampDivider（今天 · 上午 9:41）
2. AITextBubble_01（"早上好，昨晚睡得怎么样？"）— 左对齐
3. UserTextBubble_01（"做了个奇怪的梦。"）— 右对齐
4. AITextBubble_02（"讲给我听呀～我陪着你。"）— 左对齐
5. AIVoiceBubble（语音朗读消息，0:18）— 左对齐
6. UserTextBubble_02（"好。"）— 右对齐
7. TypingIndicatorBubble（"···"输入中）— 左对齐
