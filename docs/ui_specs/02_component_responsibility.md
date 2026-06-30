# 02 Component Responsibility — 组件职责边界

## 1. 必须由 React 组件实现

以下元素禁止用图片替代，必须是真实组件：

- Button
- Dialog
- Toast
- BottomSheet
- NavigationBar
- TabBar
- Header
- Typography
- List / ListRow
- Input / OTPInput / SearchInput / ComposerInput
- SegmentedControl
- Switch
- Slider
- ChatBubble
- VoiceWaveform
- Loading
- Skeleton
- EmptyState 容器
- ErrorState 容器
- OfflineState 容器
- Transition 容器

## 2. 必须由状态驱动实现

- 页面 Loading / Loaded / Empty / Error / Offline
- Toast 显隐
- Dialog 开关
- BottomSheet 开关
- 主题切换
- 当前选中角色
- Chat 发送中 / 已发送 / 失败
- OTP 输入完成度

## 3. 可以引用图片的部分

- 页面背景图
- Hero Banner
- Splash 全屏图
- Onboarding 插画
- Redeem 礼盒
- 角色头像

## 4. 明确禁止

- 不允许把按钮做成整张图片
- 不允许把输入框做成整张图片
- 不允许把 Toggle / Slider / TabBar / Toast / BottomSheet 做成整张图片
- 不允许把聊天气泡正文做成位图
- 不允许把骨架屏做成静态图

## 5. 状态管理职责

- 路由状态：由路由层管理
- 页面 UI 状态：由页面级 state machine 管理
- 组件局部状态：由组件内部管理
- 长生命周期全局状态：如主题、当前角色、登录态，可使用 store

允许实现自由：

- Zustand / Context / Redux 均可

不允许的自由：

- 用隐式布尔散落管理页面状态
- 让一个页面同时落入多个互斥状态
