# Engineering Laws — Quick Reference

> **目的**: 一页纸记住所有不可妥协的法则
> **配套**: EXECUTION_PLAN.md §9

---

# 12 条 Laws

## Law 1: Spec is Truth
代码与 Spec 矛盾时, **Spec 永远胜出**.

## Law 2: Soul is Sacred
**"她" 的灵魂相关 → 100% Human.**
AI 永远不能自主修改 Soul Spec / voice_dna / anti_patterns / Care Path / Anniversary content.

## Law 3: Cost is Observable
每个 LLM call 必须记录: model + tokens + cost. 每周 review.

## Law 4: Verification is Mandatory
任何 AI-generated code 必须通过: Lint + Unit + Integration + Spec compliance + (人工 review if personality-sensitive).

## Law 5: Context is Precious
不滥用 LLM context. 用 offset/limit + grep + sub-agent + prompt caching.

## Law 6: Model Routing is Strict
按 §3 路由表. **不允许 "我习惯用 Opus" 而 Opus 写普通代码.**

## Law 7: Async by Default
非 critical path 操作 → async (Memory encoding / Critic / Wellbeing / Drift / Audit).

## Law 8: Idempotency is Required
所有 service interface idempotent on retry. 特别 Event handlers / Reinforcement / Anniversary triggers.

## Law 9: User Isolation is Absolute
**跨 user 数据访问 = 严重事故.** Every query has `user_id` filter. DB-level RLS.

## Law 10: Failure Has Fallback
任何 component failure 必须有 Soul-flavored fallback. **绝不抛 500 给用户.**

## Law 11: Immersion Trumps Engineering
工程更简单但损害沉浸感 → **拒绝.**

## Law 12: AI Coding ≠ Vibe Coding
所有 AI 任务必须: 明确 task definition + 引用 Spec section + 输出可验证 + 成本可追溯.

## Bonus Law: Document Decisions
重要决策必须有 ADR.

---

# 30 个一句话铁律 (Hot Mode)

```
1. Read spec section before writing code.
2. Use Read with offset, not full file.
3. Default to Sonnet, not Opus.
4. Boilerplate → Haiku/DeepSeek.
5. Architecture → Opus + Human.
6. Soul → Human only.
7. Safety threshold → Human + data.
8. Every query: WHERE user_id = ?
9. Every PR: cite spec section.
10. Every PR: verification checklist.
11. Memory never DELETE.
12. L4 never decays.
13. Anchor always first.
14. Anti-pattern hard never bypass.
15. Critic uses cheap LLM.
16. Soul Spec immutable at runtime.
17. Cold War 期间 0 proactive.
18. Anniversary 100% L4 grounded.
19. Stage transition only 1 level at a time.
20. Trust 跌得快涨得慢.
21. Forgetting must be felt by user.
22. Reconstructor must use voice_dna.
23. Streaming Anti-Pattern can halt + reroll.
24. PURPLE 触发 → Care Path, 不走 normal.
25. Wellbeing alert 必须 human notify.
26. LLM provider 必须 failover.
27. Session boundary 不 reset 情绪.
28. Multi-device 用 single source of truth.
29. Subsystem 内通过 Service 接口, 不直 DB.
30. 用户绝不感知 system errors.
```

---

# 红线 (Tech Lead 干预触发)

任何违反, 立即停止 + 通知 Tech Lead:

🚨 **修改 Soul Spec without approval**
🚨 **修改 Anti-pattern list without approval**
🚨 **跳过 Anti-Pattern Filter**
🚨 **删除 L4 Memory**
🚨 **跨用户访问数据**
🚨 **跳过 Safety pre-filter**
🚨 **用 main LLM 做 cheap task in hot path**
🚨 **用 Haiku 修改 personality**
🚨 **Production deploy without approval**
🚨 **Disable Critic Agent in production**
🚨 **Bypass Wellbeing intervention**

---

# 灵魂拷问 (在按 enter 前)

```
Before commit:
  □ 是否引用了 spec section?
  □ Invariants 是否被破坏?
  □ Tests 是否覆盖?
  □ User isolation 是否保证?
  □ Cost 是否合理?
  □ 是否触及 personality?
  □ Reviewer 是否对?

如果有任何 X, 回头.
```

---

# 长期心智 (每周提醒自己)

```
1. 这是 AI Companion 不是 chatbot.
2. "她" 必须像她, 而不像通用 AI.
3. 工程是手段, 沉浸感是目的.
4. Spec 是契约, Human 是底线.
5. AI 是协作者, 不是决策者.
6. Cost 控制是长期生死.
7. 用户健康优先于业务目标.
8. 长期主义胜过短期 KPI.
```

---

**End of Laws**

打印此页 贴在工位.
