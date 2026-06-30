# 06 State Machine — 页面状态流

以下状态机是业务页面强约束。若某状态未触发，也必须在工程中可被正确处理。

## 1. Splash

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | App 冷启动 | 启动资源就绪 | 全屏静态图淡入 |
| Loaded | 启动资源已就绪 | 计时结束或鉴权完成 | 保持显示 |
| Error | 启动资源加载失败 | 降级到纯色启动页 | `180ms` fade |
| Transition | 准备跳往 Onboarding / Login | 新页面 mount 完成 | `320ms` fade out |
| Dialog | 不使用 | — | — |
| Toast | 不使用 | — | — |
| BottomSheet | 不使用 | — | — |
| Empty | 不使用 | — | — |
| Offline | 不使用 | — | — |

## 2. Onboarding

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 首次进入 | 三张引导资源就绪 | `240ms` fade |
| Loaded | 当前步骤 ready | 点击下一步 / 开始体验 | 插画静态，按钮可交互 |
| Empty | 不使用 | — | — |
| Offline | 不使用 | — | — |
| Error | 某张引导图加载失败 | 回退到纯文案降级态 | `180ms` fade |
| Transition | 页间切换 | 新 step 就绪 | `280ms` horizontal slide |
| Dialog | 不使用 | — | — |
| Toast | 可用于“资源加载失败，已降级” | 自动消失 | `220ms` |
| BottomSheet | 不使用 | — | — |

## 3. Login

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 页面 mount | Hero 图和表单 ready | `240ms` fade |
| Loaded | 默认进入 | 提交邮箱 / 跳转 Redeem | Hero 静态，表单可交互 |
| Empty | 邮箱为空 | 用户输入内容 | 无额外动画 |
| Offline | 网络不可用 | 网络恢复 | Toast + 禁用提交 |
| Error | 邮箱格式错误 / 发送失败 | 用户修改输入或重试 | 错误文案 `180ms` fade |
| Transition | 跳转 Home / Redeem | 新页就绪 | `300ms` fade + up |
| Dialog | 法务链接可选弹出 WebView | 关闭 | `280ms` |
| Toast | 登录链接已发送 / 发送失败 | 自动消失 | `220ms` |
| BottomSheet | 不使用 | — | — |

## 4. Home

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 登录后首次进入 / 刷新 | 首屏数据就绪 | `240ms` fade |
| Loaded | 数据齐全 | 进入其他页面或刷新失败 | Hero / 列表展示 |
| Empty | 最近对话为空 | 有会话数据返回 | 空列表淡入 |
| Offline | 网络断开 | 网络恢复 | 顶部或列表内离线提示 |
| Error | 首页数据失败 | 重试成功 | `180ms` fade |
| Transition | 跳 Chat / Character / Settings / Redeem | 新页 mount | `300ms` push |
| Dialog | 可用于退出登录确认 | 关闭 | `280ms` |
| Toast | 操作反馈 | 自动消失 | `220ms` |
| BottomSheet | 可用于快捷操作二级菜单 | 收起 | `360ms` |

## 5. Chat Light

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 会话进入 | 历史消息 ready | `240ms` fade |
| Loaded | 消息可展示 | 会话关闭 / 错误 | 气泡依序进入 |
| Empty | 新会话无历史 | 用户发送首条消息 | 欢迎态淡入 |
| Offline | 网络断开 | 网络恢复 | Composer 禁发，显示离线提示 |
| Error | 发消息失败 / 拉历史失败 | 重试成功 | 失败标记 `180ms` |
| Transition | 从 Home push 进来 / pop 返回 | 转场完成 | `300ms` push / pop |
| Dialog | 长按消息操作可选 | 关闭 | `280ms` |
| Toast | 已复制 / 发送失败 / 已重试 | 自动消失 | `220ms` |
| BottomSheet | 更多操作 / 附件面板 | 收起 | `360ms` |

## 6. Chat Dark

与 Chat Light 完全相同，只允许替换为深色背景和深色玻璃层。

## 7. Character

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 页面进入 | Banner 和角色数据 ready | `240ms` fade |
| Loaded | 角色列表可交互 | 确认选择 / 返回 | 选中态即时反馈 |
| Empty | 角色列表为空 | 数据返回 | 空列表淡入 |
| Offline | 网络断开 | 网络恢复 | 禁用确认按钮 |
| Error | 列表拉取失败 | 重试成功 | `180ms` fade |
| Transition | 返回 / 进入 Chat | 新页 ready | `300ms` push/pop |
| Dialog | 切换角色确认可选 | 关闭 | `280ms` |
| Toast | 选择成功 / 失败 | 自动消失 | `220ms` |
| BottomSheet | 不使用 | — | — |

## 8. Settings

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 页面进入 | 配置数据 ready | `240ms` fade |
| Loaded | 默认 | 跳转子页面 / 提交配置 | 组件即时反馈 |
| Empty | 某 section 无数据 | 数据到达 | 空 section 提示 |
| Offline | 网络断开 | 网络恢复 | 某些远程设置只读 |
| Error | 保存失败 / 拉取失败 | 重试成功 | `180ms` fade |
| Transition | Push 进入 / 返回 | 完成 | `300ms` push/pop |
| Dialog | 清除数据 / 注销确认 | 关闭 | `280ms` |
| Toast | 保存成功 / 失败 | 自动消失 | `220ms` |
| BottomSheet | 主题选择、静音时段可选 | 收起 | `360ms` |

## 9. Redeem

| 状态 | 进入条件 | 退出条件 | 动画 |
|---|---|---|---|
| Loading | 页面进入 | 背景和表单 ready | `240ms` fade |
| Loaded | 默认 | 提交成功 / 返回 | 卡片静态 |
| Empty | 兑换码未填满 | 输入完成 | 无额外动画 |
| Offline | 网络断开 | 网络恢复 | 提交按钮禁用 |
| Error | 校验失败 / 激活失败 | 修改输入或重试 | 输入框抖动 `180ms` |
| Transition | 登录页进入 / 返回 | 完成 | `300ms` push/pop |
| Dialog | 激活成功确认可选 | 关闭 | `280ms` |
| Toast | 粘贴成功 / 激活失败 | 自动消失 | `220ms` |
| BottomSheet | 不使用 | — | — |
