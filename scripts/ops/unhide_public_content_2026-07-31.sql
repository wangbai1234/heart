-- ops: 回滚 hide_public_content_2026-07-31.sql — 重新上架被下架的内置角色 + 剧情
-- 2026-07-31 — 从快照表精确还原原始值（只还原当初被本脚本改动的行）。
-- 违禁词限制做好后执行。执行后可自行 DROP 两张 _hide_snapshot_* 表。
BEGIN;

-- 还原内置角色 visibility（只还原快照里记录的那些）
UPDATE characters c
SET visibility = s.prev_visibility
FROM _hide_snapshot_characters s
WHERE c.id = s.id;

-- 还原剧情 status
UPDATE story_scenarios ss
SET status = s.prev_status, updated_at = NOW()
FROM _hide_snapshot_scenarios s
WHERE ss.id = s.id;

-- 结果核对
SELECT 'restored_builtin_characters' AS what, count(*) FROM _hide_snapshot_characters
UNION ALL
SELECT 'restored_scenarios', count(*) FROM _hide_snapshot_scenarios;

COMMIT;

-- 上架完成后清理快照表（手动确认后执行）：
-- DROP TABLE IF EXISTS _hide_snapshot_characters;
-- DROP TABLE IF EXISTS _hide_snapshot_scenarios;
