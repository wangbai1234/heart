# 前端导航重构：删首页 + 底部创作中心 + 公告迁移

## 目标
1. 删除 `/home` 首页（无实质功能，只有公告展示）
2. 登录后默认落地角色页
3. 底部导航中间放醒目的「创作」凸起按钮（nimoo 风格，yuoyuo 樱花粉调）→ 进「创作中心页」
4. 角色页右上角：隐藏 `+` 新建按钮，改放**公告按钮**（nimoo 风格）
5. 角色页右上角 `我的角色` 文字按钮删除（内容并入创作中心页）
6. 「我的创造」= 原 `我的角色` 列表，放进创作中心页

## 最终底部 Tab
`角色 · 探索 · ⊕创作(凸起) · 消息 · 设置`

## 改动清单

### 1. TabBar.tsx — 重构为 5 槽含中间凸起按钮
- 删除 `home` tab
- 新顺序：角色 / 探索 / **[创作凸起按钮]** / 消息 / 设置
- 中间 `创作` 按钮：圆形凸起（`-translate-y` 上浮），樱花粉渐变 `#FFB7C5→#FF8FAB`，白色 `+` 图标，柔和投影 `shadow-[0_8px_20px_-4px_rgba(255,143,171,.45)]`，`active:scale-90`。label「创作」。点击 `navigate('/create')`
- 左右各 2 个普通 tab，中间按钮用绝对定位或 flex 居中上浮，其余 tab 正常高度

### 2. 新增 CreateHubPage（创作中心页，路由 /create）
- 复用 MyCharactersPage 的玻璃卡样式 + ExplorePage/CharacterPage 顶栏 safe-top 结构
- 顶栏标题「创作中心」
- 顶部大号主 CTA「+ 创建新角色」（渐变按钮，样式同 MyCharactersPage 底部创建按钮），达上限(5)禁用并提示
- 下方「我的创造 (n/5)」区块 = 把 MyCharactersPage 的 CharacterCard 列表 + 编辑/可见范围/停用菜单整体搬进来
- 空态复用 MyCharactersPage 的 EmptyState
- 底部挂 TabBar（属于主 tab 页）

### 3. MyCharactersPage.tsx — 处置
- 逻辑与 CharacterCard 迁入 CreateHubPage；`/my-characters` 路由保留做重定向到 `/create`（老书签/last-route 兼容），或直接删路由+加兜底重定向。选：保留 CharacterCard/菜单组件抽出复用，页面壳删除

### 4. CharacterPage.tsx — 右上角改造
- 删除 `我的角色` 文字按钮
- 删除 `+` 新建按钮
- 新增**公告按钮**（铃铛图标圆形玻璃按钮，nimoo 风格），点击打开公告 BottomSheet/Modal
- 保留搜索按钮
- 顶栏左侧返回按钮 `navigate('/home')` → 角色页是主 tab，返回按钮本就多余，改为不显示或跳 `/character`（评估：角色页作为落地页，左上返回箭头应移除）

### 5. 公告迁移
- 新增 `AnnouncementSheet` 组件（抽自 HomePage 的公告列表 + 详情弹窗逻辑），读 `HOME_ANNOUNCEMENTS`
- 由 CharacterPage 公告按钮触发

### 6. 删除 HomePage + 清理 /home 死链
- 删 `src/pages/HomePage.tsx`
- `App.tsx`：删 HomePage import；`/home` route 改为 `<Navigate to="/character" replace />`（兼容老 last-route）；`NotFoundRedirect` 的 `/home`→`/character`
- `LoginPage.tsx`：`pendingDest` 默认值 + line 298 `/home`→`/character`
- `ForgotPasswordPage.tsx` line 94：`/home`→`/character`
- `ProfileEditPage.tsx` line 74：`/home`→`/character`
- `useSwipeNavigation.ts`：默认 fallback `/home`→`/character`
- `ConversationChatPage.tsx` line 77：右滑 `/home`→`/character`（或按会话来源，保守用 /character）
- `useSafeBack('/home')` 各处（Settings/Invite/CreateCharacter/MyCharacters）→ `/character`
- `main.tsx` 注释提及 /home，无需改代码

### 7. last-route 兼容
- SplashPage 已跳 `/character`（无需改）
- `/home` route 保留为重定向兜住存量用户 localStorage 里的 `yuoyuo-last-route=/home`
- App.tsx `SKIP_SAVE_ROUTES` 加 `/create`？—— /create 是主 tab 可作为 last-route，**不加**，允许恢复

## 验证
- `cd web && npm run build`（tsc + vite）确保无类型错误 / 死 import
- `npm run lint`
- 手动过一遍：登录→落地角色页；点中间创作→创作中心页；创建/编辑/可见范围/停用；角色页公告按钮→公告弹窗；老 `/home`、`/my-characters` 重定向不白屏
- 全程无 emoji（CLAUDE.md UI 铁律）

## 风险 / 注意
- 中间凸起按钮在 TabBar 圆角容器里的定位：容器 `overflow` 需允许上浮（当前无 overflow-hidden，OK）
- 达角色上限 5 时创作按钮/CTA 的禁用态提示
- 不动后端、不动 DB、不涉及迁移 —— 纯前端

## 提交
小步：可拆 2 个 commit（导航重构 / 公告迁移）或 1 个 feat commit。走当前分支 `feat/age-confirm-ai-banner`？还是新开 `feat/create-hub-nav`？建议新开分支走 PR。
