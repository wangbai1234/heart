# Page

Home

---------------------------------------

Overall Score

62 / 100

---------------------------------------

Summary

当前 Home 已引用正确背景与角色资源，但整体仍是“功能型近似实现”，与设计稿的精细构图、玻璃层级和底部导航形态差距明显。

---------------------------------------

P0（必须修复）

- Hero Card 不是设计稿对应的构图。
原因：当前使用了自绘 `HeartOrb` 和简化信息浮层，心形尺寸、光晕、文字区与 CTA 的关系都与设计稿不一致。
建议修改方式：重建 Hero Card 的内部层级和比例，不要继续使用当前简化的 `HeartOrb` 结构。
涉及组件：Hero Card、CTA、主视觉心形。
涉及文件：`web/src/pages/HomePage.tsx`

- 底部导航栏样式错误。
原因：设计稿是浮动的玻璃胶囊式 TabBar；当前实现是贴底全宽平栏。
建议修改方式：重做 `TabBar` 的容器形态、阴影、圆角、底部留白和激活态指示。
涉及组件：TabBar。
涉及文件：`web/src/components/ui/TabBar.tsx`

- 最近聊天区域结构错误。
原因：设计稿是整体玻璃卡片加分割线列表；当前是裸列表，缺少包裹卡片、统一内边距和分组阴影。
建议修改方式：将最近聊天列表重构为单一玻璃卡片容器，统一头像尺寸、时间列、未读点和分割线。
涉及组件：最近聊天列表。
涉及文件：`web/src/pages/HomePage.tsx`

---------------------------------------

P1（建议修复）

- Header 品牌字标、右上角头像和顶部间距偏小，首页第一屏识别度不足。
涉及组件：Header、Avatar。
涉及文件：`web/src/pages/HomePage.tsx`、`web/src/components/ui/Avatar.tsx`

- 三个快捷入口卡片尺寸偏小，图标和标签权重不够，导致与设计稿的三列入口块差距明显。
涉及组件：Quick Actions。
涉及文件：`web/src/pages/HomePage.tsx`

- Hero Card 背景资源虽然正确，但裁切方式与设计稿不同，顶部心形与底部信息层被压缩。
涉及组件：Hero 背景图裁切。
涉及文件：`web/src/pages/HomePage.tsx`

---------------------------------------

P2（可优化）

- `loading` 分支存在但没有真实数据态入口，Skeleton 目前无法进行稳定视觉回归。
涉及组件：Skeleton、Loading State。
涉及文件：`web/src/pages/HomePage.tsx`、`web/src/components/ui/Skeleton.tsx`

---------------------------------------

Assets

- 资源引用正确：`亮色背景图.png`、`暗色背景图.png`、`background_character_hero.webp`、角色头像资源。
- 当前问题主要来自资源排版方式，而不是资源引用错误。
- 运行态用户头像为空时使用空白占位，符合当前约束。

---------------------------------------

Motion

- Hero 心形有浮动动画，但不是设计稿中的最终质感。
- Tab 切换与卡片按压仅有基础缩放，缺少设计稿级的轻玻璃回弹。

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
☐ Hero
☑ Interaction
☐ State

---------------------------------------

Final Score

62 / 100
