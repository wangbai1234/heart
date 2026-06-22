# SS04 Special States — 实现路线决策

**日期**: 2026-06-22
**决策者**: HUMAN（已签字 Option A）
**执行者**: opencode

---

## 1. 背景

`service.py:21-36` 已接入 anti_gaming/attachment_tracker/signal_aggregator/trust_tracker。
`process_turn` step 4 走 `special_states.py` 的轻量实现，`cold_war.py` / `reunion.py` 未被任何 prod 代码引用。

当前 `service.py:307` 硬编码 `emotion_state=None`，导致 cold war **永远不会被触发**。

## 2. 能力对比

| 能力 | special_states.py | cold_war.py | reunion.py |
|------|-------------------|-------------|------------|
| 4 种 enum | ✅ | (作为 cold_war 内部) | (reunion phases) |
| 强度衰减 | ❌ | ✅ | — |
| 信号冷却 | ❌ | ✅ | — |
| Reconciliation 多阶段 | ❌ | ✅ | — |
| Reunion phases | ❌ | — | ✅ |
| Warmth signals | ❌ | — | ✅ |
| Anniversary triggers | ❌ | — | ❌ (spec 提及但未实现) |
| Soul 特定 overlay | ❌ | ✅ (Rin/Dorothy) | ✅ (Rin/Dorothy) |
| Gottman 效应 | ❌ | ✅ (+0.02 trust, +0.05 attachment) | — |
| 紧急衰减 (30+天) | ❌ | ✅ | — |
| 信任衰减 (spec §4.4) | ❌ | — | ✅ |
| 测试覆盖 | 19 tests | 0 tests | 0 tests |

## 3. 选项

### 选项 A — 接入完整版 ✅ 已选

- 改 `service.py:296-333` → 调用 cold_war / reunion 的类
- 传递真实 `emotion_state`（去掉 None）
- Persona Composer 接入 behavioral overlay
- 跑 19 个 special_states 测试：兼容
- 工作量评估: 2 天
- 风险: 行为变化、需要回归 SS04 全套测试

### 选项 B — 文档化 special_states 为正式实现

- 删除 cold_war.py / reunion.py（~920 行）
- 在 service.py 顶部加注释说明"轻量实现"
- 工作量评估: 30 分钟
- 风险: 违反 spec R-8/R-9/IMM-R-3/IMM-R-4，丢失 soul 特定行为

## 4. 推荐 + 决策

**推荐 Option A，HUMAN 已签字确认。**

理由：
1. Spec 合规：runtime spec §3.11 要求 cold war 有行为 overlay、Gottman 效应、紧急衰减
2. Soul 角色差异化：Rin 和 Dorothy 的中文散文级 prompt overlay 已写好
3. 架构互补：special_states.py 做入口路由，cold_war/reunion 做深度状态管理
4. ~920 行 spec 对齐代码，删了要重写

## 5. 后续 PR

- **PR-6a** `feat/ss04-wire-cold-war-reunion` — 接入实施（本次已决定）
- PR-6b 不需要（Option B 未选）

---

**HUMAN 签字**: ________________ 日期: ________
