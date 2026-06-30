# Page

Login

---------------------------------------

Overall Score

74 / 100

---------------------------------------

Summary

资源引用正确，但页面比例、玻璃卡片体量和表单层级都比设计稿更弱，当前更像缩小版实现。

---------------------------------------

P0（必须修复）

- Hero 区高度和下方表单卡片比例不对。
原因：设计稿上半部分主视觉更强，下半部分玻璃卡片也更大；当前 `42%` 高度和较小卡片导致页面重心下沉。
建议修改方式：按设计稿重建上下区块比例，放大 Hero 区和表单卡片，重算品牌区与表单区间距。
涉及组件：页面布局。
涉及文件：`web/src/pages/LoginPage.tsx`

- 表单卡片质感不足。
原因：设计稿中的玻璃卡片更厚、更亮、留白更大；当前输入、说明、CTA 被压得过紧。
建议修改方式：增加卡片 padding、圆角体量、按钮高度和说明区留白；不要继续沿用当前通用尺寸。
涉及组件：Input、Button、表单容器。
涉及文件：`web/src/pages/LoginPage.tsx`、`web/src/components/ui/Input.tsx`、`web/src/components/ui/Button.tsx`

---------------------------------------

P1（建议修复）

- 品牌字标和副标题尺寸偏小，无法达到设计稿中的首屏识别度。
涉及组件：Typography。
涉及文件：`web/src/pages/LoginPage.tsx`

- 协议文案与“我有兑换码”入口过于靠下且视觉弱化。
涉及组件：页尾文案区。
涉及文件：`web/src/pages/LoginPage.tsx`

- 按钮禁用态过淡，容易被误判为不可用装饰元素。
涉及组件：Button。
涉及文件：`web/src/components/ui/Button.tsx`

---------------------------------------

P2（可优化）

- 成功提交后的过渡状态目前只表现为 loading spinner，没有设计稿级的情绪化反馈层。
涉及组件：Button loading。
涉及文件：`web/src/components/ui/Button.tsx`

---------------------------------------

Assets

- 资源引用正确：`/assets/backgrounds/background_login_hero.webp`
- 未发现错误资源、拉伸或污染。

---------------------------------------

Motion

- 基础交互存在。
- 缺少设计稿对应的表单出现节奏和按钮状态反馈表现。

---------------------------------------

Acceptance

☐ Layout
☑ Assets
☐ Typography
☐ Motion
☑ Glass
☑ Blur
☐ Shadow
☑ Background
☑ Hero
☑ Interaction
☐ State

---------------------------------------

Final Score

74 / 100
