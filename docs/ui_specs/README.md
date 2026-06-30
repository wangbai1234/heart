# UI Specs — AI Coding 唯一工程规范入口

本目录是 yuoyuo 前端 UI 工程规范的唯一入口，目标是直接驱动 AI Coding（Mimo）生成与 GPT-Image2 原始设计高度一致的 React + Tailwind 前端工程。

## 目标

- 视觉一致性目标：`>= 95%`
- 不允许 AI 重新设计、补画、脑补资源
- 不允许 AI 自行改动布局、颜色、比例、间距、动效节奏
- 只允许在代码组织、状态管理实现、组件拆分方式上做工程化选择

## 规范优先级

出现冲突时，必须按以下顺序执行：

1. 本目录根级文档 `README.md` + `00`–`09` 文档
2. 各页面目录下的 `05_assets.md`
3. 各页面目录下的其他页面说明
4. `web/design/source/` 设计图
5. `docs/design/gpt_image2_visual_prompts.md`

说明：

- 页面目录中凡是出现“建议”“可选”“可生成”等旧表述，一律以下方新增的根级总规范和最新 `05_assets.md` 为准。
- `components_feedback`、`state_empty`、`state_offline`、`motion_storyboard`、`palette`、`typography`、`style_tile`、`iconset`、`elevation_radius_glass`、`app_icon` 是基础参考模块，不是业务路由页面。

## 业务页面目录映射

| 规范目录 | 页面标识 | 视觉参考 |
|---|---|---|
| `splash/` | Splash | `web/design/source/phase1_foundations/08_splash.png` |
| `onboarding/` | Onboarding 3-Up | `web/design/source/phase2_screens/16_onboarding_3up.png` |
| `login/` | Login | `web/design/source/phase2_screens/14_login.png` |
| `home/` | Home | `web/design/source/phase2_screens/09_home.png` |
| `chat_light/` | Chat Light | `web/design/source/phase2_screens/10_chat_light.png` |
| `chat_dark/` | Chat Dark | `web/design/source/phase2_screens/11_chat_dark.png` |
| `character_selector/` | Character | `web/design/source/phase2_screens/12_character.png` |
| `settings/` | Settings | `web/design/source/phase2_screens/13_settings.png` |
| `redeem/` | Redeem | `web/design/source/phase2_screens/15_redeem.png` |

## 必读顺序

AI Coding 在开始实现前，必须先读取：

1. `docs/ui_specs/README.md`
2. `docs/ui_specs/00_global_rules.md`
3. `docs/ui_specs/01_asset_mapping.md`
4. `docs/ui_specs/03_layout_constraints.md`
5. `docs/ui_specs/04_visual_constraints.md`
6. `docs/ui_specs/05_motion_specification.md`
7. `docs/ui_specs/06_state_machines.md`
8. `docs/ui_specs/07_navigation_flow.md`
9. `docs/ui_specs/08_ai_coding_rules.md`
10. 对应页面目录下全部文档，至少要读该页面的 `01_overview.md`、`02_layout.md`、`05_assets.md`、`10_acceptance.md`

## 资源来源限制

- 视觉参考只允许来自：
  - `/Users/wanglixun/heart/web/design/source`
  - `/Users/wanglixun/heart/assets/backgrounds`
  - `/Users/wanglixun/heart/assets/characters`
- 严禁 AI 自行寻找资源
- 严禁 AI 重新生成资源
- 严禁用 CSS 重画已存在的复杂资源

## 工程结果要求

- 输出必须是可运行的 React + Tailwind 工程实现
- 但实现过程必须忠实于本目录规范，而不是“理解后自由发挥”
- 页面、组件、状态流、动效、路由、主题切换都必须以本目录为准
