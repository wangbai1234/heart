# Page

Chat Light

---------------------------------------

Overall Score

68 / 100

---------------------------------------

Summary

浅色聊天页已经使用正确背景资源并具备基本结构，但头部、气泡、语音卡片和输入栏都比设计稿更小、更平，缺少最终视觉张力。

---------------------------------------

P0（必须修复）

- 整体比例偏小，导致页面像缩略版。
原因：头部高度、消息气泡宽高、语音卡片尺寸、底部输入栏厚度都明显小于设计稿。
建议修改方式：按设计稿重设聊天页整体尺寸体系，不要只微调单个数值。
涉及组件：Header、ChatBubble、VoiceBubble、Composer。
涉及文件：`web/src/pages/ChatLightPage.tsx`、`web/src/components/ui/ChatBubble.tsx`

- 语音消息卡片与设计稿不一致。
原因：设计稿中的语音卡片有更完整的播放按钮、波形密度、信息排版和玻璃光感；当前实现是简化柱状条。
建议修改方式：重做语音卡片结构与波形样式。
涉及组件：Voice Message Bubble。
涉及文件：`web/src/pages/ChatLightPage.tsx`

- 底部输入区太薄，发送按钮和左侧加号按钮尺寸不对。
原因：设计稿输入条更厚、更柔和，按钮更大、底部浮动感更强。
建议修改方式：重做 Composer 的高度、圆角、左右按钮尺寸和内部占位文案位置。
涉及组件：Composer。
涉及文件：`web/src/pages/ChatLightPage.tsx`

---------------------------------------

P1（建议修复）

- 头部头像、名称和在线状态区缩小过度，导致首屏识别度不足。
涉及组件：Header。
涉及文件：`web/src/pages/ChatLightPage.tsx`

- AI 气泡和用户气泡缺少设计稿中的柔和渐变与玻璃边缘处理。
涉及组件：ChatBubble。
涉及文件：`web/src/components/ui/ChatBubble.tsx`

---------------------------------------

P2（可优化）

- typing 状态存在，但没有稳定 QA 入口，难以反复验收设计稿中的加载语义。
涉及组件：BreathingDots。
涉及文件：`web/src/pages/ChatLightPage.tsx`

---------------------------------------

Assets

- 资源引用正确：`亮色背景图.png`
- 当前 Companion 头像使用角色资源，符合设计图方向。
- 未发现背景错误引用。

---------------------------------------

Motion

- 基础输入、发送和 typing 状态存在。
- 缺少设计稿中气泡出现、语音卡片与输入栏的更柔和动效节奏。

---------------------------------------

Acceptance

☐ Layout
☑ Assets
☐ Typography
☐ Motion
☐ Glass
☐ Blur
☐ Shadow
☑ Background
☑ Hero
☑ Interaction
☐ State

---------------------------------------

Final Score

68 / 100
