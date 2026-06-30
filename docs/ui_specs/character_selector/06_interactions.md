# 06 Interactions — 角色页 Character Selector

---

## 页面进入动画

### 进入方式：Modal Slide-Up（底部向上滑入）
- 触发：从 onboarding 上一步完成后自动触发，或"更换伴侣"入口手动触发
- 动画类型：Sheet presentation（iOS native bottom sheet 风格）
- 持续时间：400 ms
- 缓动：`easing-decelerate`（cubic-bezier 0.0, 0.0, 0.2, 1）
- 具体行为：
  1. 页面从底部 100% 屏幕高度位移滑入到位
  2. 底层页面轻微缩小（scale 0.94）并降低亮度，呈现景深感
  3. 英雄区心形图标延迟 150 ms 后从 scale(0.7) opacity(0) → scale(1.0) opacity(1)（600 ms spring）
  4. 角色卡片依次错落进场（stagger 80 ms，从底部 20 pt 偏移 fade in）

---

## 页面退出动画

### 退出方式：Dismiss 下拉关闭
- 触发：点击左上角 ∨（chevron down）按钮
- 动画类型：反向 slide-down
- 持续时间：300 ms
- 缓动：`easing-standard`（cubic-bezier 0.4, 0.0, 0.2, 1）
- 底层页面恢复 scale(1.0) 和亮度

### 退出方式：确认选择后跳转
- 触发：点击"确认选择"按钮（已有角色选中时）
- 动画类型：Push（向左推出）或 Crossfade（推测，设计稿未定义）
- ⚠️ 设计稿未定义，建议参考 Motion Storyboard

---

## 手势交互

### 下拉关闭手势
- 触发：在顶部导航区域下拉（pan gesture，downward）
- 行为：跟手下滑，释放时根据速度/距离判断是否 dismiss
- ⚠️ 设计稿未定义，建议参考 Motion Storyboard

---

## Hover 状态

> 注：移动端无真实 hover，以下适用于网页端或可访问性 focus 态模拟。

### CharacterCard Hover
- 样式：卡片背景轻微加深（rgba(0,0,0,0.02)），shadow 轻微增强
- 持续时间：150 ms

### SelectButton Hover
- 样式：背景从透明 → rgba(255,183,197,0.12)
- 持续时间：150 ms

---

## Pressed 状态（触摸按压）

### CharacterCard Pressed
- 变化：scale 0.98，shadow Y 减少至 2 pt
- 持续时间：100 ms（按下），200 ms（释放）
- 缓动：linear（按下），easing-decelerate（释放）

### SelectButton Pressed（未选中态）
- 变化：背景 rgba(255,183,197,0.20)，scale 0.96
- 持续时间：100 ms

### SelectedIndicator Pressed（已选中态）
- 变化：scale 0.90，opacity 0.8
- 持续时间：100 ms

### ConfirmButton Pressed
- 变化：scale 0.97，渐变色加深（略微变暗），shadow 减弱
- 持续时间：150 ms（按下），250 ms 弹性回弹释放（spring easing）

---

## Selected 状态（卡片选中切换）

### 触发方式
- 点击卡片任意位置
- 点击右上角"选择"按钮

### 动画行为（未选中 → 选中）
1. "选择"描边按钮：fade out + scale(0.8)，持续 150 ms
2. SelectedIndicator（实心粉圆）：fade in + scale(0.8 → 1.1 → 1.0) spring，持续 250 ms
3. 白色勾图标：stroke path draw（从 0% → 100%），延迟 80 ms，持续 200 ms

### 动画行为（选中 → 取消选中，选择其他角色）
1. 旧选中卡 SelectedIndicator：fade out + scale(1.0 → 0.8)，150 ms
2. 旧选中卡恢复"选择"描边按钮：fade in，200 ms
3. 同时新卡执行"选中动画"（见上）

### 状态约束
- 同一时刻只能有一个角色处于 selected 状态
- 进入页面时默认选中第一个角色（神无月 凛），无需用户操作即可看到选中态

---

## Disabled 状态

### ConfirmButton Disabled（无选中角色时）
- ⚠️ 设计稿未定义此状态（进入页面已有默认选中）
- 建议：opacity 0.45，无 shadow，不可点击
- 建议参考 Motion Storyboard

---

## Loading 状态

### 点击"确认选择"后的加载
- ⚠️ 设计稿未定义
- 建议：按钮内显示旋转指示器，文字替换为"请稍候..."，不可再次点击
- 持续时间：依网络速度，最长建议 3 s 超时后展示 Error 态

---

## Error 状态

- ⚠️ 设计稿未定义
- 建议：底部 Toast 提示错误信息，持续 3 s 自动消失
- 参考 Motion Storyboard

---

## Empty 状态

- 不适用：角色列表由系统预定义，不存在空列表场景

---

## Skeleton 加载状态

- ⚠️ 设计稿未定义
- 建议：角色卡片在图片加载前显示灰色脉冲骨架屏（shimmer），约 200 ms 过渡
- 参考 Motion Storyboard

---

## Scroll 行为

### 角色列表滚动
- 方向：垂直
- 类型：iOS momentum scrolling（惯性）
- 顶部吸附：英雄区不滚动，或随首次滑动消失（具体行为推测，⚠️ 设计稿未明确定义）
- 底部固定：ConfirmCTABar 始终可见，不随内容滚动
- 弹性：iOS 系统默认 rubber-band 效果

### 滚动遮罩
- 顶部：英雄区与卡片区重叠约 40 pt，卡片滚入时渐入（fade in from bottom）
- 底部：ConfirmCTABar 背景色不透明，遮挡底部卡片内容

---

## 卡片选择（Card Selection）完整流程

1. 用户进入页面 → 第一张卡（神无月 凛）处于选中态（SelectedIndicator 显示）
2. 用户向下滑动 → 露出第二张卡（桃乐丝）
3. 用户点击第二张卡或其"选择"按钮
   - 第一张卡 SelectedIndicator 消失，恢复"选择"按钮
   - 第二张卡"选择"按钮消失，SelectedIndicator 出现（spring 动画）
4. 用户点击"确认选择" → 进入聊天主页

---

## 底部确认按钮（Bottom Button）

- 进场：随页面进入时已就位，无独立动画
- 激活条件：有角色被选中（进入即满足）
- 点击反馈：Pressed 态（见上）
- 点击结果：跳转至聊天主页（⚠️ 转场动画设计稿未定义）

---

## 页面转场（Page Transition）

- 进入本页：Bottom Sheet Slide Up（见"页面进入动画"）
- 离开本页（dismiss）：Slide Down（见"页面退出动画"）
- 离开本页（确认后跳转聊天）：⚠️ 设计稿未定义，建议参考 Motion Storyboard
