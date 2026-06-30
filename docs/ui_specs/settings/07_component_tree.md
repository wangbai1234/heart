# 07 Component Tree — 设置页 Settings

完整 ASCII 组件树，从 Page 根节点开始，覆盖每个可见元素（包括装饰性背景、分隔线等）。

```
Page（设置页 Settings）
├── BackgroundLayer（z=0，全屏固定，不随 ScrollView 滚动）
│   ├── LinearGradient（180°，浅粉 → 薰衣草白粉 → 紫粉，全屏）
│   └── RadialGlow（左下角光晕，blur ~40pt，薰衣草紫渐变透明）
│
├── StatusBar（z=20，系统层，44pt 高）
│   ├── TimeLabel（"9:41"，左侧）
│   └── SystemIconGroup（右侧）
│       ├── SignalIcon（信号强度 4 格）
│       ├── WiFiIcon（WiFi 信号）
│       └── BatteryIcon（电量满格）
│
├── NavigationBar（z=10，固定顶部，StatusBar 下方，44pt 高）
│   ├── BackButton（左侧，"<" 箭头，约 24×24pt）
│   └── TitleLabel（居中，"设置"，PingFang SC Medium 18pt）
│
└── ScrollView（可垂直滚动，StatusBar+NavBar 下方至底部）
    │
    ├── ProfileCard（圆角卡片，约 358×96pt，radius 20pt）
    │   ├── CardBackground（rgba(255,255,255,0.90)，blur，shadow）
    │   ├── AvatarView（圆形，直径 60pt）
    │   │   ├── AvatarImage（晨曦角色，circle clip）
    │   │   └── AvatarBorder（2pt 白色圆形边框）
    │   ├── UserInfoColumn（垂直排列）
    │   │   ├── UserNameLabel（"晨曦"，PingFang SC Semibold 17pt）
    │   │   └── MemberBadge（"会员 · 至 2026-12-31"）
    │   │       ├── BadgeBackground（rgba(255,183,197,0.20)，radius 11pt）
    │   │       └── BadgeLabel（"会员 · 至 2026-12-31"，12pt，#FF85A1）
    │   └── ChevronRight（">", 20×20pt，#C0C0CC）
    │
    ├── SectionLabel_Member（"我的会员"，12pt，#8A8A9A）
    │
    ├── GroupCard_Member（会员组卡片，约 358×108pt，radius 20pt）
    │   ├── CardBackground（rgba(255,255,255,0.88)，shadow）
    │   ├── SettingRow_MemberRedeem（会员兑换，Expandable）
    │   │   ├── IconView（礼盒图标，22×22pt，粉色）
    │   │   ├── LabelText（"会员兑换"，15pt，#3A3A4A）
    │   │   └── ChevronDown（"∨"，12×8pt，#C0C0CC）
    │   ├── Divider_H1（水平分隔线，0.5pt，左 inset 52pt）
    │   └── SettingRow_Subscription（订阅状态，Chevron）
    │       ├── IconView（皇冠图标，22×22pt，粉色）
    │       ├── LabelText（"订阅状态"，15pt，#3A3A4A）
    │       ├── ValueLabel（"至 2026-12-31"，13pt，#8A8A9A）
    │       └── ChevronRight（">", 8×14pt，#C0C0CC）
    │
    ├── SectionLabel_Appearance（"外观"，12pt，#8A8A9A）
    │
    ├── GroupCard_Appearance（外观组卡片，约 358×108pt，radius 20pt）
    │   ├── CardBackground（rgba(255,255,255,0.88)，shadow）
    │   ├── SettingRow_Theme（主题，SegmentPicker）
    │   │   ├── IconView（调色板图标，22×22pt，粉色）
    │   │   ├── LabelText（"主题"，15pt，#3A3A4A）
    │   │   └── SegmentPicker（约 180×34pt）
    │   │       ├── PickerContainer（rgba(240,235,245,0.8)，radius 10pt）
    │   │       ├── SegmentItem_Light（"浅色"，选中）
    │   │       │   ├── SelectedBackground（#FFFFFF，radius 8pt，shadow）
    │   │       │   └── SegmentLabel（"浅色"，13pt Medium，#3A3A4A）
    │   │       ├── SegmentItem_Dark（"深色"，未选中）
    │   │       │   └── SegmentLabel（"深色"，13pt，#8A8A9A）
    │   │       └── SegmentItem_Auto（"自动"，未选中）
    │   │           └── SegmentLabel（"自动"，13pt，#8A8A9A）
    │   ├── Divider_H2（水平分隔线，0.5pt，左 inset 52pt）
    │   └── SettingRow_FontSize（字体大小，Slider）
    │       ├── IconView（字母A图标，22×22pt，粉色）
    │       ├── LabelText（"字体大小"，15pt，#3A3A4A）
    │       └── SliderArea（约 220pt 宽）
    │           ├── SmallALabel（"A"，11pt，#8A8A9A）
    │           ├── SliderControl（约 180pt 宽）
    │           │   ├── TrackBackground（灰色，4pt 高）
    │           │   ├── TrackFilled（粉色，约 60% 宽）
    │           │   └── Thumb（圆形，22pt 直径，#FFB7C5）
    │           └── LargeALabel（"A"，17pt，#8A8A9A）
    │
    ├── SectionLabel_Notification（"通知"，12pt，#8A8A9A）
    │
    ├── GroupCard_Notification（通知组卡片，约 358×108pt，radius 20pt）
    │   ├── CardBackground（rgba(255,255,255,0.88)，shadow）
    │   ├── SettingRow_ActiveReminder（积极提醒，Toggle）
    │   │   ├── IconView（铃铛图标，22×22pt，粉色）
    │   │   ├── LabelText（"积极提醒"，15pt，#3A3A4A）
    │   │   └── Toggle_ON（51×31pt）
    │   │       ├── Track（渐变 #FFB7C5→#FF85A1，radius full）
    │   │       └── Thumb（白色圆形，27pt，阴影，位于右侧）
    │   ├── Divider_H3（水平分隔线，0.5pt，左 inset 52pt）
    │   └── SettingRow_Mute（静音，Chevron）
    │       ├── IconView（月亮图标，22×22pt，粉色）
    │       ├── LabelText（"静音"，15pt，#3A3A4A）
    │       ├── ValueLabel（"22:00 - 8:00"，13pt，#8A8A9A）
    │       └── ChevronRight（">", 8×14pt，#C0C0CC）
    │
    ├── SectionLabel_Privacy（"隐私与数据"，12pt，#8A8A9A）
    │
    ├── GroupCard_Privacy（隐私与数据组，约 358×162pt，radius 20pt）
    │   ├── CardBackground（rgba(255,255,255,0.88)，shadow）
    │   ├── SettingRow_ClearServer（清除网格服务器，Chevron）
    │   │   ├── IconView（垃圾桶图标，22×22pt，粉色）
    │   │   ├── LabelText（"清除网格服务器"，15pt，#3A3A4A）
    │   │   └── ChevronRight（">", 8×14pt，#C0C0CC）
    │   ├── Divider_H4（水平分隔线）
    │   ├── SettingRow_ExportData（导出我的数据，Chevron）
    │   │   ├── IconView（下载/导出图标，22×22pt，粉色）
    │   │   ├── LabelText（"导出我的数据"，15pt，#3A3A4A）
    │   │   └── ChevronRight（">", 8×14pt，#C0C0CC）
    │   ├── Divider_H5（水平分隔线）
    │   └── SettingRow_DeleteAccount（注销账号，Chevron，危险色）
    │       ├── IconView（账号注销图标，22×22pt，#FF85A1）
    │       ├── LabelText（"注销账号"，15pt，#FF85A1）
    │       └── ChevronRight（">", 8×14pt，#C0C0CC）
    │
    ├── SectionLabel_About（"关于"，12pt，#8A8A9A）
    │
    └── GroupCard_About（关于组，约 358×162pt，radius 20pt）
        ├── CardBackground（rgba(255,255,255,0.88)，shadow）
        ├── SettingRow_Version（版本 1.0.0，Chevron）
        │   ├── IconView（信息圆圈图标，22×22pt，粉色）
        │   ├── LabelText（"版本 1.0.0"，15pt，#3A3A4A）
        │   └── ChevronRight（">", 8×14pt，#C0C0CC）
        ├── Divider_H6（水平分隔线）
        ├── SettingRow_Agreement（用户协议 / 隐私政策，Chevron）
        │   ├── IconView（文档图标，22×22pt，粉色）
        │   ├── LabelText（"用户协议 / 隐私政策"，15pt，#3A3A4A）
        │   └── ChevronRight（">", 8×14pt，#C0C0CC）
        ├── Divider_H7（水平分隔线）
        └── SettingRow_ContactUs（联系我们，Chevron）
            ├── IconView（耳机图标，22×22pt，粉色）
            ├── LabelText（"联系我们"，15pt，#3A3A4A）
            └── ChevronRight（">", 8×14pt，#C0C0CC）
```

---

## 树形说明

- 括号内为：组件描述、尺寸、颜色或关键属性（估算值）
- `Divider_Hx`：水平分隔线，出现在相邻两行之间
- `CardBackground`：每个 GroupCard 和 ProfileCard 的背景层（rgba + blur + shadow）
- 所有 `IconView` 为粉色系线条图标
- `SettingRow_DeleteAccount` 是本页唯一使用警示粉色（#FF85A1）的行
- `Toggle_ON` 表示积极提醒当前为开启状态（PNG 所示）
- `SegmentItem_Light` 当前为选中状态（PNG 所示：浅色主题）
