# 07 Component Tree — Redeem 兑换页

```
Page (Redeem 兑换页)
├── Background
│   ├── SkyGradientLayer                    # 全屏粉紫→樱花粉→浅粉渐变背景
│   └── CloudsOverlayLayer                  # 天空云彩装饰（PNG，叠加在渐变上）
│
├── SafeArea
│   ├── StatusBar                           # 系统状态栏（时间 + 信号图标）
│   │   ├── TimeLabel ("9:41")
│   │   └── SystemIcons
│   │       ├── CellularIcon
│   │       ├── WiFiIcon
│   │       └── BatteryIcon
│   │
│   ├── NavigationBar                       # 导航栏（固定顶部）
│   │   ├── BackButton ("<")                # 返回按钮，触摸区 88×88px
│   │   └── TitleLabel ("兑换会员")          # 页面标题，水平居中
│   │
│   └── ScrollView                          # 主内容滚动区域
│       ├── InputCard                       # 主输入卡片（白色圆角卡片）
│       │   ├── GiftIllustration            # 礼品盒插画（PNG / Lottie）
│       │   │   ├── GiftBoxImage            # 礼品盒主体（白色/浅粉，带光泽）
│       │   │   ├── RibbonDecoration        # 薰衣草紫丝带（交叉 + 蝴蝶结）
│       │   │   └── FloatingParticles       # 散落心形/花瓣装饰碎片
│       │   │
│       │   ├── CardTitle                   # 主标题「输入兑换码激活会员」
│       │   ├── CardSubtitle                # 副标题说明文字
│       │   │
│       │   ├── RedeemCodeInput             # 4-4-4 分组输入框组
│       │   │   ├── SegmentGroup_1          # 第一段（4 个字符格）
│       │   │   │   ├── CharBox_1_1
│       │   │   │   ├── CharBox_1_2
│       │   │   │   ├── CharBox_1_3
│       │   │   │   └── CharBox_1_4
│       │   │   ├── SeparatorDash_1         # 分隔符「-」
│       │   │   ├── SegmentGroup_2          # 第二段（4 个字符格）
│       │   │   │   ├── CharBox_2_1
│       │   │   │   ├── CharBox_2_2
│       │   │   │   ├── CharBox_2_3
│       │   │   │   └── CharBox_2_4
│       │   │   ├── SeparatorDash_2         # 分隔符「-」
│       │   │   └── SegmentGroup_3          # 第三段（4 个字符格）
│       │   │       ├── CharBox_3_1
│       │   │       ├── CharBox_3_2
│       │   │       ├── CharBox_3_3
│       │   │       └── CharBox_3_4
│       │   │
│       │   └── PasteButton                 # 粘贴兑换码按钮（毛玻璃）
│       │       ├── ClipboardIcon           # 剪贴板图标（SF Symbol）
│       │       └── PasteLabel ("粘贴兑换码")
│       │
│       ├── ActivateButton                  # 立即激活主 CTA 按钮（pill，渐变）
│       │   └── ActivateLabel ("立即激活")
│       │
│       ├── FAQAccordion                    # 如何获取兑换码折叠卡片
│       │   ├── AccordionHeader             # 折叠标题行（可点击）
│       │   │   ├── QuestionIcon            # 问号圆形图标
│       │   │   ├── FAQTitle ("如何获取兑换码")
│       │   │   └── ChevronIcon             # 展开/折叠箭头（旋转动效）
│       │   │
│       │   └── AccordionContent            # 展开内容区（当前为展开态）
│       │       ├── StepList                # 步骤列表
│       │       │   ├── StepItem_1
│       │       │   │   ├── StepBadge ("1")
│       │       │   │   └── StepText ("前往「爱发电」赞助页面")
│       │       │   ├── StepItem_2
│       │       │   │   ├── StepBadge ("2")
│       │       │   │   └── StepText ("选择心仪的赞助挡位")
│       │       │   ├── StepItem_3
│       │       │   │   ├── StepBadge ("3")
│       │       │   │   └── StepText ("完成支付后查收兑换码邮件")
│       │       │   └── StepItem_4
│       │       │       ├── StepBadge ("4")
│       │       │       └── StepText ("返回yuoyuo输入兑换码")
│       │       │
│       │       └── ExternalLink            # 「去爱发电 →」品牌色链接
│       │
│       └── DisclaimerText                  # 免责声明「兑换码一次性有效…」
│
└── BottomSafeArea                          # 底部安全区域
    └── HomeIndicator                       # iPhone Home 手势指示条
```

---

## 层叠顺序（Z-index，从低到高）

| 层级 | 组件 | 说明 |
|------|------|------|
| 0 | Background（SkyGradientLayer + CloudsOverlayLayer） | 最底层装饰 |
| 1 | ScrollView 及其子元素 | 主内容区 |
| 2 | NavigationBar | 固定顶部，覆盖滚动内容 |
| 3 | StatusBar | 系统级，始终在顶 |
| 10 | Toast（错误/成功提示） | 覆盖全页内容，临时显示 |
| 20 | 系统键盘 | 系统级，最高层 |

---

## 组件关系备注

- `InputCard` 是页面核心容器，包含所有直接操作组件
- `RedeemCodeInput` 内的 12 个 `CharBox` 在逻辑上是一个联动的 Input Group，焦点在格间自动流转
- `FAQAccordion` 的 `AccordionContent` 在折叠态时 height=0，overflow=hidden；展开态时高度动画至内容自然高度
- `PasteButton` 与 `RedeemCodeInput` 存在数据联动关系（粘贴内容填入输入框）
- `ActivateButton` 的启用/禁用状态由 `RedeemCodeInput` 的填写完整度驱动（全 12 位填满 → 启用）
