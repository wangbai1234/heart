-- ============================================
-- Yuoyuo 用户行为分析脚本
-- 分析日期: 2026年7月25日 - 7月26日
-- ============================================

-- ============================================
-- 一、用户增长分析
-- ============================================

-- 1. 新注册用户数（按日期）
SELECT 
  DATE(created_at AT TIME ZONE 'Asia/Shanghai') as reg_date,
  COUNT(*) as new_users
FROM users 
WHERE created_at >= '2026-07-25 00:00:00' 
  AND created_at < '2026-07-27 00:00:00'
  AND status = 'active'
GROUP BY reg_date
ORDER BY reg_date;

-- 2. 登录用户情况（DAU）
WITH 
-- 7月25日注册用户
reg_25 AS (
  SELECT id FROM users 
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-26 00:00:00'
),
-- 7月26日注册用户
reg_26 AS (
  SELECT id FROM users 
  WHERE created_at >= '2026-07-26 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
-- 7月25日登录用户（通过last_login_at判断）
login_25 AS (
  SELECT DISTINCT user_id 
  FROM sessions 
  WHERE last_activity_at >= '2026-07-25 00:00:00' 
    AND last_activity_at < '2026-07-26 00:00:00'
),
-- 7月26日登录用户
login_26 AS (
  SELECT DISTINCT user_id 
  FROM sessions 
  WHERE last_activity_at >= '2026-07-26 00:00:00' 
    AND last_activity_at < '2026-07-27 00:00:00'
)
SELECT 
  '2026-07-25' as date,
  (SELECT COUNT(*) FROM reg_25) as registered_users,
  (SELECT COUNT(*) FROM login_25) as dau,
  (SELECT COUNT(*) FROM login_25 l JOIN reg_25 r ON l.user_id = r.id) as new_user_logins,
  (SELECT COUNT(*) FROM login_25 l JOIN reg_26 r ON l.user_id = r.id) as returning_users,
  CASE 
    WHEN (SELECT COUNT(*) FROM login_25) > 0 
    THEN ROUND((SELECT COUNT(*) FROM login_25 l JOIN reg_26 r ON l.user_id = r.id)::decimal / 
         (SELECT COUNT(*) FROM login_25) * 100, 2)
    ELSE 0 
  END as return_rate_pct

UNION ALL

SELECT 
  '2026-07-26' as date,
  (SELECT COUNT(*) FROM reg_26) as registered_users,
  (SELECT COUNT(*) FROM login_26) as dau,
  (SELECT COUNT(*) FROM login_26 l JOIN reg_26 r ON l.user_id = r.id) as new_user_logins,
  (SELECT COUNT(*) FROM login_26 l JOIN reg_25 r ON l.user_id = r.id) as returning_users,
  CASE 
    WHEN (SELECT COUNT(*) FROM login_26) > 0 
    THEN ROUND((SELECT COUNT(*) FROM login_26 l JOIN reg_25 r ON l.user_id = r.id)::decimal / 
         (SELECT COUNT(*) FROM login_26) * 100, 2)
    ELSE 0 
  END as return_rate_pct;

-- ============================================
-- 二、用户活跃行为分析（漏斗）
-- ============================================

WITH 
-- 7月25-26日注册用户
new_users AS (
  SELECT id FROM users 
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
-- 登录用户（7月25-26日有会话活动）
logged_in AS (
  SELECT DISTINCT user_id 
  FROM sessions 
  WHERE last_activity_at >= '2026-07-25 00:00:00' 
    AND last_activity_at < '2026-07-27 00:00:00'
),
-- 创建角色用户（有character_content或characters记录）
created_character AS (
  SELECT DISTINCT user_id FROM user_character_settings
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
-- 进入剧情用户
entered_story AS (
  SELECT DISTINCT user_id FROM story_runs
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
-- 开始聊天用户（有chat_messages记录）
started_chat AS (
  SELECT DISTINCT user_id FROM chat_messages
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
-- 完成第一次聊天用户（至少2条消息）
completed_first_chat AS (
  SELECT user_id 
  FROM chat_messages
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
  GROUP BY user_id
  HAVING COUNT(*) >= 2
),
-- 二次进入聊天用户（第二天再次聊天）
returned_chat AS (
  SELECT DISTINCT user_id FROM chat_messages
  WHERE created_at >= '2026-07-26 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
    AND user_id IN (SELECT user_id FROM started_chat WHERE created_at < '2026-07-26 00:00:00')
)
SELECT 
  '注册' as stage,
  (SELECT COUNT(*) FROM new_users) as user_count,
  100.0 as percentage
UNION ALL
SELECT 
  '登录' as stage,
  (SELECT COUNT(*) FROM logged_in) as user_count,
  ROUND((SELECT COUNT(*) FROM logged_in)::decimal / (SELECT COUNT(*) FROM new_users) * 100, 2)
UNION ALL
SELECT 
  '创建角色' as stage,
  (SELECT COUNT(*) FROM created_character) as user_count,
  ROUND((SELECT COUNT(*) FROM created_character)::decimal / (SELECT COUNT(*) FROM new_users) * 100, 2)
UNION ALL
SELECT 
  '进入剧情' as stage,
  (SELECT COUNT(*) FROM entered_story) as user_count,
  ROUND((SELECT COUNT(*) FROM entered_story)::decimal / (SELECT COUNT(*) FROM new_users) * 100, 2)
UNION ALL
SELECT 
  '开始聊天' as stage,
  (SELECT COUNT(*) FROM started_chat) as user_count,
  ROUND((SELECT COUNT(*) FROM started_chat)::decimal / (SELECT COUNT(*) FROM new_users) * 100, 2)
UNION ALL
SELECT 
  '完成第一次聊天' as stage,
  (SELECT COUNT(*) FROM completed_first_chat) as user_count,
  ROUND((SELECT COUNT(*) FROM completed_first_chat)::decimal / (SELECT COUNT(*) FROM new_users) * 100, 2)
UNION ALL
SELECT 
  '二次进入聊天' as stage,
  (SELECT COUNT(*) FROM returned_chat) as user_count,
  ROUND((SELECT COUNT(*) FROM returned_chat)::decimal / (SELECT COUNT(*) FROM new_users) * 100, 2);

-- ============================================
-- 三、剧情消费分析
-- ============================================

-- 所有剧情使用情况（7月25-26日）
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
  WHERE sr.created_at >= '2026-07-25 00:00:00' 
    AND sr.created_at < '2026-07-27 00:00:00'
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

-- 剧情进入次数排名
WITH story_stats AS (
  SELECT 
    ss.id as scenario_id,
    ss.title as story_name,
    ss.genre,
    COUNT(DISTINCT sr.user_id) as unique_users,
    COUNT(*) as total_runs,
    COUNT(DISTINCT sr.user_id) FILTER (WHERE sr.turn_count > 0) as chat_users,
    COALESCE(SUM(sr.turn_count), 0) as total_messages
  FROM story_runs sr
  JOIN story_scenarios ss ON sr.scenario_id = ss.id
  WHERE sr.created_at >= '2026-07-25 00:00:00' 
    AND sr.created_at < '2026-07-27 00:00:00'
  GROUP BY ss.id, ss.title, ss.genre
)
SELECT 
  RANK() OVER (ORDER BY total_runs DESC) as rank_by_runs,
  story_name,
  genre,
  unique_users as 使用人数,
  total_runs as 进入次数,
  chat_users as 聊天人数,
  ROUND(total_messages::decimal / NULLIF(chat_users, 0), 2) as 平均聊天次数
FROM story_stats
ORDER BY total_runs DESC
LIMIT 20;

-- 用户粘性排名（平均聊天次数）
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
      THEN ROUND(SUM(sr.turn_count)::decimal / COUNT(DISTINCT sr.user_id), 2)
      ELSE 0 
    END as avg_messages_per_user
  FROM story_runs sr
  JOIN story_scenarios ss ON sr.scenario_id = ss.id
  WHERE sr.created_at >= '2026-07-25 00:00:00' 
    AND sr.created_at < '2026-07-27 00:00:00'
  GROUP BY ss.id, ss.title, ss.genre
  HAVING COUNT(DISTINCT sr.user_id) >= 3  -- 至少3个用户
)
SELECT 
  RANK() OVER (ORDER BY avg_messages_per_user DESC) as rank_by_engagement,
  story_name,
  genre,
  unique_users as 使用人数,
  total_runs as 进入次数,
  chat_users as 聊天人数,
  total_messages as 聊天消息数,
  avg_messages_per_user as 平均每用户聊天次数
FROM story_stats
ORDER BY avg_messages_per_user DESC
LIMIT 20;

-- ============================================
-- 四、角色偏好分析
-- ============================================

WITH character_stats AS (
  SELECT 
    c.id as character_id,
    c.id as character_name,  -- characters表没有name字段，用id
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
        WHERE created_at < '2026-07-25 00:00:00'
      )
    ) as returning_users
  FROM chat_messages cm
  JOIN characters c ON cm.character_id = c.id
  WHERE cm.created_at >= '2026-07-25 00:00:00' 
    AND cm.created_at < '2026-07-27 00:00:00'
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
-- 五、用户复访分析
-- ============================================

-- 7月25日注册用户的留存情况
WITH reg_25 AS (
  SELECT id, created_at FROM users 
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-26 00:00:00'
),
login_25 AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-25 00:00:00' 
    AND last_activity_at < '2026-07-26 00:00:00'
),
login_26 AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-26 00:00:00' 
    AND last_activity_at < '2026-07-27 00:00:00'
)
SELECT 
  '2026-07-25' as registration_date,
  (SELECT COUNT(*) FROM reg_25) as new_users,
  (SELECT COUNT(*) FROM login_25) as day0_logins,
  (SELECT COUNT(*) FROM login_26 WHERE user_id IN (SELECT id FROM reg_25)) as day1_returns,
  CASE 
    WHEN (SELECT COUNT(*) FROM login_25) > 0 
    THEN ROUND(
      (SELECT COUNT(*) FROM login_26 WHERE user_id IN (SELECT id FROM reg_25))::decimal / 
      (SELECT COUNT(*) FROM login_25) * 100, 2
    )
    ELSE 0 
  END as retention_rate_pct;

-- 7月26日注册用户的激活情况
WITH reg_26 AS (
  SELECT id, created_at FROM users 
  WHERE created_at >= '2026-07-26 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
login_26 AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-26 00:00:00' 
    AND last_activity_at < '2026-07-27 00:00:00'
)
SELECT 
  '2026-07-26' as registration_date,
  (SELECT COUNT(*) FROM reg_26) as new_users,
  (SELECT COUNT(*) FROM login_26 WHERE user_id IN (SELECT id FROM reg_26)) as activated_users,
  CASE 
    WHEN (SELECT COUNT(*) FROM reg_26) > 0 
    THEN ROUND(
      (SELECT COUNT(*) FROM login_26 WHERE user_id IN (SELECT id FROM reg_26))::decimal / 
      (SELECT COUNT(*) FROM reg_26) * 100, 2
    )
    ELSE 0 
  END as activation_rate_pct;

-- ============================================
-- 六、补充分析：用户行为时间分布
-- ============================================

-- 按小时统计登录分布
SELECT 
  EXTRACT(HOUR FROM last_activity_at AT TIME ZONE 'Asia/Shanghai') as hour_of_day,
  DATE(last_activity_at AT TIME ZONE 'Asia/Shanghai') as activity_date,
  COUNT(DISTINCT user_id) as unique_users
FROM sessions
WHERE last_activity_at >= '2026-07-25 00:00:00' 
  AND last_activity_at < '2026-07-27 00:00:00'
GROUP BY hour_of_day, activity_date
ORDER BY activity_date, hour_of_day;

-- 按小时统计聊天分布
SELECT 
  EXTRACT(HOUR FROM created_at AT TIME ZONE 'Asia/Shanghai') as hour_of_day,
  DATE(created_at AT TIME ZONE 'Asia/Shanghai') as chat_date,
  COUNT(*) as message_count,
  COUNT(DISTINCT user_id) as unique_users
FROM chat_messages
WHERE created_at >= '2026-07-25 00:00:00' 
  AND created_at < '2026-07-27 00:00:00'
GROUP BY hour_of_day, chat_date
ORDER BY chat_date, hour_of_day;

-- ============================================
-- 七、补充分析：用户生命周期
-- ============================================

-- 用户从注册到首次聊天的时间差
WITH first_chat AS (
  SELECT 
    user_id,
    MIN(created_at) as first_chat_at
  FROM chat_messages
  GROUP BY user_id
)
SELECT 
  u.id as user_id,
  u.created_at as registered_at,
  fc.first_chat_at,
  ROUND(EXTRACT(EPOCH FROM (fc.first_chat_at - u.created_at)) / 3600, 2) as hours_to_first_chat
FROM users u
JOIN first_chat fc ON u.id = fc.user_id
WHERE u.created_at >= '2026-07-25 00:00:00' 
  AND u.created_at < '2026-07-27 00:00:00'
ORDER BY hours_to_first_chat;

-- ============================================
-- 八、补充分析：流失用户分析
-- ============================================

-- 注册后未登录的用户
WITH reg_users AS (
  SELECT id, created_at FROM users 
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
logged_in_users AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-25 00:00:00' 
    AND last_activity_at < '2026-07-27 00:00:00'
)
SELECT 
  r.id as user_id,
  r.created_at as registered_at,
  '未登录' as status
FROM reg_users r
LEFT JOIN logged_in_users l ON r.id = l.user_id
WHERE l.user_id IS NULL;

-- 登录后未进入剧情的用户
WITH logged_in_users AS (
  SELECT DISTINCT user_id FROM sessions 
  WHERE last_activity_at >= '2026-07-25 00:00:00' 
    AND last_activity_at < '2026-07-27 00:00:00'
),
entered_story_users AS (
  SELECT DISTINCT user_id FROM story_runs
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
)
SELECT 
  l.user_id,
  '登录未进入剧情' as status
FROM logged_in_users l
LEFT JOIN entered_story_users e ON l.user_id = e.user_id
WHERE e.user_id IS NULL;

-- 进入剧情但未聊天的用户
WITH entered_story_users AS (
  SELECT DISTINCT user_id FROM story_runs
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
),
chat_users AS (
  SELECT DISTINCT user_id FROM chat_messages
  WHERE created_at >= '2026-07-25 00:00:00' 
    AND created_at < '2026-07-27 00:00:00'
)
SELECT 
  e.user_id,
  '进入剧情未聊天' as status
FROM entered_story_users e
LEFT JOIN chat_users c ON e.user_id = c.user_id
WHERE c.user_id IS NULL;
