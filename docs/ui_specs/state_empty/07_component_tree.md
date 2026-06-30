# 07 Component Tree — 加载 / 空状态

## 完整 ASCII 组件树

```
18_state_empty (Canvas 1024×1536)
│
├── [Panel 1] EmptyChatState (0–768px)
│   │   background: /Users/wanglixun/heart/assets/backgrounds/亮色背景图.png
│   │
│   ├── StatusBar (1024×60px, Z:10)
│   │   ├── TimeText "9:41"
│   │   │     font: PingFang SC Semibold ~28px
│   │   │     color: #3A3A4A
│   │   └── SystemIcons (Row, gap ~12px)
│   │         ├── SignalIcon (SF Symbols)
│   │         ├── WiFiIcon (SF Symbols)
│   │         └── BatteryIcon (SF Symbols)
│   │               color: #3A3A4A
│   │
│   ├── ChatHeader (1024×100px, Z:10)
│   │   ├── LeftGroup (Row, align: center, gap ~16px)
│   │   │   ├── BackButton "<"
│   │   │   │     size: 48×48px
│   │   │   │     color: #8A8A9A
│   │   │   │     touch-target: 48×48px
│   │   │   ├── CharacterAvatar
│   │   │   │     shape: circle, dia: ~88px
│   │   │   │     border: 3px solid #FFFFFF
│   │   │   │     shadow: 0 2px 8px rgba(0,0,0,0.10)
│   │   │   │     src: real-avatar or blank-placeholder
│   │   │   └── CharacterInfo (Column, align: left, gap ~4px)
│   │   │         ├── CharacterName "悠悠"
│   │   │         │     font: PingFang SC Semibold ~32px
│   │   │         │     color: #3A3A4A
│   │   │         └── StatusText "在线 · 愿意倾听你的一切"
│   │   │               font: PingFang SC Regular ~22px
│   │   │               color: #A07888
│   │   │               variant: default
│   │   └── RightGroup (Row, align: center, gap ~24px)
│   │         ├── PhoneButton
│   │         │     size: 44×44px
│   │         │     color: #8A8A9A
│   │         │     icon: icon_phone.svg
│   │         └── MoreMenuButton "···"
│   │               size: 48×48px
│   │               color: #8A8A9A
│   │               icon: icon_more_menu.svg
│   │
│   ├── EmptyIllustrationArea (~700×380px, Z:2)
│   │   │   layout: Stack (absolute positioning)
│   │   │   align: center
│   │   │
│   │   ├── CloudGlow (Z:1)
│   │   │     size: ~600×280px
│   │   │     type: component glow layer
│   │   │     opacity: ~0.60
│   │   │     blur: ~24px
│   │   │     colors: #FFB7C5 → #C8B6FF → transparent
│   │   └── GemHeart (Z:2)
│   │         size: ~240×220px
│   │         src: component-rendered glass heart
│   │         opacity: 1.0
│   │         animation: pulse (Y ±6px, 2s, ease-in-out, infinite)
│   │
│   ├── GuideText (auto×~44px, Z:2)
│   │     content: "我们刚认识，先聊点什么吧？"
│   │     font: PingFang SC Medium ~36px
│   │     color: #3A3A4A
│   │     align: center
│   │     margin-top: ~32px (from IllustrationArea)
│   │
│   └── SuggestionPillsRow (Row, gap ~16px, align: center, Z:2)
│         │   margin-top: ~32px (from GuideText)
│         │
│         ├── SuggestionPill[0]
│         │     label: "今天心情如何？"
│         │     icon: icon_smile_circle.svg (#FFB7C5)
│         │     height: ~64px, radius: ~32px
│         │     bg: rgba(255,255,255,0.80)
│         │     border: 1.5px rgba(255,183,197,0.40)
│         │     shadow: 0 2px 8px rgba(255,183,197,0.25)
│         │     interaction: tap → send
│         ├── SuggestionPill[1]
│         │     label: "陪我说话"
│         │     icon: icon_chat_bubble.svg (#FFB7C5)
│         │     [same visual specs as Pill[0]]
│         │     interaction: tap → send
│         └── SuggestionPill[2]
│               label: "给我讲个故事"
│               icon: icon_star.svg (#E8C84A)
│               [same visual specs, star icon gold]
│               interaction: tap → send
│
└── [Panel 2] LoadingState (768–1536px)
    │   background: /Users/wanglixun/heart/assets/backgrounds/亮色背景图.png
    │
    ├── StatusBar (same as Panel 1)
    │   ├── TimeText "9:41"
    │   └── SystemIcons
    │
    ├── ChatHeader — Loading Variant (1024×100px, Z:10)
    │   ├── LeftGroup (Row, same structure as Panel 1)
    │   │   ├── BackButton "<"
    │   │   ├── CharacterAvatar (same: real-avatar or blank-placeholder)
    │   │   └── CharacterInfo (Column)
    │   │         ├── CharacterName "悠悠"
    │   │         └── StatusText "···" (DotTypingAnimation)
    │   │               animation: 3 dots sequential opacity 0→1
    │   │               cycle: ~900ms, infinite
    │   │               variant: loading
    │   └── RightGroup (same as Panel 1)
    │         ├── PhoneButton
    │         └── MoreMenuButton "···"
    │
    ├── SkeletonChatArea (~1024×492px, Z:2)
    │   │   padding-horizontal: ~40px
    │   │
    │   ├── SkeletonBubble[0] — Left (Row, align:center, gap ~16px)
    │   │   │   margin-top: ~48px
    │   │   │   align: flex-start
    │   │   │
    │   │   ├── SkeletonAvatarPlaceholder
    │   │   │     shape: circle, dia: ~72px
    │   │   │     color: #F2C8D0
    │   │   │     shimmer: overlay enabled
    │   │   └── SkeletonMessageBar[0]
    │   │         size: ~480×56px
    │   │         radius: ~16px
    │   │         color: #F2D0D8
    │   │         shimmer: linear-gradient sweep, 1400ms, linear, infinite
    │   │
    │   ├── SkeletonBubble[1] — Right (Row, align:center, gap ~16px)
    │   │   │   margin-top: ~32px
    │   │   │   align: flex-end
    │   │   │
    │   │   ├── SkeletonMessageBar[1]
    │   │   │     size: ~420×56px
    │   │   │     radius: ~16px
    │   │   │     color: #F2D0D8
    │   │   │     shimmer: same as above
    │   │   └── SkeletonAvatarPlaceholder
    │   │         shape: circle, dia: ~60px
    │   │         color: #F2C8D0
    │   │         shimmer: enabled
    │   │
    │   └── SkeletonBubble[2] — Left, Multiline (Row, align:flex-start, gap ~16px)
    │       │   margin-top: ~32px
    │       │   align: flex-start
    │       │
    │       ├── SkeletonAvatarPlaceholder
    │       │     shape: circle, dia: ~72px
    │       │     color: #F2C8D0
    │       │     shimmer: enabled
    │       └── SkeletonMessageBarGroup (Column, gap ~12px)
    │             ├── SkeletonMessageBar[2a]
    │             │     size: ~420×48px
    │             │     radius: ~14px
    │             │     color: #F2D0D8
    │             │     shimmer: enabled
    │             └── SkeletonMessageBar[2b]
    │                   size: ~300×48px
    │                   radius: ~14px
    │                   color: #F2D0D8
    │                   shimmer: enabled
    │
    └── InputBar (1024×116px, Z:10)
          │   padding-horizontal: ~40px
          │   padding-bottom: ~34px (safe area)
          │   background: existing light background over glass input container
          │
          ├── AddButton "+"
          │     shape: circle, dia: ~64px
          │     border: ~2px solid #A8A8B8
          │     icon: icon_add_circle.svg
          │     color: #A8A8B8
          ├── InputField (flex:1)
          │     placeholder: "想对悠悠说什么呢..."
          │     placeholder-color: #C8B6C8
          │     font: PingFang SC Regular ~26px
          │     background: transparent
          └── MicButton
                shape: circle, dia: ~64px
                border: ~2px solid #FFB7C5
                icon: icon_microphone.svg
                icon-color: #FFB7C5
```

---

## 组件关系图（扁平）

```
18_state_empty
├── [Shared] StatusBar
├── [Shared] ChatHeader
│   ├── BackButton
│   ├── CharacterAvatar
│   ├── CharacterInfo
│   │   ├── CharacterName
│   │   └── StatusText [variant: default | loading]
│   ├── PhoneButton
│   └── MoreMenuButton
├── [Empty] EmptyIllustrationArea
│   ├── CloudGlow
│   └── GemHeart
├── [Empty] GuideText
├── [Empty] SuggestionPillsRow
│   └── SuggestionPill × 3
│       ├── PillIcon
│       └── PillLabel
├── [Loading] SkeletonChatArea
│   ├── SkeletonBubble × 3
│   │   ├── SkeletonAvatarPlaceholder
│   │   └── SkeletonMessageBar [+ ShimmerOverlay]
│   └── (SkeletonMessageBarGroup for multiline)
└── [Shared] InputBar
    ├── AddButton
    ├── InputField
    └── MicButton
```
