# Memory Extractor §5.2 dual-mode 观察期跳过 — 合理化决策

**Date**: 2026-06-20
**Decision**: Skip §5.2 2-week dual-mode observation; rely on Golden Set live regression as substitute gate.
**Decided by**: HUMAN

## 背景

`docs/execution/MEMORY_LLM_EXTRACTOR_REFACTOR.md` §5.2 要求切默认 `mode=llm` 前完成 2 周 dual-mode 观察 + `extractor_diff_report.py` 日报 + acceptance metrics（LLM recall ≥ regex × 1.5、precision ≥ regex、假阳性 < 5%、cost < $0.50/天/活跃用户）。

## 跳过原因

1. **当前无生产流量**（Phase 8 Closed Beta 未启），dual-mode 没有"真实样本"可观察。2 周观察期的意义在于对比两套实现在同一流量下的表现——无流量则无从对比。
2. **Golden Set 49 case + live regression gate** 提供了更强、更稳定的保险——它直接基于 expected envelope 打分，比 dual-mode 抽样 1% 由 HUMAN 裁决更严密。v1.0.2 后 strict scoring baseline 已建立。
3. **Regex 已通过 §5.1 降级为 hints provider**，不存在两套独立写入 L3 的路径。dual-mode shadow 表 (`memory_l3_facts_shadow_regex`) 仅能记录 regex 产出，对比的是 L2 层 hint 质量而非 L3 写入质量——与 §5.2 原始设计意图（"两套 L3 writer 对比"）已有偏差。

## 替代验证

- Golden live gate（strict scoring: no HARD failures + recall ≥ 0.8 + precision ≥ 0.7 + drop_recall ≥ 0.8）持续 ≥ 75% pass（v1.0.2 当前基线）
- Closed Beta 上线后 7 天 0 回归即视为通过 §5.3 sunset pre-condition
- 单 call 成本 $0.0006–$0.0008 持续 < $0.002 cap

## 触发回滚条件（替代 §5.2 acceptance metrics）

| Condition | Action |
|---|---|
| Golden live pass 率连续 2 次 < 60% | 回滚 prompt 到上一版 |
| 生产 audit_log dropped/candidate 比 > 0.5 | 暂停默认 llm，回 dual 观察 |
| 单 call 成本 > $0.005 | 启用 §3.2 mitigations（压缩 few-shot / 降 L3 snapshot / 启用 prompt caching） |

## §5.3 regex sunset 更新计划

原计划：60 天观察后删除 `regex_shadow.py` + 关闭 `mode=regex` 代码路径。
更新：改为 issue 跟踪——**Closed Beta 上线 + 7 天 0 回归** 作为 pre-condition，触发后 60 天 grace period，然后删除。

删除清单：
- `backend/heart/ss02_memory/extractor/regex_shadow.py`
- `mode in ("dual", "regex")` 代码路径
- `memory_l3_facts_shadow_regex` 表 + 迁移文件 `010_memory_regex_shadow.py`

Sunset date: TBD（待 Closed Beta 上线日期确认）

---

## Approval

| Date | Reviewer | Role | Decision | Notes |
|---|---|---|---|---|
| 2026-06-20 | HUMAN | Project Lead | APPROVED | Golden gate substitutes §5.2 observation period; sunset deferred to issue tracker |
