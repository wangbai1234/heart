# 10 Acceptance Checklist — 聊天页 Chat（浅色模式）

> 目标：整体视觉一致度 ≥ 95%
> 验收人员在实现完成后，对照设计稿（10_chat_light.png）逐项检查并勾选。

---

## 一、Layout 布局

### 1.1 整体结构
- □ 页面分为 Background / StatusBar / Header / MessageScrollArea / Composer / HomeIndicator 六个层级
- □ Header 固定在顶部，不随消息列表滚动
- □ Composer 固定在底部，不随消息列表滚动
- □ 消息列表区域位于 Header 底部与 Composer 顶部之间，可独立滚动
- □ Background 层覆盖全屏，pointer-events 禁用
- □ Z-index 层级正确，Composer 覆盖消息列表，Header 覆盖消息列表

### 1.2 Safe Area
- □ StatusBar 区域（约 47 pt）已预留，内容不遮挡系统状态栏
- □ Home Indicator 区域（约 34 pt）已预留，Composer 不遮挡 Home Bar
- □ 在 iPhone 14 Pro Max / iPhone SE 等不同机型上验证 Safe Area 适配

---

## 二、Spacing / Padding / Margin

- □ 页面水平 Padding 约 16 pt（消息列表区域）
- □ Header 内部水平 Padding 约 20 pt（左右各）
- □ AI Bubble 内部 Padding：约 14 pt 垂直，16 pt 水平（估算值）
- □ User Bubble 内部 Padding：约 14 pt 垂直，16 pt 水平（估算值）
- □ Voice Bubble 内部 Padding：约 16 pt 四周（估算值）
- □ Typing Indicator 内部 Padding：约 16 pt 水平，12 pt 垂直（估算值）
- □ 相邻 Bubble 纵向间距约 8-12 pt（估算值）
- □ Composer 与屏幕底边的间距约 46 pt（含 Home Indicator 高度，估算值）
- □ Composer 内部元素间 Gap 约 10 pt（估算值）
- □ 角色头像与 CharacterInfo 的间距约 10 pt（估算值）
- □ 在线状态圆点与状态文字的间距约 4 pt（估算值）

---

## 三、Radius 圆角

- □ AI Bubble 圆角：右上/右下/左上约 20 pt，左下约 6 pt（气泡尾部，估算值）
- □ User Bubble 圆角：左上/左下/右下约 20 pt，右上约 6 pt（气泡尾部，估算值）
- □ Voice Bubble 圆角与 AI Bubble 一致
- □ Typing Indicator 圆角与 AI Bubble 一致
- □ Header 底部圆角约 24 pt（估算值）
- □ Composer 圆角约 32 pt（胶囊形，估算值）
- □ 发送按钮圆角：圆形（radius-full）
- □ 角色头像裁切：圆形（radius-full）
- □ 在线状态圆点：圆形（radius-full）
- □ Home Indicator：圆角 full

---

## 四、Shadow 阴影

- □ Header 底部有柔和投影（rgba(0,0,0,0.06)，blur 12pt，向下 2pt，估算值）
- □ Composer 顶部有向上阴影（rgba(0,0,0,0.08)，blur 16pt，向上 -4pt，估算值）
- □ AI Bubble 有轻微粉色投影（rgba(255,183,197,0.1)，blur 8pt，估算值）
- □ 发送按钮有粉色光晕阴影（rgba(255,183,197,0.3)，blur 12pt，向下 4pt，估算值）
- □ User Bubble 无明显阴影

---

## 五、Blur 效果

- □ Header 背景有毛玻璃模糊效果（backdrop-filter: blur 约 20pt，估算值）
- □ AI Bubble 背景有轻微毛玻璃效果（白色半透明）
- □ Voice Bubble 背景有轻微毛玻璃效果（与 AI Bubble 一致）
- □ Typing Indicator 背景有轻微毛玻璃效果
- □ Composer 背景有毛玻璃模糊效果（backdrop-filter: blur 约 24pt，估算值）
- □ 背景光晕有 blur 效果（filter: blur 约 40pt，估算值）
- □ 毛玻璃效果在半透明 Bubble 下方仍可见背景渐变（视觉层次清晰）

---

## 六、Background / Gradient

- □ 页面背景是否直接使用 `/Users/wanglixun/heart/assets/backgrounds/亮色背景图.png`
- □ 背景图是否保留原始云层、暖光、星点氛围，无 CSS 重画痕迹
- □ Voice Bubble 波形颜色：水平渐变，左侧 #FFB7C5（粉）→ 右侧 #C8B6FF（紫），估算值
- □ 是否未将背景替换为代码渐变

---

## 七、Typography 字体排版

- □ 中文使用 PingFang SC（或 HarmonyOS Sans SC）
- □ 数字/拉丁字符使用 SF Pro Rounded
- □ 角色名"小屿"：约 17pt，font-weight 600
- □ AI Bubble 正文：约 16pt，font-weight 400，行高约 1.6
- □ User Bubble 正文：约 16pt，font-weight 400，行高约 1.6
- □ 在线状态"温柔在线"：约 13pt，font-weight 400
- □ 日期分隔符"今天 · 上午 9:41"：约 12pt，font-weight 400
- □ 语音 Caption "AI朗读 · 可点击播放"：约 12pt，font-weight 400
- □ 时长"0:18"：约 13pt，font-weight 400
- □ Composer Placeholder：约 15pt，font-weight 400
- □ 时间显示"9:41"（StatusBar）：约 15pt，font-weight 600

---

## 八、组件尺寸

- □ Header 高度约 80pt（估算值）
- □ 角色头像 48×48pt，圆形（估算值）
- □ 若用户未上传头像，Header 是否显示空白占位头像组件
- □ 返回按钮触摸区 44×44pt
- □ 更多按钮触摸区 44×44pt
- □ 在线状态圆点 6×6pt（估算值）
- □ AI Bubble 最大宽度约 260pt（不超过屏宽 67%，估算值）
- □ User Bubble 最大宽度约 260pt（估算值）
- □ Voice Bubble 宽度约 300pt（估算值）
- □ Voice Bubble 高度约 90pt（估算值）
- □ 播放按钮容器约 32×32pt（估算值）
- □ 波形可视化约 170×32pt（估算值）
- □ Typing Indicator 约 72×48pt（估算值）
- □ 3个 Typing 圆点直径约 10pt（估算值）
- □ Composer 高度约 64pt（估算值）
- □ Composer 宽度约 358pt（左右各约 16pt 间距，估算值）
- □ 发送按钮 40×40pt 圆形（估算值）
- □ 附加"+"按钮约 36×36pt（估算值）
- □ Home Indicator 约 134×5pt（估算值）

---

## 九、Glass Effect 透明度

- □ Header 背景：rgba(255,255,255,0.55)（opacity 约 55%，估算值）
- □ AI Bubble 背景：rgba(255,255,255,0.75)（opacity 约 75%，估算值）
- □ Voice Bubble 背景：rgba(255,255,255,0.75)（与 AI Bubble 一致）
- □ Typing Indicator 背景：rgba(255,255,255,0.75)（与 AI Bubble 一致）
- □ Composer 背景：rgba(255,255,255,0.65)（opacity 约 65%，估算值）
- □ User Bubble 背景：#A7C7E7 实色（无透明度）
- □ 所有毛玻璃组件在设计稿背景下，透明度视觉层次清晰可辨
- □ 空白占位头像若出现，是否保持中性、无角色特征

---

## 十、Visual Weight 视觉重量

- □ 发送按钮（粉色圆形）是页面视觉重心之一，正确引导用户注意力
- □ AI Bubble 与 User Bubble 颜色差异明显，一眼可区分发送方
- □ Typing Indicator 粉色圆点足够醒目，但不喧宾夺主
- □ Header 角色头像和名字作为信息锚点清晰可识别
- □ 背景光晕是装饰性元素，视觉重量不超过前景内容
- □ Voice Bubble 的波形渐变颜色增加了视觉趣味性，同时不干扰正文 Bubble

---

## 十一、Alignment 对齐

- □ AI Bubble：左对齐，Margin Left 约 16pt（估算值）
- □ User Bubble：右对齐，Margin Right 约 16pt（估算值）
- □ 日期分隔符：水平居中
- □ Typing Indicator：左对齐（与 AI Bubble 一致）
- □ Voice Bubble：左对齐（与 AI Bubble 一致）
- □ Header 内部：返回按钮左对齐，角色信息居中（左侧），更多按钮右对齐
- □ Composer 内部：附加按钮左对齐，文字输入框居中弹性，发送按钮右对齐
- □ Voice Bubble Caption 文字：在 Bubble 内水平居中（估算值）

---

## 十二、Safe Area 遵守

- □ 内容不侵入 StatusBar 区域（顶部 47pt，估算值）
- □ 内容不侵入 Home Indicator 区域（底部 34pt，估算值）
- □ Composer 底部距屏幕底边包含 Safe Area Inset（约 34pt Home Area + 约 12pt Margin）
- □ 在 iPhone 14 / 15 系列（Dynamic Island）验证顶部 Safe Area
- □ 在 iPhone SE（无刘海）验证顶部 Safe Area 适配

---

## 十三、状态指示器

- □ 在线状态圆点颜色正确（蓝色 #5FC8E8，估算值）
- □ 在线状态文字"温柔在线"正确显示
- □ Typing Indicator 3个圆点颜色正确（#FFB7C5 粉色）
- □ Typing Indicator 圆点呼吸动画运行（不静止）
- □ Voice Bubble 播放状态图标正确（三角形 = 未播放）
- □ Home Indicator 颜色正确（深色 #3A3A4A，适配浅色背景）

---

## 十四、颜色 100% 符合 Design Token

- □ Primary #FFB7C5 用于：发送按钮背景、播放按钮图标色、Typing 圆点色
- □ Secondary #A7C7E7 用于：User Bubble 背景色
- □ Accent #C8B6FF 用于：背景光晕辅助色、波形渐变终点色
- □ Ink #3A3A4A 用于：AI Bubble 正文、角色名、Header 图标、Home Indicator
- □ 所有颜色值与 03_design_tokens.md 中定义的 Token 一致，无偏差
- □ 渐变颜色与 03_design_tokens.md 中定义的 Gradient Token 一致

---

## 十五、应用名"yuoyuo"拼写

- □ 如页面内出现 App 名称，拼写为"yuoyuo"（全小写，无大写，无空格）
- □ 不出现"YuoYuo"、"Yuoyuo"、"YUOYUO"等变体
- □ Placeholder 文字"想和小屿说点什么..."中未出现 App 名称（无需检查）
- □ 如有 Toast/提示消息包含 App 名，确认拼写正确

---

## 十六、整体视觉一致度目标

- □ 与设计稿（10_chat_light.png）对比，布局偏差 ≤ 2pt
- □ 颜色使用与设计稿无肉眼可见色差
- □ 字体大小与设计稿视觉一致
- □ 圆角弧度与设计稿一致
- □ 透明度/毛玻璃效果与设计稿视觉一致
- □ 阴影方向/强度与设计稿一致
- □ 整体视觉氛围（温暖/治愈/二次元）与设计稿一致
- □ **整体视觉一致度评分 ≥ 95%**（由 UI 设计师或产品经理最终评分）

---

## 验收结果记录

| 项目 | 评分（0-100） | 备注 |
|------|-------------|------|
| Layout 布局 | — | |
| Spacing/Padding | — | |
| Radius 圆角 | — | |
| Shadow 阴影 | — | |
| Blur 效果 | — | |
| Gradient 渐变 | — | |
| Typography | — | |
| 组件尺寸 | — | |
| Glass Effect | — | |
| Visual Weight | — | |
| Alignment | — | |
| Safe Area | — | |
| 状态指示器 | — | |
| 颜色准确度 | — | |
| **综合评分** | — | 目标 ≥ 95 |

验收人：___________　日期：___________　签字：___________
