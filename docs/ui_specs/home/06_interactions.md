# 06 Interactions — 首页 Home

---

## 进入动画（Page Enter）

| 元素 | 动画 | Duration | Easing | Delay |
|------|------|----------|--------|-------|
| 页面背景 | 渐现 fade-in（opacity 0→1） | 200 ms | ease-out | 0 ms |
| AppBar（yuoyuo + 头像） | 从上方 translateY(-8pt)→0 + fade-in | 300 ms | decelerate | 50 ms |
| HeroCard | 从下方 translateY(12pt)→0 + fade-in，scale(0.97)→1 | 400 ms | spring | 80 ms |
| HeroCard 内宝珠 | scale(0.8)→1 + fade-in | 400 ms | spring | 150 ms |
| QuickActionTiles | 从下方 translateY(8pt)→0 + fade-in，stagger 50 ms 每格 | 300 ms | decelerate | 200 ms |
| SectionHeader | fade-in | 250 ms | ease-out | 280 ms |
| ConversationListItem 1 | 从下方 translateY(8pt)→0 + fade-in | 300 ms | decelerate | 300 ms |
| ConversationListItem 2 | 从下方 translateY(8pt)→0 + fade-in | 300 ms | decelerate | 360 ms |
| BottomTabBar | 从下方 translateY(20pt)→0 + fade-in | 350 ms | decelerate | 0 ms |

> ⚠️ 设计稿未定义具体动画参数，以上为推荐值，建议参考 Motion Storyboard 确认。

---

## 退出动画（Page Exit）

| 场景 | 动画 |
|------|------|
| 进入对话页（点击"开始聊天"） | 页面内容整体向上滑出，聊天页从下方滑入（iOS Push 风格） |
| 点击 Tab 切换 | Cross-fade（淡入淡出），duration 200 ms |
| 点击快速操作瓷砖 | 同进入对话页，Push 风格 |

> ⚠️ 设计稿未定义退出动画，建议参考 Motion Storyboard。

---

## 持续动效（Idle State）

### 宝珠脉冲发光（Heart Orb Pulse）
| 属性 | 值 |
|------|---|
| 效果 | 外发光半径周期性扩大缩小（glow pulse） |
| 循环 | 无限循环 |
| Duration | 2000 ms 一个完整周期 |
| 幅度 | 发光半径从 30 pt → 50 pt → 30 pt |
| Easing | ease-in-out |
| 透明度变化 | glow opacity 0.5 → 0.8 → 0.5 |

> ⚠️ 设计稿为静态图，以上脉冲动效为推测建议，建议参考 Motion Storyboard 确认。

### 宝珠浮动（Floating）
| 属性 | 值 |
|------|---|
| 效果 | Y 轴轻微上下浮动 translateY(0→-6pt→0) |
| 循环 | 无限循环 |
| Duration | 3000 ms |
| Easing | ease-in-out |

> ⚠️ 设计稿未定义，建议参考 Motion Storyboard。

---

## Hover 状态
> 本 App 为移动端，无 Web 鼠标 Hover 场景。若实现 Web 版，参考 Pressed 状态。

---

## Pressed 状态

| 组件 | 效果 | Duration |
|------|------|----------|
| StartChatButton（开始聊天） | background-color 加深约 8%，scale(0.97) | 150 ms，ease-out |
| QuickActionTile（每格） | background-color 加深约 5%，scale(0.96) | 150 ms |
| ConversationListItem | 背景变为 rgba(255,183,197,0.12)，无缩放 | 150 ms |
| BottomTabItem | scale(0.88)，弹性回弹 | 150 ms，spring |
| UserAvatar（右上角） | opacity 0.75，scale(0.95) | 150 ms |
| ViewAll Link（查看全部） | opacity 0.6 | 100 ms |

---

## Selected 状态

| 组件 | 效果 |
|------|------|
| BottomTabItem（首页 Active） | 图标+文字颜色 #FFB7C5，图标下方显示小圆点指示器（直径 4 pt） |
| ConversationListItem | 无持久 Selected 状态（点击直接跳转） |

---

## Disabled 状态
> 本设计稿中所有元素均为可用状态，无 Disabled 展示。

> ⚠️ 如需 Disabled 状态（如未登录时），建议：opacity 0.4，pointer-events: none，cursor: not-allowed。参考 Motion Storyboard。

---

## Loading 状态

| 场景 | 建议效果 |
|------|---------|
| 首页数据加载中 | 显示 Skeleton 骨架屏（见下方 Skeleton 说明） |
| 头像图片加载中 | 圆形占位符，颜色 #FFF0F3，shimmer 动效 |
| 对话列表加载中 | 列表行 Skeleton（见下方） |

> ⚠️ 设计稿未定义 Loading 状态，建议参考 Motion Storyboard。

---

## Skeleton 骨架屏

| 区域 | Skeleton 形态 |
|------|-------------|
| HeroCard | 圆角矩形占位块（358×280 pt），颜色 #F0E6E9，shimmer 动效 |
| 宝珠 | 心形占位块或圆形（约 120×120 pt），颜色同上 |
| 角色名 | 约 100×20 pt 矩形占位，居中 |
| 状态文字 | 约 160×14 pt 矩形占位，居中 |
| QuickActionTiles | 三格占位矩形，111×90 pt |
| ConversationListItem | 圆形头像占位 + 两行矩形文字占位 |

> ⚠️ 设计稿未定义 Skeleton，建议参考 Motion Storyboard。

---

## Error 状态

| 场景 | 建议效果 |
|------|---------|
| 网络错误（列表加载失败） | 空状态提示 + 重试按钮，居中显示 |
| 头像加载失败 | 显示默认头像占位图（角色轮廓剪影） |
| 宝珠数据加载失败 | 宝珠显示为灰色版本，状态文字显示"---" |

> ⚠️ 设计稿未定义 Error 状态，建议参考 Motion Storyboard。

---

## Empty 状态

| 场景 | 建议效果 |
|------|---------|
| 最近对话列表为空 | 显示提示文字"还没有对话，快去和伴侣聊天吧~"，配插图 |
| 无绑定角色 | HeroCard 显示默认空状态 + "选择角色"CTA |

> ⚠️ 设计稿未定义 Empty 状态，建议参考 Motion Storyboard。

---

## Scroll 行为

| 属性 | 值 |
|------|---|
| 方向 | 垂直向上滚动 |
| 弹性 | iOS 原生弹性滚动（rubber band） |
| Header 行为 | 固定不滚动，始终可见 |
| Tab Bar 行为 | 固定不随滚动，始终可见 |
| HeroCard 行为 | 随页面滚动向上消失（非 sticky） |
| 滚动时 Header | 可选：下滑时 HeroCard 逐渐缩小/淡出，⚠️ 设计稿未定义 |

---

## 页面转场（Navigation Transitions）

| 来源 → 目标 | 转场方式 |
|------------|---------|
| 首页 → 聊天页（点击"开始聊天"） | iOS Push（右滑进入），200 ms |
| 首页 → 对话历史列表（点击"查看全部"） | iOS Push，200 ms |
| 首页 → 对话页（点击列表行） | iOS Push，200 ms |
| 首页 → 兑换会员页 | iOS Push，200 ms |
| 首页 → 角色切换页 | iOS Push，200 ms |
| 首页 → 系统设置页 | iOS Push，200 ms |
| 首页 → 个人中心（头像） | iOS Push，200 ms |
| Tab 切换 | Cross-fade（不使用 Push），200 ms |

> ⚠️ 转场动画方向约定（Push/Modal）设计稿未明确定义，建议参考 Motion Storyboard。

---

## Card Selection（HeroCard）

| 状态 | 说明 |
|------|------|
| 非交互 | HeroCard 本身不可点击（整体），仅内部"开始聊天"按钮响应 |
| 按钮 Pressed | 见 Pressed 状态表 |

---

## Bottom Bar Tab Selection

| 操作 | 效果 |
|------|------|
| 点击非当前 Tab | 图标+文字切换颜色（#ADADB8→#FFB7C5），指示点出现，Cross-fade 转场 |
| 点击当前 Tab（首页） | 页面滚动回顶部（ScrollTo 0，300 ms，easing: decelerate） |
