# Sonnet 执行手册 — F 系列（简单批）

> **背景**：真机复测（`docs/TEST_REPORT_20260712.md`）后剩余 bug。
> **分工**：本手册 F1–F6 由 Sonnet 独立执行；H 系列由 Opus 完成，不在本手册。
>
> **执行铁律**（源自 `.claude/CLAUDE.md`）：
>
> 1. 每个 F-x 一个独立 PR，base=main，标题写 `fix: xxx (F-x)`
> 2. 单人 open PR ≤ 3，同一时刻最多 3 个 F-x 并行推
> 3. 修改前 `git ls-tree` / Read 验证现状，不凭 commit message 推断
> 4. 每 PR 都必须包含单测/回归测；`bash scripts/ci.sh` 全绿再 push
> 5. **合并即删分支**，`--squash --delete-branch`
> 6. 用户已授权自动合并：CI 绿即 squash-merge，无需询问
> 7. 提交后运行 `git checkout main && git pull --ff-only` 再开下一个
>
> **顺序建议**：F1 → F2 → F3 → F4 → F5 → F6（互相独立，也可并行 3 个）。

---

## F-1 半角括号 `｢｣` 拆分回归修复（BUG-4，P2）

**根因**：`backend/heart/ss05_composer/message_splitter.py:293` 的 `corner_quote_depth` 只统计全角 `「」` (U+300C/U+300D)，不统计 Windows IME 半角 `｢｣` (U+FF62/U+FF63)。LLM 输出 `｢今晚别走。我们聊聊。｣` 时，`。` 在 depth=0 被拆到独立气泡。

### 改动清单

**File 1**：`backend/heart/ss05_composer/message_splitter.py`

在 `_split_by_terminators` 的 depth 累加行（约 line 293）改为同时统计半角：

```python
# was:
corner_quote_depth += part.count("「") - part.count("」")
# now:
corner_quote_depth += (
    part.count("「") + part.count("｢")
    - part.count("」") - part.count("｣")
)
```

**File 2**：`backend/tests/unit/ss05_composer/test_message_splitter.py`

追加两个测试：

```python
def test_halfwidth_corner_quote_stays_atomic():
    """半角 ｢｣ 也应被视为原子引号，内部句号不触发拆分。"""
    result = split_response("｢今晚别走。我们聊聊。｣")
    assert result == [{"kind": "text", "content": "｢今晚别走。我们聊聊。｣"}]


def test_halfwidth_corner_quote_mixed_with_fullwidth():
    """全角与半角混用（罕见但可能）也不能出现负深度或孤儿。"""
    result = split_response("「外层。｢内层。｣」")
    # 全部保留在一条气泡内
    assert len(result) == 1
    assert result[0]["kind"] == "text"
    assert "内层" in result[0]["content"] and "外层" in result[0]["content"]
```

### 验收

```bash
cd backend
pytest tests/unit/ss05_composer/test_message_splitter.py -v -k corner_quote
```

3 个原有 `corner_quote_*` 测试 + 2 个新测试全绿。

---

## F-2 消息 unmount 时也标已读（Bug 6.2，P1）

**根因**：`web/src/components/ConversationChatPage.tsx:101-114` 只监听 `pagehide` + `visibilitychange`——但用户在 SPA 内 navigate 回 `/chat` 或 `/home` 时**不触发**这两个事件（它们是 tab 层面的）。所以"聊完退出 → 列表仍未读"，必须再进一次才生效。

### 改动

**File**：`web/src/components/ConversationChatPage.tsx`

在 mount-time `useEffect` (line 77–82) **同一 effect 的 cleanup** 里追加 mark-read。cleanup 里的 `currentCharacterId` 是当次 mount 的值（闭包），正好是要标已读的那个角色：

```tsx
// Mark character read on mount + unmount: clears the unread badge for this
// character on entry AND when leaving via in-app navigation (SPA navigate
// doesn't fire visibilitychange/pagehide — those are tab-level events).
useEffect(() => {
  if (!isAuthenticated()) return
  markCharacterRead(currentCharacterId).catch(() => {})
  setInboxUnreadTotal(0)
  return () => {
    // Fire-and-forget; response ignored (component is unmounting).
    markCharacterRead(currentCharacterId).catch(() => {})
  }
}, [currentCharacterId, isAuthenticated, setInboxUnreadTotal])
```

### 验收（真机 Chrome）

1. `/chat` 列表某角色显示红点 N
2. 点进去，等两三条消息渲染
3. 点右上角/物理返回按钮回到 `/chat`
4. **该行红点消失，不需要再进一次**

单测暂不加（React unmount cleanup 单测成本高、价值低）。若后续退化再补 Playwright e2e。

---

## F-3 桌面端删除按钮补丁（BUG-3，P2）

**根因**：`web/src/pages/ChatInboxPage.tsx` 的 `SwipeableRow` 只挂了 `onTouch*` 事件（line 74–76），**桌面鼠标不触发**，用户看不到删除按钮，只能整行点击进入聊天。

### 修复方向（二选一，推荐 A）

**方案 A**：给每一行加一个"⋯"按钮（桌面 & 移动端都可见），点击后调用 `setDeleteTarget(cid)`，弹现有 Dialog。

**方案 B**：`SwipeableRow` 加 `onMouseDown/Move/Up` 事件平行分支，让桌面也能拖出侧滑按钮。

推荐 **A**，理由：一致性、桌面右键菜单成本更高、方案 B 在桌面上体验诡异（拖着行走）。

### 改动（方案 A）

**File**：`web/src/pages/ChatInboxPage.tsx`

在每个会话行的**右侧** timestamp 旁边加一个 `MoreIcon` 按钮：

```tsx
<button
  aria-label="更多操作"
  onClick={(e) => {
    e.stopPropagation()  // 不触发行 click → 不跳聊天
    setDeleteTarget(characterId)
  }}
  className="ml-2 flex h-8 w-8 items-center justify-center rounded-full opacity-60 hover:opacity-100 hover:bg-[var(--color-glass-25)]"
>
  <span className="text-lg leading-none">⋯</span>
</button>
```

嵌入位置：找到渲染时间戳/未读数的那个 `<div>` 块（通常在 conversation.name / lastText 后面），追加此按钮。**保留原有 SwipeableRow**，两条路径并存（移动端左滑仍用侧滑，桌面点⋯直接弹确认框）。

### 验收

- 桌面 Chrome：会话行右边有 `⋯`，点它弹出 `确认删除聊天记录？` 对话框；确认后行消失
- 手机 Safari：左滑仍露出红色"删除"，⋯ 也可点击
- 不影响整行 click 进入聊天

---

## F-4 Toast 时长延长 + 断网/失败类持久（4.6，P2）

**根因**：`web/src/components/ui/Toast.tsx:26` 硬编码 `setTimeout(onDismiss, 2200)`——2.2 秒对断网、语音超时、克隆失败这类信息量大的错误 toast 太短，用户还没读完就消失。

### 改动

**File**：`web/src/components/ui/Toast.tsx`

按 variant 分档时长：

```tsx
const DURATION_BY_VARIANT: Record<ToastVariant, number> = {
  info: 2200,
  success: 2200,
  error: 4500,  // 错误类：让用户有时间读完 + 看清操作
}

useEffect(() => {
  if (visible && onDismiss) {
    timerRef.current = setTimeout(onDismiss, DURATION_BY_VARIANT[variant])
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }
}, [visible, onDismiss, variant])
```

### 验收

- 触发一个 error toast（例如断网发消息）：可读约 4–5 秒
- 触发 info/success toast：仍 2 秒左右消失（原有节奏）

无单测（timer 单测不稳定），手动验收。

---

## F-5 主动消息每日 3 条硬限额（BUG-6，P1）

**根因**：`backend/heart/ss06_inner_state/service.py:150-153` 已经写了 `count_all_today` gate + `DAILY_PROACTIVE_QUOTA = 3` 判断，但**只在 `db is not None` 分支生效**（tick 是否传 db 决定）。`inner_loop_worker.py:_check_ritual_triggers` 走的是 line 470，那里也已加了 gate；但**bulk 触发器** 或历史存量已经超过 3 条。

问题实际发生的路径需 grep 补一次：

```bash
rg -n "proactive.*sent|_send_proactive|insert_proactive|create_proactive" backend/heart/ss06_inner_state
```

### 改动

**Step 1**：审计每个 proactive-send 调用点，确保**每一次真正落库前**都过 `count_all_today` gate。当前已知 gate 存在于：
- `service.py:tick()` line 150–153 ✓
- `inner_loop_worker.py:_check_ritual_triggers` line 470–471 ✓

如果存在其它 send 分支（如 `ss06_inner_state/service.py:_send_proactive_message` / activity_generator batch 触发），也必须在**写入 `proactive_messages` 表前** 加同款 gate。

**Step 2**：把 gate 提到 `proactive_repo.insert_proactive`（如存在）**内部**作为最后防线：

```python
async def insert_proactive(
    session: AsyncSession,
    user_id: uuid.UUID,
    character_id: str,
    content: str,
    trigger_type: str,
) -> uuid.UUID | None:
    """Persist a proactive message. Returns None (no-op) if the daily quota
    for (user, character) is already exhausted — defense-in-depth against any
    upstream call site that forgot to gate.
    """
    sent_today = await count_all_today(session, user_id, character_id)
    if sent_today >= 3:  # DAILY_PROACTIVE_QUOTA
        logger.warning(
            "proactive_quota_exceeded_at_repo",
            user_id=str(user_id), character_id=character_id, sent_today=sent_today,
        )
        return None
    # ... existing insert
```

**Step 3**：`proactive_messages` 表加 `PARTIAL UNIQUE INDEX` 兜底 —— 同一 (user_id, character_id, DATE(created_at)) 每天最多 3 行：不好用唯一索引直接卡上限，改成加 **CHECK constraint**（PostgreSQL 12+ 支持 partial + generated column），或不做（Step 1+2 足够）。**推荐跳过 Step 3**，只做 1+2。

**Step 4**：清理历史积压（数据修复，**独立 SQL 脚本，不进代码库**）：

```sql
-- 手动执行，dev DB 里删掉今日已超量的重复主动消息
-- Sonnet 不要写进 migration，交给运维手动执行
DELETE FROM proactive_messages
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (
      PARTITION BY user_id, character_id, DATE(created_at AT TIME ZONE 'UTC')
      ORDER BY created_at
    ) AS rn
    FROM proactive_messages
    WHERE created_at >= NOW() - interval '7 days'
  ) t
  WHERE rn > 3
);
```

### 单测

`backend/tests/unit/test_proactive_ritual_dedup.py`（已存在）追加：

```python
def test_repo_insert_refuses_over_quota(monkeypatch):
    """proactive_repo.insert_proactive 在 sent_today >= 3 时返回 None，不落库。"""
    # mock count_all_today → 3
    # 调用 insert_proactive
    # assert 返回 None + insert SQL 未执行
```

### 验收

- 手动 stub `count_all_today = 3` 后 tick 一轮：不出现新的 proactive_messages 行，日志有 `proactive_quota_exceeded` warning
- rg `insert_proactive|_send_proactive` 全站，每个 call site 都能看到 gate 或走 repo 内部 gate

---

## F-6 桌面手势鼠标事件支持（可选，§7 移动端优先则跳过）

**背景**：用户 §7 报"手势功能异常"——因为在 chrome **桌面** 上测的，`useSwipeNavigation` 只监听 `touchstart/touchmove/touchend`，桌面鼠标无事件。**移动端 PWA 是主要目标**，桌面手势不属于 launch 关键路径。

### 决策

**推荐跳过 F-6**，在 `docs/PROJECT_STATUS.md` 增加一行"桌面浏览器不支持左边缘右滑手势（by design，PWA 主设备是手机）"，避免下次测试重复报同一 bug。

如果决定要做（后续版本）：在 `useSwipeNavigation.ts` 平行加 `mousedown/mousemove/mouseup` 分支，事件从 `e.clientX` 取值（TouchEvent 换成 MouseEvent），threshold 提到 100（鼠标操作更精准）。

**Sonnet 本轮：只更新 PROJECT_STATUS.md，不改代码。**

---

## 提交模板

每个 F-x 的 PR 描述：

```markdown
## 关联

- 手册：`docs/SONNET_F_SERIES_20260712.md` §F-x
- 报告：`docs/TEST_REPORT_20260712.md` 第 X 章

## 改动

- <一句话>

## 验证

- [x] `bash scripts/ci.sh`
- [x] 手动/真机验收步骤（复制手册的验收段）
- [x] rg 全站 grep 未见旧模式

🤖 Generated with Claude Code (Sonnet)
```

---

## 结束

F-1..F-5 完成后回来通知 Opus 汇总。F-6 若选跳过，只需一个 docs-only 提交。
