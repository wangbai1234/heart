# Page

Shared States / Feedback

---------------------------------------

Overall Score

35 / 100

---------------------------------------

Summary

`Offline / Empty / BottomSheet / Loading / Toast / Dialog / Skeleton` 虽然部分已有组件实现，但当前没有稳定、可路由、可自动化截图的 QA 预览入口，导致这些状态无法完成逐页视觉验收。

---------------------------------------

P0（必须修复）

- 缺少状态页与反馈层 QA 入口。
原因：`App.tsx` 只注册了业务页路由，没有给 `OfflineState`、`EmptyState`、`BottomSheet`、`Loading`、`Toast`、`Dialog`、`Skeleton` 提供独立预览页。
建议修改方式：新增内部 QA 路由或 preview harness，例如 `/qa/offline`、`/qa/empty`、`/qa/feedback`、`/qa/loading`。
涉及组件：路由、状态预览页。
涉及文件：`web/src/App.tsx`

- `OfflineState`、`EmptyState`、`BottomSheet`、`Loading` 等组件没有被稳定挂载，无法验证是否匹配设计稿。
原因：组件存在，但未进入可验收页面流。
建议修改方式：建立统一 `UIStatePreviewPage`，集中展示 light/dark、dialog/toast/sheet/loading/skeleton。
涉及组件：OfflineState、EmptyState、BottomSheet、Loading、Skeleton。
涉及文件：`web/src/components/ui/OfflineState.tsx`、`web/src/components/ui/EmptyState.tsx`、`web/src/components/ui/BottomSheet.tsx`、`web/src/components/ui/Loading.tsx`、`web/src/components/ui/Skeleton.tsx`

- 当前 BottomSheet 根本没有业务入口，不满足“自动浏览所有页面/状态”的验收要求。
原因：组件存在但未使用。
建议修改方式：至少提供一个稳定的展示页或业务触发入口。
涉及组件：BottomSheet。
涉及文件：`web/src/components/ui/BottomSheet.tsx`

---------------------------------------

P1（建议修复）

- `Dialog` 与 `Toast` 虽可在个别页面触发，但没有固定 QA 档位，视觉回归非常低效。
涉及组件：Dialog、Toast。
涉及文件：`web/src/components/ui/Dialog.tsx`、`web/src/components/ui/Toast.tsx`

- `usePageState` 已定义 loading/loaded/empty/offline/error/transition，但当前没有任何总控页面消费这套状态机。
涉及组件：状态管理。
涉及文件：`web/src/hooks/usePageState.ts`

---------------------------------------

P2（可优化）

- 可增加一页同时展示 light/dark 反馈层，对齐设计稿 `components_feedback` 与 `state_empty`、`state_offline` 的验收方式。
涉及组件：Preview Page。
涉及文件：建议新增 `web/src/pages/UIStatePreviewPage.tsx`

---------------------------------------

Assets

- 这些共享状态多数不依赖额外复杂图片资源。
- 问题核心是“不可访问、不可截图、不可回归”，不是资源映射错误。

---------------------------------------

Motion

- 当前无法稳定审查 Toast、Dialog、BottomSheet、Loading 的出现与退出动画一致性。

---------------------------------------

Acceptance

☐ Layout
☐ Assets
☐ Typography
☐ Motion
☐ Glass
☐ Blur
☐ Shadow
☐ Background
☐ Hero
☐ Interaction
☐ State

---------------------------------------

Final Score

35 / 100
