# 07 Component Tree — 离线降级状态页

## ASCII 组件树（完整层级）

```
StateOfflinePage
│
├── StatusBar                               [系统组件，Z:7]
│   ├── TimeLabel "9:41"
│   └── SystemIconsGroup
│       ├── SignalIcon
│       ├── WiFiIcon
│       └── BatteryIcon
│
├── ChatNavBar                              [固定顶部，Z:5]
│   ├── BackButton                          [触摸目标 44×44pt]
│   │   └── BackArrowIcon (24×24pt, #3A3A4A)
│   ├── AvatarImage (40×40pt, circle)       [真实头像或空白占位头像]
│   ├── NavTextGroup                        [垂直堆叠]
│   │   ├── NavTitle "悠悠" (17pt SemiBold, #3A3A4A)
│   │   └── NavSubtitle                     [★ 离线状态变体]
│   │       "离线 · 消息将自动发送" (12pt Regular, #A0A0B0)
│   └── NavActionGroup                      [右侧图标组]
│       ├── PhoneButton (44×44pt touch)
│       │   └── PhoneIcon (22×22pt, #3A3A4A)
│       └── MoreButton (44×44pt touch)
│           └── MoreDotsIcon (22×6pt, #3A3A4A)
│
├── OfflineBanner                           [横幅卡片，Z:4，Margin H:16pt]
│   ├── CloudIcon (24×20pt, #FFB7C5)        [★ 离线专属]
│   ├── BannerText                          [flex:1]
│   │   "网络不太稳定，刚才的消息已暂存。"
│   │   (14pt Regular, #3A3A4A)
│   └── RetryButton                         [68×32pt, pill, 边框#FFB7C5]
│       ├── RetryIcon (13×13pt, #FFB7C5)    [重连中时旋转动画]
│       └── RetryLabel "重试" (13pt Medium, #FFB7C5)
│
├── ChatScrollView                          [可滚动区域，Z:2，opacity:0.92]  ★ 暗淡
│   │
│   ├── ── TimestampLabel "昨天 22:18" (12pt, #ACACAC, 居中)
│   │
│   ├── AiBubbleGroup                       [左对齐，flexRow]
│   │   ├── AvatarImage (36×36pt, circle)   [真实头像或空白占位头像]
│   │   └── AiBubble                        [白色气泡，TL:4pt其余16pt]
│   │       ├── BubbleText
│   │       │   "今天过得怎么样呀？"
│   │       │   "有没有遇到什么开心的事～"
│   │       │   (15pt Regular, #3A3A4A)
│   │       └── HeartDeco ♥                 [独立浮动，粉色，约16pt，旋转-10°]
│   │
│   ├── ── TimestampLabel "昨天 22:21" (12pt, #ACACAC, 居中)
│   │
│   ├── UserBubbleGroup                     [右对齐]
│   │   ├── UserBubble                      [粉色渐变气泡，TR:4pt其余16pt]
│   │   │   └── BubbleText
│   │   │       "还不错！下班路上看到超美的晚霞，"
│   │   │       "感觉一天的疲惫都被治愈了 🌅"
│   │   │       (15pt Regular, #3A3A4A)
│   │   └── DoubleTick ✓✓ (14pt, #A7C7E7)  [气泡右下角外侧]
│   │
│   ├── ── TimestampLabel "昨天 22:23" (12pt, #ACACAC, 居中)
│   │
│   ├── AiBubbleGroup                       [左对齐，flexRow]
│   │   ├── AvatarImage (36×36pt, circle)
│   │   └── AiBubble                        [白色气泡]
│   │       └── BubbleText
│   │           "晚霞总是能带来好心情呢 ☁️"
│   │           "要记得多抬头看看天空哦～"
│   │           (15pt Regular, #3A3A4A)
│   │
│   ├── ── TimestampLabel "昨天 22:25" (12pt, #ACACAC, 居中)
│   │
│   ├── UserBubbleGroup                     [右对齐]
│   │   ├── UserBubble                      [粉色渐变气泡]
│   │   │   └── BubbleText
│   │   │       "嗯嗯，你总是这么温柔，陪着我 🥰"
│   │   │       (15pt Regular, #3A3A4A)
│   │   └── DoubleTick ✓✓ (14pt, #A7C7E7)
│   │
│   └── StagedDivider                       [★ 离线专属，内嵌于滚动流中]
│       ├── StagedLabel                     [居中]
│       │   "以下为暂存消息" (13pt Regular, #C0A0A0)
│       └── StagedSubLabel                  [居中，间距4pt]
│           "网络恢复后会自动发送" (12pt Regular, #C0A0A0)
│
└── Composer                                [固定底部，Z:6]
    ├── ComposerBackground                  [rgba(255,255,255,0.80) + blur(8pt)]
    ├── ComposerTopBorder                   [0.5pt, rgba(0,0,0,0.08)]
    ├── AddButton (36×36pt, circle)
    │   ├── CircleBorder (1pt, #D0D0D0)
    │   └── AddIcon (18×18pt, #A0A0A8)
    ├── TextInput                           [flex:1, pill形, 36pt高]
    │   ├── InputBackground (rgba(255,255,255,0.60))
    │   └── Placeholder "想对悠悠说点什么呢..." (15pt, #C0C0C8)
    └── ClockBadgeButton                    [★ 离线专属，替代发送按钮]
        ├── CircleFill (36×36pt, #FFB7C5)
        ├── ClockIcon (20×20pt, #FFFFFF)
        └── GlowShadow (0 2pt 6pt rgba(255,183,197,0.40))
```

---

## 层级说明

| 层级标记 | 说明 |
|---------|------|
| `★ 离线专属` | 仅在离线状态下出现或发生变化的元素 |
| `opacity:0.92` | ChatScrollView 整体透明度降低 |
| `[Z:N]` | Z-index 层级 |
| `[flex:1]` | 弹性伸缩填满可用空间 |
| `[居中]` | 水平居中对齐 |

---

## 组件复用关系

```
AvatarImageOrBlankPlaceholder ─── 复用 ──► ChatNavBar (40×40pt)
                               └─ 复用 ──► AiBubbleGroup (36×36pt, scaled)

AiBubble ─── 复用 ──► 所有 AI 消息行
UserBubble ── 复用 ──► 所有用户消息行
DoubleTick ── 复用 ──► 所有用户消息（已读状态）

OfflineBanner ─── 仅 offline state
ClockBadgeButton ─ 仅 offline state（替代 SendButton）
StagedDivider ──── 仅 offline state（及暂存消息场景）
NavSubtitle ─────── 状态切换文字/颜色（Props 控制）
```
