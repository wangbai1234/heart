# 07 组件树 — Icon Set（24×24 系统图标）

## 图标库展示画布组件树

```
IconSetCanvas (1024×1024)
├── Background
│   └── CanvasBackground [#FAF0EC, 1024×1024]
│
├── IconGrid (6列×6行)
│   │
│   ├── Row1_NavigationGroup
│   │   ├── Row1Background [白色圆角卡片, ~920×120px, radius:20px]
│   │   ├── IconCell_01 [~112×112px]
│   │   │   └── Icon_Home [24×24dp, stroke:#4A4A6A, strokeWidth:1.5]
│   │   │       ├── Path_RoofTriangle
│   │   │       └── Path_DoorRect
│   │   ├── IconCell_02 [~112×112px]
│   │   │   └── Icon_Chat [24×24dp]
│   │   │       ├── Path_BubbleOutline
│   │   │       ├── Circle_Dot1
│   │   │       ├── Circle_Dot2
│   │   │       └── Circle_Dot3
│   │   ├── IconCell_03 [~112×112px]
│   │   │   └── Icon_AICompanion [24×24dp]
│   │   │       ├── Path_PersonCircle
│   │   │       ├── Path_Head
│   │   │       ├── Path_Shoulders
│   │   │       └── Path_HeartDecoration [右下角附加心形]
│   │   ├── IconCell_04 [~112×112px]
│   │   │   └── Icon_Settings [24×24dp]
│   │   │       ├── Path_GearOuter [8齿轮廓]
│   │   │       └── Circle_GearCenter
│   │   ├── IconCell_05 [~112×112px]
│   │   │   └── Icon_Profile [24×24dp]
│   │   │       ├── Circle_ProfileOuter
│   │   │       ├── Circle_Head
│   │   │       └── Path_Shoulders
│   │   └── IconCell_06 [~112×112px]
│   │       └── Icon_Search [24×24dp]
│   │           ├── Circle_Lens
│   │           └── Path_Handle
│   │
│   ├── Row2_ChatGroup
│   │   ├── IconCell_07 [~112×112px]
│   │   │   └── Icon_Send [24×24dp]
│   │   │       └── Path_PaperPlane
│   │   ├── IconCell_08 [~112×112px]
│   │   │   └── Icon_Microphone [24×24dp]
│   │   │       ├── Path_MicCapsule
│   │   │       ├── Path_MicStem
│   │   │       └── Path_MicBase [U形支架]
│   │   ├── IconCell_09 [~112×112px]
│   │   │   └── Icon_MicrophoneOff [24×24dp]
│   │   │       ├── Path_MicCapsule
│   │   │       ├── Path_MicStem
│   │   │       ├── Path_MicBase
│   │   │       └── Path_SlashLine [斜线覆盖]
│   │   ├── IconCell_10 [~112×112px]
│   │   │   └── Icon_Emoji [24×24dp]
│   │   │       ├── Circle_Face
│   │   │       ├── Circle_EyeLeft
│   │   │       ├── Circle_EyeRight
│   │   │       └── Path_Smile
│   │   ├── IconCell_11 [~112×112px]
│   │   │   └── Icon_Sticker [24×24dp]
│   │   │       ├── Path_NoteBody [带翻角矩形]
│   │   │       └── Path_FoldedCorner [右上折角]
│   │   └── IconCell_12 [~112×112px]
│   │       └── Icon_Add [24×24dp]
│   │           ├── Circle_AddOuter
│   │           ├── Path_HorizontalBar
│   │           └── Path_VerticalBar
│   │
│   ├── Row3_MediaGroup
│   │   ├── IconCell_13 [~112×112px]
│   │   │   └── Icon_Play [24×24dp]
│   │   │       ├── Circle_PlayOuter
│   │   │       └── Path_PlayTriangle
│   │   ├── IconCell_14 [~112×112px]
│   │   │   └── Icon_Pause [24×24dp]
│   │   │       ├── Circle_PauseOuter
│   │   │       ├── Path_PauseBar1
│   │   │       └── Path_PauseBar2
│   │   ├── IconCell_15 [~112×112px]
│   │   │   └── Icon_Waveform [24×24dp]
│   │   │       ├── Path_Bar1 [最短]
│   │   │       ├── Path_Bar2
│   │   │       ├── Path_Bar3 [最高,居中]
│   │   │       ├── Path_Bar4
│   │   │       └── Path_Bar5 [最短]
│   │   ├── IconCell_16 [~112×112px]
│   │   │   └── Icon_VolumeUp [24×24dp]
│   │   │       ├── Path_SpeakerBody
│   │   │       ├── Path_Wave1 [内弧]
│   │   │       └── Path_Wave2 [外弧]
│   │   ├── IconCell_17 [~112×112px]
│   │   │   └── Icon_Mute [24×24dp]
│   │   │       ├── Path_SpeakerBody
│   │   │       ├── Path_XLine1
│   │   │       └── Path_XLine2
│   │   └── IconCell_18 [~112×112px]
│   │       └── Icon_Headphone [24×24dp]
│   │           ├── Path_HeadBand [弧形头梁]
│   │           ├── Path_EarCupLeft
│   │           └── Path_EarCupRight
│   │
│   ├── Row4_SystemGroup
│   │   ├── IconCell_19 [~112×112px]
│   │   │   └── Icon_Lock [24×24dp]
│   │   │       ├── Path_LockBody [矩形]
│   │   │       ├── Path_LockShackle [U形锁环]
│   │   │       └── Circle_Keyhole
│   │   ├── IconCell_20 [~112×112px]
│   │   │   └── Icon_Key [24×24dp]
│   │   │       ├── Circle_KeyHead
│   │   │       ├── Path_KeyStem
│   │   │       ├── Path_KeyTooth1
│   │   │       └── Path_KeyTooth2
│   │   ├── IconCell_21 [~112×112px]
│   │   │   └── Icon_Bell [24×24dp]
│   │   │       ├── Path_BellBody
│   │   │       ├── Circle_BellTop [挂钩圆]
│   │   │       └── Path_BellClapper [铃舌弧]
│   │   ├── IconCell_22 [~112×112px]
│   │   │   └── Icon_Moon [24×24dp]
│   │   │       └── Path_CrescentMoon
│   │   ├── IconCell_23 [~112×112px]
│   │   │   └── Icon_Sun [24×24dp]
│   │   │       ├── Circle_SunCore
│   │   │       ├── Path_Ray1
│   │   │       ├── Path_Ray2
│   │   │       ├── Path_Ray3
│   │   │       ├── Path_Ray4
│   │   │       ├── Path_Ray5
│   │   │       ├── Path_Ray6
│   │   │       ├── Path_Ray7
│   │   │       └── Path_Ray8
│   │   └── IconCell_24 [~112×112px]
│   │       └── Icon_Globe [24×24dp]
│   │           ├── Circle_GlobeOuter
│   │           ├── Path_LongitudeLine1
│   │           ├── Path_LongitudeLine2
│   │           ├── Path_LatitudeLine1 [赤道]
│   │           └── Path_LatitudeLine2
│   │
│   ├── Row5_CommerceGroup
│   │   ├── IconCell_25 [~112×112px]
│   │   │   └── Icon_Gift [24×24dp]
│   │   │       ├── Path_GiftBox
│   │   │       ├── Path_GiftLid
│   │   │       ├── Path_RibbonVertical
│   │   │       ├── Path_BowLeft
│   │   │       └── Path_BowRight
│   │   ├── IconCell_26 [~112×112px]
│   │   │   └── Icon_Coupon [24×24dp]
│   │   │       ├── Path_CouponBody [横向矩形]
│   │   │       ├── Path_NotchLeft [左半圆缺口]
│   │   │       ├── Path_NotchRight [右半圆缺口]
│   │   │       └── Path_DashedLine [中间虚线]
│   │   ├── IconCell_27 [~112×112px]
│   │   │   └── Icon_Star [24×24dp]
│   │   │       └── Path_StarOutline [五角星路径]
│   │   ├── IconCell_28 [~112×112px]
│   │   │   └── Icon_Sparkle [24×24dp]
│   │   │       └── Path_FourPointStar [四角星路径]
│   │   ├── IconCell_29 [~112×112px]
│   │   │   └── Icon_Crown [24×24dp]
│   │   │       ├── Path_CrownOutline
│   │   │       └── Path_CrownBase [底部横带]
│   │   └── IconCell_30 [~112×112px]
│   │       └── Icon_Heart [24×24dp]
│   │           └── Path_HeartOutline
│   │
│   └── Row6_ToolsGroup
│       ├── IconCell_31 [~112×112px]
│       │   └── Icon_ArrowLeft [24×24dp]
│       │       ├── Path_ArrowStem
│       │       └── Path_ArrowHead
│       ├── IconCell_32 [~112×112px]
│       │   └── Icon_ArrowRight [24×24dp]
│       │       ├── Path_ArrowStem
│       │       └── Path_ArrowHead
│       ├── IconCell_33 [~112×112px]
│       │   └── Icon_Close [24×24dp]
│       │       ├── Path_DiagonalLine1
│       │       └── Path_DiagonalLine2
│       ├── IconCell_34 [~112×112px]
│       │   └── Icon_Check [24×24dp]
│       │       └── Path_CheckMark
│       ├── IconCell_35 [~112×112px]
│       │   └── Icon_More [24×24dp]
│       │       ├── Circle_Dot1
│       │       ├── Circle_Dot2
│       │       └── Circle_Dot3
│       └── IconCell_36 [~112×112px]
│           └── Icon_Trash [24×24dp]
│               ├── Path_TrashBody
│               ├── Path_TrashLid
│               ├── Path_TrashHandle [盖上提手]
│               ├── Path_TrashLine1 [桶内竖线]
│               ├── Path_TrashLine2
│               └── Path_TrashLine3
```

---

## 应用层组件树（图标在 App 中使用）

```
App
├── BottomNavigationBar
│   ├── NavItem [首页]
│   │   ├── IconButton [44×44dp 触控区]
│   │   │   └── Icon_Home [24×24dp]
│   │   └── Label_Text ["首页", PingFang SC 10px]
│   ├── NavItem [聊天]
│   │   ├── IconButton [44×44dp]
│   │   │   └── Icon_Chat [24×24dp]
│   │   └── Label_Text ["聊天"]
│   ├── NavItem [AI伴侣]
│   │   ├── IconButton [44×44dp]
│   │   │   └── Icon_AICompanion [24×24dp]
│   │   └── Label_Text ["yuoyuo"]
│   └── NavItem [我的]
│       ├── IconButton [44×44dp]
│       │   └── Icon_Profile [24×24dp]
│       └── Label_Text ["我的"]
│
├── ChatInputBar
│   ├── IconButton_Microphone [44×44dp]
│   │   └── Icon_Microphone / Icon_MicrophoneOff [切换]
│   ├── TextField [输入区域]
│   ├── IconButton_Emoji [44×44dp]
│   │   └── Icon_Emoji
│   ├── IconButton_Add [44×44dp]
│   │   └── Icon_Add
│   └── IconButton_Send [44×44dp, Primary色]
│       └── Icon_Send
│
└── AudioPlaybackBar
    ├── IconButton_Play [44×44dp]
    │   └── Icon_Play / Icon_Pause [切换]
    ├── WaveformVisualizer
    │   └── Icon_Waveform [动态]
    ├── IconButton_VolumeUp [44×44dp]
    │   └── Icon_VolumeUp / Icon_Mute [切换]
    └── IconButton_Headphone [44×44dp]
        └── Icon_Headphone
```

---

## 组件层级深度说明

| 层级 | 类型 | 示例 |
|------|------|------|
| L0 | 页面/画布 | IconSetCanvas |
| L1 | 区域容器 | Row1_NavigationGroup |
| L2 | 单元格容器 | IconCell_01 |
| L3 | 原子图标 | Icon_Home |
| L4 | SVG 路径 | Path_RoofTriangle |

最大深度：4层（Path 路径级）
平均深度：3层（Icon 原子级）
