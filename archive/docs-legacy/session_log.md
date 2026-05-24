# AI Session Log — 成本与质量追踪

> **目的**: 每个 AI session 结束时记录一行，让我们对"AI 到底花了多少钱、产出质量如何"有可治理的数据。
> **强制规则**: 任何修改了仓库代码或 `.md` 的 AI session 必须追加一行。
> **维护者**: 由完成 session 的 AI 自行追加；HUMAN 每月 review 一次趋势。

---

## 字段定义

| 字段 | 含义 |
|------|------|
| `Date` | YYYY-MM-DD，session 结束日 |
| `Model` | 主力模型代号（CC-Opus / CC-S46 / CC-Haiku / Codex-DeepSeek / 其他） |
| `Task` | 一句话描述任务，最多 10 个词 |
| `Files Touched` | 修改/创建的文件数（粗略） |
| `Token Est` | 整个 session 的 token 估计（k-tokens, 粗略） |
| `Cost USD` | 估计成本（粗略，可空） |
| `Regret 1-5` | 自评 — 1=非常满意，5=应该用不同 model 或不同方法 |
| `PR / Note` | 链接到 PR；或如果没出 PR，留一行原因 |

`Regret` 字段的精神：**"如果重来一次会不会改变方法？"**。这不是质量打分，而是诚实的事后反思。Regret ≥ 3 应在 Note 列写明原因，作为后续 model routing / workflow 调整的输入。

---

## 日志（最新在最上面）

| Date       | Model            | Task                                                | Files | Tokens | Cost   | Regret | PR / Note |
|------------|------------------|-----------------------------------------------------|-------|--------|--------|--------|-----------|
| 2026-05-24 | CC-Sonnet-4.5    | Phase 7 准备工作完整清单 + 5 个 blocker 文件合并 | 6     | ~65k   | ~$0.65 | 1      | PR #7 updated; 产出 PHASE_7_READINESS_CHECKLIST.md + 合并 governance blocker 文件; 确认 Top 10 + 分支合并策略 |
| 2026-05-23 | CC-Opus-4.7      | Phase 7 §1.7 架构 audit（41 findings + Top 10）        | 1     | ~50k   | ~$1.50 | 2      | docs/audit/2026-05-23_architecture_audit.md — audit-only，未改 src；下次 audit 应跑 pytest --cov 补 D7 |
| 2026-05-23 | CC-Opus-4.7      | 仓库治理 + Phase 7+ 操作手册 + governance 文件骨架    | 7     | ~120k  | ~$3.60 | 2      | 本次 session（初始化）— 一次性产出大量治理文件，未来 governance 工作应增量 |

---

## 月度趋势（HUMAN 填）

```
2026-05: TBD
```

---

## 使用提示

- **不要把 session_log 当成 changelog**。代码变更看 git log；这里只追踪"AI 花了多少 + 为什么这么花"。
- **Regret ≥ 3 是宝贵信号**，不是失败标签。它告诉未来 session "下次别这么做"。
- **完整 session token 不可知**，估算到 10k 量级即可。重要的是趋势，不是精度。
- 当本文件超过 200 行时，把旧条目归档到 `docs/archive/session_log_<YYYY-QN>.md`，本文件只保留最近一个季度。
