-- ops: 暂时下架所有官方内置角色 + 所有剧情（等违禁词限制做好后再上架）
-- 2026-07-31 — 可逆：先快照受影响 ID，再翻转 visibility/status。
-- 回滚见 scripts/ops/unhide_public_content_2026-07-31.sql
-- 保留：用户自建 UGC 角色（owner_user_id 非空）完全不动。
BEGIN;

-- 快照表（幂等）：记录翻转前的原始值，供精确回滚。
CREATE TABLE IF NOT EXISTS _hide_snapshot_characters (
    id TEXT PRIMARY KEY,
    prev_visibility TEXT NOT NULL,
    hidden_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS _hide_snapshot_scenarios (
    id UUID PRIMARY KEY,
    prev_status TEXT NOT NULL,
    hidden_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 记录当前 public 的内置角色（owner_user_id IS NULL = 系统内置）
INSERT INTO _hide_snapshot_characters (id, prev_visibility)
SELECT id, visibility FROM characters
WHERE owner_user_id IS NULL AND visibility = 'public'
ON CONFLICT (id) DO NOTHING;

-- 记录当前 published 的剧情
INSERT INTO _hide_snapshot_scenarios (id, prev_status)
SELECT id, status FROM story_scenarios
WHERE status = 'published'
ON CONFLICT (id) DO NOTHING;

-- 翻转：内置角色 public -> private（无 owner，故对所有人不可见；UGC 不受影响）
UPDATE characters SET visibility = 'private'
WHERE owner_user_id IS NULL AND visibility = 'public';

-- 翻转：所有剧情 published -> archived（browse 只展示 published）
UPDATE story_scenarios SET status = 'archived', updated_at = NOW()
WHERE status = 'published';

-- 结果核对
SELECT 'hidden_builtin_characters' AS what, count(*) FROM _hide_snapshot_characters
UNION ALL
SELECT 'hidden_scenarios', count(*) FROM _hide_snapshot_scenarios;

COMMIT;
