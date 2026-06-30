# 06 Interactions — 聊天页 Chat（浅色模式）

## 进入动画

| 场景 | 动画描述 | 时长 | Easing |
|------|---------|------|--------|
| 从会话列表进入 | 整个页面从右侧滑入（iOS 原生 push 转场） | 300 ms | easing-decelerate |
| Header 出现 | 随页面滑入同步出现，无独立动画 | — | — |
| 消息列表出现 | ⚠️ 设计稿未定义，建议：消息从下到上依次 fade+slide in，stagger 30ms per item | — | — |
| Composer 出现 | ⚠️ 设计稿未定义，建议：随页面同步出现，或从底部 slide up | — | — |

---

## 退出动画

| 场景 | 动画描述 | 时长 | Easing |
|------|---------|------|--------|
| 点击返回按钮退出 | 整个页面向右滑出（iOS 原生 pop 转场） | 300 ms | easing-accelerate |
| 边缘右滑手势退出 | iOS 原生交互式拖拽返回 | 跟手 | — |

---

## 按压（Pressed）状态

### BackButton（返回按钮）
- 触发：手指按下瞬间
- 效果：图标 opacity 降至 60%（估算值）
- 时长：100 ms（duration-instant）
- 松开：opacity 恢复 100%，触发页面返回

### MoreButton（更多按钮）
- 触发：手指按下瞬间
- 效果：图标 opacity 降至 60%（估算值）
- 时长：100 ms
- 松开：弹出 ActionSheet / BottomSheet（⚠️ 设计稿未定义弹出内容）

### AITextBubble（AI 文字气泡）
- 短按：⚠️ 设计稿未定义，建议：scale(0.98) + opacity 90%，100ms
- 长按：⚠️ 设计稿未定义，建议：触发上下文菜单（复制/收藏/朗读）

### UserTextBubble（用户文字气泡）
- 短按：⚠️ 设计稿未定义，建议：scale(0.98) + opacity 90%，100ms
- 长按：⚠️ 设计稿未定义，建议：触发上下文菜单（复制/删除）

### AIVoiceBubble（语音气泡）
- 点击整个 Bubble：触发播放/暂停语音
- 点击播放按钮：同上（触摸区扩展到整个 Bubble，提升可用性）
- 按压效果：播放按钮 scale(0.9)，100ms（估算值）

### AttachButton（"+"按钮）
- 触发：手指按下
- 效果：scale(0.9) + opacity 70%，100ms（估算值）
- 松开：展开附加功能面板（⚠️ 设计稿未定义面板内容和展开动画）

### SendButton（发送按钮）
- 触发：手指按下
- 效果：scale(0.9) + shadow-send-btn 缩小，100ms（估算值）
- 松开：发送消息，输入框清空，新消息 Bubble 出现动画

---

## 消息发送交互

### 用户发送消息流程
1. 用户在 Composer 输入文字
2. 点击发送按钮（SendButton）
3. 输入框文字清空
4. **User Bubble 出现动画**：⚠️ 设计稿未定义，建议：从底部 slide up + fade in，300ms，easing-decelerate
5. 消息列表滚动到底部（auto-scroll）
6. AI Typing Indicator 出现（呼吸动画开始）
7. AI 生成完成后，Typing Indicator 消失，AI Bubble 出现

### AI Bubble 出现动画
⚠️ 设计稿未定义，建议参考 Motion Storyboard：
- 效果：从左侧 translate-x(-10px) + opacity 0 → translate-x(0) + opacity 1
- 时长：300ms，easing-decelerate
- 弹簧可选：spring-bubble 参数

---

## AI Voice Bubble 播放交互

### 播放状态切换
- 点击未播放的 Voice Bubble → 开始播放
  - 播放按钮：三角形 → 暂停图标（⚠️ 设计稿未定义暂停图标样式）
  - 波形动画：⚠️ 设计稿未定义，建议：从左到右扫描高亮，高亮颜色比默认色更深
- 点击播放中的 Voice Bubble → 暂停
  - 暂停图标 → 三角形
  - 波形动画停止，停在当前位置

### 播放完成
- 播放按钮恢复三角形（暂停图标 → 播放图标）
- 波形扫描指示复位到起点
- ⚠️ 设计稿未定义完成后的视觉变化，建议：波形颜色整体轻微变暗表示已播放

---

## Typing Indicator（打字中指示器）动画

### 呼吸动画规范（⚠️ 设计稿未定义时序，以下为建议值）
- 动画类型：三个圆点交替上下弹跳或缩放
- 单点动画：scale 0.6 → 1.0 → 0.6（或 translateY 0 → -4pt → 0）
- 单次时长：600ms
- 循环：infinite
- 错开延迟：
  - 第1个圆点：delay 0ms
  - 第2个圆点：delay 150ms
  - 第3个圆点：delay 300ms
- Easing：easing-standard

### 出现/消失
- 出现：fade in + scale 0.8 → 1.0，200ms（建议值）
- 消失：fade out + scale 1.0 → 0.8，200ms（建议值）

---

## 滚动行为

| 场景 | 行为描述 |
|------|---------|
| 加载历史消息 | 初次进入页面，列表滚动定位到最底部，显示最新消息 |
| 新消息到达 | 若用户当前在列表底部，自动滚动到最新消息 |
| 用户手动上滑 | auto-scroll 暂停，保持用户当前阅读位置 |
| 新消息到达但用户上滑中 | ⚠️ 设计稿未定义，建议：底部出现"X条新消息"提示气泡，点击跳到底部 |
| 滚动到顶部 | ⚠️ 设计稿未定义，建议：触发加载更早历史消息（上拉加载更多） |
| 消息列表滚动条 | 隐藏滚动条（scrollbar: hidden） |
| 滚动惯性 | iOS 原生弹性滚动（overscroll-behavior: auto） |

---

## 键盘弹出行为
⚠️ 设计稿未定义，建议参考 Motion Storyboard：
- 点击 TextInput → 系统键盘弹起
- Composer 随键盘上移（KeyboardAvoidingView 或 adjustResize）
- 消息列表高度压缩，最新消息保持可见
- 键盘收起：点击消息区域任意位置，Composer 随键盘下移

---

## Hover 状态（移动端不适用）
移动端触屏设备无 Hover 状态，跳过。

---

## Selected 状态
⚠️ 设计稿未定义选中状态，建议参考 Motion Storyboard：
- 长按 Bubble 进入选中模式
- 选中的 Bubble 显示 checkmark 覆盖层
- 顶部出现批量操作工具栏（转发/删除/收藏）

---

## Disabled 状态
⚠️ 设计稿未定义禁用状态，建议：
- 网络断开时：SendButton opacity 40%，不可点击
- 消息发送中：SendButton 变为加载 spinner（⚠️ 设计稿未定义）

---

## Loading 状态
⚠️ 设计稿未定义，建议参考 Motion Storyboard：
- 历史消息加载中：列表顶部显示小型 loading spinner
- 消息发送中：User Bubble 右下角显示发送状态点（发送中/已送达/已读）

---

## Error 状态
⚠️ 设计稿未定义，建议参考 Motion Storyboard：
- 消息发送失败：User Bubble 左侧显示红色感叹号图标，点击可重试

---

## Empty 状态
⚠️ 设计稿未定义，建议参考 Motion Storyboard：
- 首次进入（无历史消息）：页面中央显示欢迎插画 + AI 角色打招呼消息

---

## Skeleton 加载状态
⚠️ 设计稿未定义，建议参考 Motion Storyboard：
- 历史消息加载时，气泡位置显示灰色骨架屏占位，shimmer 动画

---

## 页面转场（汇总）

| 来源页 | 目标页 | 转场方式 |
|--------|--------|---------|
| 会话列表 → 聊天页 | Push 滑入（右→左） | iOS Native Push |
| 聊天页 → 会话列表 | Pop 滑出（左→右） | iOS Native Pop |
| 聊天页 → 更多菜单 | Bottom Sheet 从底部上滑 | ⚠️ 设计稿未定义 |
| 聊天页 → 附加功能面板 | ⚠️ 设计稿未定义 | ⚠️ 设计稿未定义 |
