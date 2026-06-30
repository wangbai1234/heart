# 07 组件树 — Typography Specimen（字样规范）

## 完整组件树（ASCII 树形结构）

```
TypographySpecBoard（字体规范看板）
│
├── BoardHeader（看板标题行）
│   └── Text: "yuoyuo · 字体比例"
│       ├── Span: "yuoyuo"  [SF Pro Rounded SemiBold, ~24px, #3A3A4A]
│       └── Span: " · 字体比例"  [PingFang SC SemiBold, ~24px, #3A3A4A]
│
├── MainContent（主内容区，Flex Row）
│   │
│   ├── LeftPanel（字级阶梯区，Flex Column, ~560px wide）
│   │   │
│   │   ├── TypeScaleRow.Display（Display 行）
│   │   │   ├── LabelColumn（级别标签列）
│   │   │   │   ├── Text: "Display"  [#FFB7C5, ~13px]
│   │   │   │   └── Text: "40 / 48"  [#FFB7C5, ~13px]
│   │   │   ├── DotDivider（粉色圆点 ●）  [#FFB7C5, ~8px diameter]
│   │   │   └── ExampleColumn（示例列）
│   │   │       ├── ExampleText: "你好，yuoyuo"
│   │   │       │   ├── Span(中文): "你好，"  [PingFang SC SemiBold, 40px/48px, #3A3A4A]
│   │   │       │   └── Span(拉丁): "yuoyuo"  [SF Pro Rounded SemiBold, 40px/48px, #3A3A4A]
│   │   │       └── AnnotationText: "PingFang SC SemiBold + SF Pro Rounded"
│   │   │           [PingFang SC Regular, ~12px, #8A8A98]
│   │   │
│   │   ├── TypeScaleRow.Title（Title 行）
│   │   │   ├── LabelColumn
│   │   │   │   ├── Text: "Title"  [#FFB7C5, ~13px]
│   │   │   │   └── Text: "28 / 36"  [#FFB7C5, ~13px]
│   │   │   ├── DotDivider  [#FFB7C5]
│   │   │   └── ExampleColumn
│   │   │       ├── ExampleText: "《今天聊点什么》"  [PingFang SC Medium, 28px/36px, #3A3A4A]
│   │   │       └── AnnotationText: "PingFang SC Medium"  [~12px, #8A8A98]
│   │   │
│   │   ├── TypeScaleRow.Headline（Headline 行）
│   │   │   ├── LabelColumn
│   │   │   │   ├── Text: "Headline"  [#FFB7C5, ~13px]
│   │   │   │   └── Text: "22 / 30"  [#FFB7C5, ~13px]
│   │   │   ├── DotDivider  [#FFB7C5]
│   │   │   └── ExampleColumn
│   │   │       ├── ExampleText: "《晚安，做好梦》"  [PingFang SC Medium, 22px/30px, #3A3A4A]
│   │   │       └── AnnotationText: "PingFang SC Medium"  [~12px, #8A8A98]
│   │   │
│   │   ├── TypeScaleRow.Body（Body 行）
│   │   │   ├── LabelColumn
│   │   │   │   ├── Text: "Body"  [#FFB7C5, ~13px]
│   │   │   │   └── Text: "16 / 24"  [#FFB7C5, ~13px]
│   │   │   ├── DotDivider  [#FFB7C5]
│   │   │   └── ExampleColumn
│   │   │       ├── ExampleText: "我在这里陪你。"  [PingFang SC Regular, 16px/24px, #3A3A4A]
│   │   │       └── AnnotationText: "PingFang SC Regular"  [~12px, #8A8A98]
│   │   │
│   │   ├── TypeScaleRow.Caption（Caption 行）
│   │   │   ├── LabelColumn
│   │   │   │   ├── Text: "Caption"  [#FFB7C5, ~13px]
│   │   │   │   └── Text: "13 / 18"  [#FFB7C5, ~13px]
│   │   │   ├── DotDivider  [#FFB7C5]
│   │   │   └── ExampleColumn
│   │   │       ├── ExampleText: "刚刚 · 已读"  [PingFang SC Regular, 13px/18px, #8A8A98]
│   │   │       └── AnnotationText: "PingFang SC Regular / #8A8A98"  [~12px, #8A8A98]
│   │   │
│   │   └── TypeScaleRow.Tabular（Tabular 行）
│   │       ├── LabelColumn
│   │       │   ├── Text: "Tabular"  [#FFB7C5, ~13px]
│   │       │   └── Text: "14"  [#FFB7C5, ~13px]
│   │       ├── DotDivider  [#FFB7C5]
│   │       └── ExampleColumn
│   │           ├── ExampleText: "12:34 · 32m"  [SF Pro Rounded Tabular, 14px, #3A3A4A]
│   │           └── AnnotationText: "SF Pro Rounded (Tabular)"  [~12px, #8A8A98]
│   │
│   └── RightPanel（应用示例区，Flex Column, ~800px wide）
│       │
│       ├── ChatPreviewCard.Light（浅色模式示例卡片）
│       │   ├── CardBackground  [~white / #FFF8F3, radius ~16px, shadow]
│       │   ├── CardStatusBar（卡片顶部状态行）
│       │   │   ├── LeftGroup
│       │   │   │   ├── OnlineDot  [~#4CAF50, ~8px diameter]
│       │   │   │   └── Text: "浅色模式示例"  [Caption, 13px/18px, #3A3A4A]
│       │   │   └── RightGroup
│       │   │       └── Text: "12:34"  [Tabular, 14px, #8A8A98]
│       │   │
│       │   ├── ChatMessageList（消息列表区）
│       │   │   │
│       │   │   ├── AIChatMessage（AI 消息行，Flex Row，左对齐）
│       │   │   │   ├── Avatar.AI.Light
│       │   │   │   │   └── Image: AI角色头像  [圆形, ~44px, 动漫粉色少女]
│       │   │   │   └── ChatBubble.AI.Light
│       │   │   │       ├── BubbleBackground  [白色/浅粉, radius ~12px]
│       │   │   │       ├── BubbleText: "今天天气很好呢，要一起去散步吗？🌸"
│       │   │   │       │   ├── TextContent  [Body, 16px/24px, PingFang SC Regular, #3A3A4A]
│       │   │   │       │   └── Emoji: "🌸"  [~16px]
│       │   │   │       └── Timestamp: "12:34"  [Tabular, 14px, #8A8A98]
│       │   │   │
│       │   │   └── UserChatMessage（用户消息行，Flex Row，右对齐）
│       │   │       ├── ChatBubble.User.Light
│       │   │       │   ├── BubbleBackground  [#A7C7E7, radius ~12px]
│       │   │       │   ├── BubbleText: "好呀好呀！一起去吧～☁"
│       │   │       │   │   ├── TextContent  [Body, 16px/24px, PingFang SC Regular, #3A3A4A]
│       │   │       │   │   └── Emoji: "☁"  [~16px]
│       │   │       │   └── Timestamp: "12:36"  [Tabular, 14px, #8A8A98]
│       │   │       ├── ReadTick: "✓"  [~蓝色]
│       │   │       └── Avatar.User.Light
│       │   │           └── Image: 用户头像  [圆形, ~44px, 动漫粉发少女]
│       │   │
│       │   └── ReadStatusBar（卡片底部已读状态行）
│       │       └── Text: "刚刚 · 已读"  [Caption, 13px/18px, #8A8A98]
│       │
│       └── ChatPreviewCard.Dark（深色模式预览卡片）
│           ├── CardBackground  [深炭灰 ~#2A2A38, radius ~16px]
│           ├── CardStatusBar
│           │   ├── LeftGroup
│           │   │   ├── OnlineDot  [~#4CAF50]
│           │   │   └── Text: "深色模式预览"  [Caption, 13px/18px, 浅灰]
│           │   └── RightGroup
│           │       └── Text: "12:34"  [Tabular, 14px, 浅灰]
│           │
│           ├── ChatMessageList
│           │   ├── AIChatMessage
│           │   │   ├── Avatar.AI.Dark
│           │   │   │   └── Image: AI角色头像（深色版）  [圆形, ~44px]
│           │   │   └── ChatBubble.AI.Dark
│           │   │       ├── BubbleBackground  [深蓝灰 ~#3A3A50]
│           │   │       ├── BubbleText: "今天天气很好呢，要一起去散步吗？🌸"
│           │   │       │   └── TextContent  [Body, 16px/24px, 浅白 ~#F0F0F8]
│           │   │       └── Timestamp: "12:34"  [Tabular, 14px, 灰 ~#9090A0]
│           │   │
│           │   └── UserChatMessage
│           │       ├── ChatBubble.User.Dark
│           │       │   ├── BubbleBackground  [深蓝灰 ~#4A4A62]
│           │       │   ├── BubbleText: "好呀好呀！一起去吧～☁"
│           │       │   │   └── TextContent  [Body, 16px/24px, 浅白 ~#F0F0F8]
│           │       │   └── Timestamp: "12:36"  [Tabular, 14px, 灰]
│           │       ├── ReadTick: "✓"  [蓝色]
│           │       └── Avatar.User.Dark
│           │           └── Image: 用户头像（深色版）  [圆形, ~44px]
│           │
│           └── ReadStatusBar
│               └── Text: "刚刚 · 已读"  [Caption, 13px/18px, 灰 ~#9090A0]
│
└── BoardFooter（看板底部字体说明区）
    ├── DividerLine  [水平分隔线, ~1px, 浅灰]
    ├── LeftGroup（字体注释区，Flex Row）
    │   ├── FontIconBadge（Aa 圆形图标）
    │   │   ├── BadgeBackground  [圆形, #FFB7C5, ~36px diameter]
    │   │   └── BadgeText: "Aa"  [SF Pro Rounded, 白色]
    │   └── FontDescriptionList（三行文字，Flex Column）
    │       ├── Text: "中文字体：PingFang SC / HarmonyOS Sans SC（圆润、几何、柔和）"
    │       │   [~13px, #6B6B7E]
    │       ├── Text: "拉丁字体：SF Pro Rounded（圆润、友好、可读性高）"
    │       │   [~13px, #6B6B7E]
    │       └── Text: "数字字体：SF Pro Rounded Tabular（等宽数字，便于阅读时间与数据）"
    │           [~13px, #6B6B7E]
    └── RightGroup（品牌字区）
        └── BrandWordmark: "yuoyuo"  [SF Pro Rounded SemiBold, ~24px, #FFB7C5]
```

---

## 组件层级关系（逻辑层级）

```
Layer 0 (背景)：  Canvas Background (#FFF8F3)
Layer 1 (内容)：  LeftPanel, RightPanel, BoardHeader, BoardFooter
Layer 2 (卡片)：  ChatPreviewCard.Light, ChatPreviewCard.Dark
Layer 3 (消息)：  AIChatMessage, UserChatMessage
Layer 4 (气泡)：  ChatBubble.*, Avatar.*
Layer 5 (文字)：  所有 Text / Span 节点
```

---

## 树形结构说明

| 符号 | 含义 |
|------|------|
| `├──` | 同级子节点，后有兄弟节点 |
| `└──` | 同级子节点，最后一个 |
| `│` | 继续当前父节点的子列表 |
| `[...]` | 括号内为样式属性说明 |
| `（估算值）` | 无法精确测量的尺寸 |
