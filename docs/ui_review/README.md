# UI Review

本目录是当前 `web/` 前端与 GPT-Image2 设计稿的逐页视觉审查结果。

审查基准：

- 设计稿：`/Users/wanglixun/heart/web/design/source`
- 工程规范：`/Users/wanglixun/heart/docs/ui_specs`
- 实际站点：`http://127.0.0.1:4173`
- 截图留档：`/Users/wanglixun/heart/docs/ui_review/screenshots`

已完成页面审查：

- `splash_review.md`
- `onboarding_review.md`
- `login_review.md`
- `home_review.md`
- `character_review.md`
- `chat_light_review.md`
- `chat_dark_review.md`
- `redeem_review.md`
- `settings_review.md`
- `shared_states_review.md`

关键结论：

- `Splash` 接近设计稿，属于当前最接近可交付状态的页面。
- `Login / Home / Character / Chat / Redeem / Settings` 均存在明显工程级偏差，不能视为 95% 视觉一致。
- `Redeem` 偏差最大，当前实现是简化版表单，不是设计稿对应页面。
- `TabBar`、`Dialog`、`Button`、`ChatBubble`、`OTPInput` 等共享组件是多页误差的核心来源。
- `Offline / Empty / BottomSheet / Loading / Toast / Dialog` 没有稳定 QA 预览入口，导致自动验收无法完整覆盖。

建议 Mimo 执行顺序：

1. 先补 QA 预览入口与状态页路由。
2. 修正共享组件：`TabBar`、`Button`、`Dialog`、`ChatBubble`、`OTPInput`。
3. 再修 `Redeem`、`Home`、`Character`、`Chat`。
4. 最后回收 `Login`、`Settings`、`Onboarding` 的细节误差。
