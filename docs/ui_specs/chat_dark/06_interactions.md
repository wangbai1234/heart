# 06 Interactions — 聊天页 Chat（深色模式）

## 进入动画 Page Enter Animation

- **触发**：从对话列表/主页点击角色进入
- **类型**：Push（水平右侧滑入）
- **时长**：约 350ms
- **缓动**：`cubic-bezier(0.0, 0.0, 0.2, 1)`（Decelerate）
- **细节**：
  1. 整个页面从右侧滑入
  2. Header 和消息列表同步滑入
  3. 消息气泡可逐条从底部弹入（stagger，每条延迟 50ms，估算值）
  4. 背景星云渐显（fade-in，opacity 0→1，150ms）
- **⚠️ 设计稿未定义具体帧动画，建议参考 Motion Storyboard**

---

## 退出动画 Page Exit Animation

- **触发**：点击返回按钮或左滑手势
- **类型**：Pop（水平左侧滑出）
- **时长**：约 280ms
- **缓动**：`cubic-bezier(0.4, 0, 1, 1)`（Accelerate）
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**

---

## 消息气泡出现动画 Bubble Appear

- **触发**：新消息到达（AI 回复或用户发送）
- **AI 消息**：
  - 从左下方向上弹入（translateY 20px → 0 + opacity 0 → 1）
  - 时长：250ms，spring 弹性缓动
  - 可配合 TypingIndicator 隐藏后显示
- **用户消息**：
  - 从右下方向上弹入（translateY 20px → 0 + opacity 0 → 1）
  - 时长：200ms
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**

---

## TypingIndicator 输入中动效

- **触发**：AI 开始生成回复时显示
- **类型**：三个粉色圆点依次弹跳（Wave bounce）
- **时长**：每个点 400ms，stagger 120ms，循环
- **隐藏**：AI 消息到达时 fade-out，时长 150ms
- **出现**：fade-in + translateY(-4px → 0)，时长 200ms

---

## 语音消息交互 Voice Bubble Interactions

### 点击播放按钮 Play/Pause
- **Pressed 反馈**：
  - 按钮缩放 scale(0.90)，时长 100ms
  - 背景圆圈加深（透明度从 0.25 → 0.40）
- **播放中状态**：
  - PlayButton 图标切换为暂停符号（crossfade，150ms）
  - 波形动态律动（各竖条高度随机变化，模拟播放 EQ）
  - 时长计数器倒计时（实时更新）
- **暂停状态**：
  - 图标回到三角形播放符号
  - 波形静止
  - 进度保留
- **播放完成**：
  - 图标回到播放符号
  - 时长显示总时长"0:18"
  - 波形回到静止状态

### 点击波形跳转进度
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**

---

## 文字气泡长按 Long Press

- **触发**：长按任意消息气泡（AI 或用户）
- **时长阈值**：约 500ms
- **效果**：
  - 气泡轻微缩放至 scale(0.97)，表示选中
  - 弹出操作菜单（复制/朗读/转发/删除等）
- **菜单样式**：⚠️ 设计稿未定义，建议参考 Motion Storyboard
- **Haptic**：触觉反馈（Medium Impact）

---

## 输入栏交互 Input Bar Interactions

### 点击输入框 Focus
- **触发**：用户点击 TextInput
- **效果**：
  - iOS 键盘从底部滑入
  - 整个 ChatInputBar 随键盘上移
  - 消息列表可视区域缩短，自动滚动至最新消息
  - 占位文字淡出
  - 输入光标显示
- **时长**：跟随系统键盘动画（约 250-350ms）

### 输入内容变化
- **有内容时**：SendButton 从禁用态切换为激活态（⚠️ 设计稿仅展示激活态）
- **清空时**：SendButton 回到禁用态
- **切换时长**：约 150ms，opacity + color 过渡

### 点击"+"按钮
- **Pressed 反馈**：背景加深，scale(0.92)，时长 100ms
- **效果**：⚠️ 附加功能面板展开，设计稿未定义，建议参考 Motion Storyboard

### 点击发送按钮 Send
- **Pressed 反馈**：scale(0.88)，粉色背景加深，时长 100ms
- **发送流程**：
  1. 用户气泡出现在消息列表底部（buble appear 动效）
  2. 输入框内容清空
  3. 滚动至底部
  4. TypingIndicator 出现（AI 开始思考）
  5. AI 回复气泡出现，TypingIndicator 消失
- **Haptic**：Light Impact

---

## 消息列表滚动 Scroll Behavior

- **方向**：垂直滚动
- **默认位置**：停留在最新消息（底部）
- **滚动类型**：Momentum scroll（iOS 原生惯性）
- **顶部阻尼**：iOS 标准回弹
- **Header 遮挡**：消息滚动至 Header 后方时被 Header 遮盖（z-index 效果）
- **新消息自动滚动**：收到新消息时，如果用户在底部区域（约 200px 范围内）则自动滚动至底部
- **用户手动上滚时**：不自动滚动，显示"新消息"提示（⚠️ 设计稿未定义，建议参考 Motion Storyboard）

---

## 返回按钮 Back Button

- **Pressed**：背景圆圈出现（`rgba(255,255,255,0.12)`），scale(0.92)，时长 100ms
- **Release**：触发返回导航动画

---

## 更多按钮 More Button

- **Pressed**：同 Back Button 按压效果
- **Release**：展开操作菜单（Bottom Sheet 或 Popover）
- **⚠️ 菜单内容，设计稿未定义，建议参考 Motion Storyboard**

---

## 头像点击 Avatar Press

- **Pressed**：scale(0.95)，时长 150ms
- **Release**：⚠️ 跳转至角色详情页，设计稿未定义，建议参考 Motion Storyboard

---

## 状态展示

### Loading 状态
- **场景**：消息发送中、网络延迟
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**
- **建议**：消息气泡尾部显示旋转圆圈或时钟图标

### Error 状态
- **场景**：消息发送失败、网络断开
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**
- **建议**：消息气泡旁显示红色感叹号，点击可重试

### Empty 状态
- **场景**：首次进入，无历史消息
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**
- **建议**：AI 角色发送欢迎语打破沉默

### Skeleton 加载状态
- **场景**：历史消息加载中
- **⚠️ 设计稿未定义，建议参考 Motion Storyboard**
- **建议**：气泡形状骨架屏，shimmer 动效

---

## 背景装饰动效

- **星点闪烁**：部分星点有轻微 opacity 脉动动效（0.4 → 0.8 → 0.4），时长约 2-4s，随机相位
- **⚠️ 设计稿未定义具体参数，建议参考 Motion Storyboard**

---

## 页面转场汇总

| 触发 | 目标页 | 转场类型 |
|------|--------|---------|
| 点击返回"<" | 对话列表/主页 | Pop（左滑） |
| 点击头像 | 角色详情页 | Push 或 Modal |
| 点击"···" | 操作菜单 | Bottom Sheet |
| 点击"+" | 附加功能面板 | Bottom Sheet |
| 长按消息 | 操作菜单 | Popup |
| 发送消息 | 同页（滚动底部） | 内部动效 |
