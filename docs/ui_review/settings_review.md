# Page

Settings

---------------------------------------

Overall Score

72 / 100

---------------------------------------

Summary

设置页有基本结构，但多处仍是轻量实现；最大问题是深色主题资源使用错误，且共享反馈层质感不足。

---------------------------------------

P0（必须修复）

- 深色模式背景资源使用错误。
原因：页面背景被硬编码为 `亮色背景图.png`，即使切到深色主题也不会切换到暗色资源。
建议修改方式：按主题分支切换设置页背景资源，保证 light/dark 都符合规范。
涉及组件：页面背景。
涉及文件：`web/src/pages/SettingsPage.tsx`

- 设置页整体密度过高，卡片比例偏小。
原因：设计稿中的 profile card、分组卡片和行高都更大、更疏朗；当前实现更像表单列表页。
建议修改方式：扩大卡片高度、外间距、标题区留白和每行控件高度。
涉及组件：Profile Card、GroupCard、SettingRow。
涉及文件：`web/src/pages/SettingsPage.tsx`

- 注销弹窗是通用简化 Dialog，不是设计稿级反馈层。
原因：当前弹窗的遮罩、卡片厚度、按钮比例和文字间距都偏弱。
建议修改方式：对 `Dialog` 做设计稿级重构，并让设置页使用重构后的反馈层。
涉及组件：Dialog、Button。
涉及文件：`web/src/pages/SettingsPage.tsx`、`web/src/components/ui/Dialog.tsx`、`web/src/components/ui/Button.tsx`

---------------------------------------

P1（建议修复）

- Profile Card 中空白头像占位样式过于通用，没有延续设计稿中的精致边框和光感。
涉及组件：Avatar。
涉及文件：`web/src/components/ui/Avatar.tsx`、`web/src/pages/SettingsPage.tsx`

- 主题分段控件、滑块、开关都能工作，但视觉权重仍低于设计稿。
涉及组件：SegmentedControl、Slider、Switch。
涉及文件：`web/src/components/ui/SegmentedControl.tsx`、`web/src/components/ui/Slider.tsx`、`web/src/components/ui/Switch.tsx`

---------------------------------------

P2（可优化）

- Toast 组件已挂载但本页没有稳定触发入口，后续需要 QA 入口统一回归。
涉及组件：Toast。
涉及文件：`web/src/pages/SettingsPage.tsx`、`web/src/components/ui/Toast.tsx`

---------------------------------------

Assets

- Light 模式资源引用正确：`亮色背景图.png`
- Dark 模式资源引用错误：应切换为 `暗色背景图.png`

---------------------------------------

Motion

- 主题切换工作正常。
- 弹窗与分段控件缺少设计稿级的柔和反馈节奏。

---------------------------------------

Acceptance

☐ Layout
☐ Assets
☐ Typography
☐ Motion
☑ Glass
☑ Blur
☐ Shadow
☐ Background
☑ Hero
☑ Interaction
☐ State

---------------------------------------

Final Score

72 / 100
