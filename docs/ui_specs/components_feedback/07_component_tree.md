# 07 Component Tree — 完整 ASCII 组件树

## 画布总体结构

```
Canvas (1536×1024, bg: #FFF0F3)
│
├── PhoneFrame_1 (iPhone 14, Toast 场景)
│   └── Screen_1
│       ├── StatusBar
│       │   ├── TimeLabel "9:41"
│       │   └── SystemIcons (signal, wifi, battery)
│       │
│       ├── ChatNavBar
│       │   ├── Avatar (circle, 36px, real-avatar or blank-placeholder)
│       │   ├── NavInfo
│       │   │   ├── NameLabel "悠悠"
│       │   │   └── StatusLabel "在线·消息将自动发送"
│       │   ├── PhoneIcon
│       │   └── MoreIcon "···"
│       │
│       ├── ChatContentArea (bg: /Users/wanglixun/heart/assets/backgrounds/亮色背景图.png)
│       │   └── ExistingBackgroundVisual (center heart retained)
│       │
│       ├── ChatInputBar
│       │   ├── AddButton (circle outline)
│       │   ├── InputField (placeholder "想对悠悠说点什么呢...")
│       │   └── VoiceButton (circle, bg: #FFB7C5)
│       │
│       └── Toast (z-index: 300, overlay)
│           ├── SuccessIcon (circle #FFB7C5 + white checkmark)
│           └── ToastLabel "兑换成功，会员已激活。"
│
├── PhoneFrame_2 (iPhone 14, Modal 场景)
│   └── Screen_2
│       ├── StatusBar
│       │   ├── TimeLabel "9:41"
│       │   └── SystemIcons
│       │
│       ├── ChatNavBar (same as Screen_1)
│       │
│       ├── ChatContentArea (bg: existing light background, dimmed by scrim)
│       │   └── ExistingBackgroundVisual (center, partially obscured)
│       │
│       ├── ChatInputBar (dimmed by scrim)
│       │
│       ├── ScrimOverlay_Modal (z-index: 100, rgba(0,0,0,0.45), full screen)
│       │
│       └── ModalCard (z-index: 200, centered, 306×280px est.)
│           ├── IllustrationArea
│           │   └── CloudHeartIllustration (48px, centered)
│           ├── ModalTitle "确认退出登录？"
│           ├── ModalBody "退出后需要重新通过邮箱链接登录。"
│           ├── PrimaryButton
│           │   └── ButtonLabel "确认退出"
│           └── SecondaryButton
│               └── ButtonLabel "取消"
│
├── PhoneFrame_3 (iPhone 14, BottomSheet 场景)
│   └── Screen_3
│       ├── StatusBar
│       │   ├── TimeLabel "9:41"
│       │   └── SystemIcons
│       │
│       ├── ChatNavBar (same as Screen_1)
│       │
│       ├── ChatContentArea (bg: existing light background, dimmed by scrim)
│       │   └── ExistingBackgroundVisual (upper area, partially obscured)
│       │
│       ├── ScrimOverlay_Sheet (z-index: 100, rgba(0,0,0,0.25), full screen)
│       │
│       └── BottomSheet (z-index: 200, bottom-anchored, 374×320px est.)
│           ├── DragHandle (36×4px, centered, #D0D0D0)
│           ├── SheetTitle "选择主题"
│           ├── RadioGroup
│           │   ├── RadioOption_1 (selected)
│           │   │   ├── RadioIcon_Selected (20px, #FFB7C5)
│           │   │   └── OptionLabel "浅色"
│           │   ├── RadioOption_2 (unselected)
│           │   │   ├── RadioIcon_Default (20px, #CCCCCC)
│           │   │   └── OptionLabel "深色"
│           │   └── RadioOption_3 (unselected)
│           │       ├── RadioIcon_Default (20px, #CCCCCC)
│           │       └── OptionLabel "跟随系统"
│           └── PrimaryButton (full-width)
│               └── ButtonLabel "完成"
│
└── AnnotationArea (canvas bottom, y≈940px)
    ├── AnnotationItem_1
    │   ├── BadgeCircle "1" (#FFB7C5, 24px)
    │   └── AnnotationText "提示信息·2.5秒自动关闭"
    ├── AnnotationItem_2
    │   ├── BadgeCircle "2" (#FFB7C5, 24px)
    │   └── AnnotationText "莫代尔·破坏性但温暖"
    └── AnnotationItem_3
        ├── BadgeCircle "3" (#FFB7C5, 24px)
        └── AnnotationText "底部页面·用于选项选择"
```

---

## 组件复用关系树

```
PrimaryButton
├── [used in] ModalCard → ButtonLabel "确认退出"
└── [used in] BottomSheet → ButtonLabel "完成"

SecondaryButton
└── [used in] ModalCard → ButtonLabel "取消"

ScrimOverlay
├── [used in] Screen_2 behind ModalCard
└── [used in] Screen_3 behind BottomSheet

ChatNavBar
├── [used in] Screen_1 (Toast host)
├── [used in] Screen_2 (Modal host)
└── [used in] Screen_3 (Sheet host)

ChatInputBar
├── [used in] Screen_1 (Toast host)
├── [used in] Screen_2 (Modal host, dimmed)
└── [used in] Screen_3 (Sheet host, hidden behind sheet)

RadioOption
└── [used in] BottomSheet × 3 instances
    ├── "浅色" — selected
    ├── "深色" — unselected
    └── "跟随系统" — unselected
```

---

## 层级深度说明

| 组件 | 最大层级深度 |
|------|-------------|
| Toast | 3层（Canvas → PhoneFrame → Screen → Toast → Icon/Label） |
| Modal | 5层（Canvas → PhoneFrame → Screen → ScrimOverlay → ModalCard → SubElements） |
| BottomSheet | 6层（Canvas → PhoneFrame → Screen → ScrimOverlay → BottomSheet → RadioGroup → RadioOption → SubElements） |

---

## 状态变体树（BottomSheet RadioGroup）

```
RadioGroup
├── state: "浅色" selected
│   └── RadioOption "浅色" [selected=true]
│   └── RadioOption "深色" [selected=false]
│   └── RadioOption "跟随系统" [selected=false]
├── state: "深色" selected
│   └── RadioOption "浅色" [selected=false]
│   └── RadioOption "深色" [selected=true]
│   └── RadioOption "跟随系统" [selected=false]
└── state: "跟随系统" selected
    └── RadioOption "浅色" [selected=false]
    └── RadioOption "深色" [selected=false]
    └── RadioOption "跟随系统" [selected=true]
```
