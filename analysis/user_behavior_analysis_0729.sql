-- ============================================
-- Yuoyuo 用户行为分析脚本
-- 分析日期: 2026年7月29日
-- ============================================

-- ============================================
-- 一、核心数据摘要
-- ============================================

-- 1. 新注册用户数（按日期）
SELECT 
  DATE(created_at AT TIME ZONE 'Asia/Shanghai') as reg_date,
  COUNT(*) as new_users
FROM users 
WHERE created_at >= '2026-07-29 00:00:00' 
  AND created_at < '2026-07-30 00:00:00'
  AND status = 'active'
GROUP BY reg_date;

-- 2. 登录用户情况（DAU）- 7月29日
WITH 
-- 7月29日注册用户
reg_29 AS (
  SELECT id FROM users 
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
),
-- 7月28日注册用户
reg_28 AS (
  SELECT id FROM users 
  WHERE created_at >= '2026-07-28 00:00:00' 
    AND created_at < '2026-07-29 00:00:00'
),
-- 7月29日登录用户
login_29 AS (
  SELECT DISTINCT user_id 
  FROM sessions 
  WHERE last_activity_at >= '2026-07-29 00:00:00' 
    AND last_activity_at < '2026-07-30 00:00:00'
)
SELECT 
  '2026-07-29' as date,
  (SELECT COUNT(*) FROM reg_29) as new_registered_users,
  (SELECT COUNT(*) FROM login_29) as dau,
  (SELECT COUNT(*) FROM login_29 l JOIN reg_29 r ON l.user_id = r.id) as new_user_logins,
  (SELECT COUNT(*) FROM login_29 l JOIN reg_28 r ON l.user_id = r.id) as returning_users,
  CASE 
    WHEN (SELECT COUNT(*) FROM login_29) > 0 
    THEN ROUND((SELECT COUNT(*) FROM login_29 l JOIN reg_28 r ON l.user_id = r.id)::decimal / 
         (SELECT COUNT(*) FROM login_29) * 100, 2)
    ELSE 0 
  END as return_rate_pct;

-- ============================================
-- 二、用户活跃行为分析（漏斗）
-- ============================================

WITH 
-- 7月29日注册用户
new_users AS (
  SELECT id FROM users 
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
),
-- 登录用户（7月29日有会话活动）
logged_in AS (
  SELECT DISTINCT user_id 
  FROM sessions 
  WHERE last_activity_at >= '2026-07-29 00:00:00' 
    AND last_activity_at < '2026-07-30 00:00:00'
),
-- 创建角色用户
created_character AS (
  SELECT DISTINCT user_id FROM user_character_settings
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
),
-- 进入剧情用户
entered_story AS (
  SELECT DISTINCT user_id FROM story_runs
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
),
-- 开始聊天用户
started_chat AS (
  SELECT DISTINCT user_id FROM chat_messages
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
),
-- 完成第一次聊天用户（至少2条消息）
completed_first_chat AS (
  SELECT user_id 
  FROM chat_messages
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
  GROUP BY user_id
  HAVING COUNT(*) >= 2
),
-- 二次进入聊天用户（当天内再次聊天）
returned_chat AS (
  SELECT DISTINCT user_id FROM chat_messages
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
    AND user_id IN (
      SELECT user_id FROM chat_messages 
      WHERE created_at < '2026-07-29 00:00:00'
    )
)
SELECT 
  '注册' as stage,
  (SELECT COUNT(*) FROM new_users) as user_count,
  100.0 as percentage
UNION ALL
SELECT 
  '登录' as stage,
  (SELECT COUNT(*) FROM logged_in) as user_count,
  ROUND((SELECT COUNT(*) FROM logged_in)::decimal / NULLIF((SELECT COUNT(*) FROM new_users), 0) * 100, 2)
UNION ALL
SELECT 
  '进入剧情' as stage,
  (SELECT COUNT(*) FROM entered_story) as user_count,
  ROUND((SELECT COUNT(*) FROM entered_story)::decimal / NULLIF((SELECT COUNT(*) FROM new_users), 0) * 100, 2)
UNION ALL
SELECT 
  '开始聊天' as stage,
  (SELECT COUNT(*) FROM started_chat) as user_count,
  ROUND((SELECT COUNT(*) FROM started_chat)::decimal / NULLIF((SELECT COUNT(*) FROM new_users), 0) * 100, 2)
UNION ALL
SELECT 
  '完成第一次聊天' as stage,
  (SELECT COUNT(*) FROM completed_first_chat) as user_count,
  ROUND((SELECT COUNT(*) FROM completed_first_chat)::decimal / NULLIF((SELECT COUNT(*) FROM new_users), 0) * 100, 2)
UNION ALL
SELECT 
  '二次进入聊天' as stage,
  (SELECT COUNT(*) FROM returned_chat) as user_count,
  ROUND((SELECT COUNT(*) FROM returned_chat)::decimal / NULLIF((SELECT COUNT(*) FROM new_users), 0) * 100, 2);

-- ============================================
-- 三、剧情消费分析
-- ============================================

-- 所有剧情使用情况（7月29日）
WITH story_stats AS (
  SELECT 
    ss.id as scenario_id,
    ss.title as story_name,
    ss.genre,
    COUNT(DISTINCT sr.user_id) as unique_users,
    COUNT(*) as total_runs,
    COUNT(DISTINCT sr.user_id) FILTER (WHERE sr.turn_count > 0) as chat_users,
    COALESCE(SUM(sr.turn_count), 0) as total_messages,
    CASE 
      WHEN COUNT(DISTINCT sr.user_id) > 0 
      THEN ROUND(COUNT(*)::decimal / COUNT(DISTINCT sr.user_id), 2)
      ELSE 0 
    END as avg_runs_per_user
  FROM story_runs sr
  JOIN story_scenarios ss ON sr.scenario_id = ss.id
  WHERE sr.created_at >= '2026-07-29 00:00:00' 
    AND sr.created_at < '2026-07-30 00:00:00'
  GROUP BY ss.id, ss.title, ss.genre
)
SELECT 
  RANK() OVER (ORDER BY unique_users DESC) as rank_by_users,
  story_name,
  genre,
  unique_users as 使用人数,
  total_runs as 进入次数,
  chat_users as 聊天人数,
  total_messages as 聊天消息数,
  ROUND(total_messages::decimal / NULLIF(chat_users, 0), 2) as 平均聊天次数,
  total_runs - unique_users as 复玩人数
FROM story_stats
ORDER BY unique_users DESC
LIMIT 20;

-- ============================================
-- 四、角色偏好分析
-- ============================================

WITH character_stats AS (
  SELECT 
    c.id as character_id,
    c.id as character_name,
    COUNT(DISTINCT cm.user_id) as chat_users,
    COUNT(*) as total_messages,
    CASE 
      WHEN COUNT(DISTINCT cm.user_id) > 0 
      THEN ROUND(COUNT(*)::decimal / COUNT(DISTINCT cm.user_id), 2)
      ELSE 0 
    END as avg_messages_per_user,
    COUNT(DISTINCT cm.user_id) FILTER (
      WHERE cm.user_id IN (
        SELECT user_id FROM chat_messages 
        WHERE created_at < '2026-07-29 00:00:00'
      )
    ) as returning_users
  FROM chat_messages cm
  JOIN characters c ON cm.character_id = c.id
  WHERE cm.created_at >= '2026-07-29 00:00:00' 
    AND cm.created_at < '2026-07-30 00:00:00'
  GROUP BY c.id
)
SELECT 
  RANK() OVER (ORDER BY chat_users DESC) as rank,
  character_name,
  chat_users as 聊天用户数,
  total_messages as 聊天次数,
  avg_messages_per_user as 平均每用户聊天次数,
  returning_users as 复访人数,
  ROUND(returning_users::decimal / NULLIF(chat_users, 0) * 100, 2) as 复访率
FROM character_stats
ORDER BY chat_users DESC
LIMIT 20;

-- ============================================
-- 五、用户复访/留存分析
-- ============================================

-- 7月28日注册用户的次日留存（7月29日回访）
WITH reg_28 AS (
  SELECT id, created_at FROM users 
  WHERE created_at >= '2026-07-28 00:00:00' 
    AND created_at < '2026-07-29 00:00:00'
),
login_28 AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-28 00:00:00' 
    AND last_activity_at < '2026-07-29 00:00:00'
),
login_29 AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-29 00:00:00' 
    AND last_activity_at < '2026-07-30 00:00:00'
)
SELECT 
  '2026-07-28' as registration_date,
  (SELECT COUNT(*) FROM reg_28) as new_users,
  (SELECT COUNT(*) FROM login_28 WHERE user_id IN (SELECT id FROM reg_28)) as day0_logins,
  (SELECT COUNT(*) FROM login_29 WHERE user_id IN (SELECT id FROM reg_28)) as day1_returns,
  CASE 
    WHEN (SELECT COUNT(*) FROM login_28 WHERE user_id IN (SELECT id FROM reg_28)) > 0 
    THEN ROUND(
      (SELECT COUNT(*) FROM login_29 WHERE user_id IN (SELECT id FROM reg_28))::decimal / 
      (SELECT COUNT(*) FROM login_28 WHERE user_id IN (SELECT id FROM reg_28)) * 100, 2
    )
    ELSE 0 
  END as retention_rate_pct;

-- 7月29日新用户激活情况
WITH reg_29 AS (
  SELECT id, created_at FROM users 
  WHERE created_at >= '2026-07-29 00:00:00' 
    AND created_at < '2026-07-30 00:00:00'
),
login_29 AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-29 00:00:00' 
    AND last_activity_at < '2026-07-30 00:00:00'
)
SELECT 
  '2026-07-29' as registration_date,
  (SELECT COUNT(*) FROM reg_29) as new_users,
  (SELECT COUNT(*) FROM login_29 WHERE user_id IN (SELECT id FROM reg_29)) as activated_users,
  CASE 
    WHEN (SELECT COUNT(*) FROM reg_29) > 0 
    THEN ROUND(
      (SELECT COUNT(*) FROM login_29 WHERE user_id IN (SELECT id FROM reg_29))::decimal / 
      (SELECT COUNT(*) FROM reg_29) * 100, 2
    )
    ELSE 0 
  END as activation_rate_pct;

-- ============================================
-- 六、聊天时间分布
-- ============================================

-- 按小时统计聊天分布（7月29日）
SELECT 
  EXTRACT(HOUR FROM created_at AT TIME ZONE 'Asia/Shanghai') as hour_of_day,
  COUNT(*) as message_count,
  COUNT(DISTINCT user_id) as unique_users
FROM chat_messages
WHERE created_at >= '2026-07-29 00:00:00' 
  AND created_at < '2026-07-30 00:00:00'
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- ============================================
-- 七、聊天消息总量统计
-- ============================================

-- 7月29日聊天消息总量
SELECT 
  COUNT(*) as total_messages,
  COUNT(DISTINCT user_id) as unique_users
FROM chat_messages
WHERE created_at >= '2026-07-29 00:00:00' 
  AND created_at < '2026-07-30 00:00:00';

-- ============================================
-- 八、剧情进入统计
-- ============================================

-- 7月29日剧情进入情况
SELECT 
  COUNT(*) as total_story_runs,
  COUNT(DISTINCT user_id) as unique_users
FROM story_runs
WHERE created_at >= '2026-07-29 00:00:00' 
  AND created_at < '2026-07-30 00:00:00';
