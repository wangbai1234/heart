# Human Review Checklist — Quick Reference

> **目的**: 一秒判断"这个 PR 需要 Human review 吗"
> **配套**: EXECUTION_PLAN.md §7
> **状态**: Reviewer 强制清单

---

## 1. 立即拒绝 — AI 无权决定

如果 PR 触及任一, **立即 reject + escalate to Tech Lead**:

### 1.1 Personality / Soul

- [ ] 修改 `soul_specs/**/*.yaml` 任何文件
- [ ] 修改 `soul_specs/**/golden_dialogues/`
- [ ] 修改 voice_dna patterns
- [ ] 修改 anti_patterns.hard_never 或 soft_never
- [ ] 修改 hidden_facets threshold
- [ ] 修改 core_wound / core_desire / core_fear
- [ ] 修改 character archetype
- [ ] 添加新角色 Soul Spec
- [ ] 修改 Character Reconstructor template (per-character override)

### 1.2 Safety / Wellbeing

- [ ] 修改 `config/safety_keywords.yaml`
- [ ] 修改 `config/care_path_responses/*`
- [ ] 修改 PURPLE / RED keyword 列表
- [ ] 修改 Safety classification thresholds
- [ ] 修改 Wellbeing intervention triggers
- [ ] 修改 suicide protocol response
- [ ] 修改 dependency / addiction detection 阈值
- [ ] 新增 Wellbeing intervention type

### 1.3 Specifications

- [ ] 修改 `runtime_specs/**/*.md`
- [ ] 修改 `engineering_execution/**/*.md`
- [ ] Bump spec version 号

### 1.4 Production Critical

- [ ] Schema migration on production DB
- [ ] User data deletion (GDPR cascade)
- [ ] Production deploy approval
- [ ] LLM provider 切换
- [ ] Multi-region rollout

---

## 2. Tech Lead Approval Required

PR 可以 AI 协助实施, 但 **Tech Lead 必须 approve before merge**:

### 2.1 Architecture

- [ ] 新增 Subsystem
- [ ] 修改 Subsystem 之间接口
- [ ] 修改 Event Bus topic schema
- [ ] 修改 LLM Routing config (`config/llm_routing.yaml`)
- [ ] 修改 Circuit Breaker threshold
- [ ] 修改 Cache TTL strategy (cross-subsystem)

### 2.2 Performance / Cost

- [ ] 修改 Critic sampling rate
- [ ] 修改 Memory decay tau values
- [ ] 修改 Stage progression speed (Soul gates)
- [ ] 修改 Proactive quota / quiet hours

### 2.3 ML / Prompts

- [ ] 修改任何 prompt template 文件
- [ ] 修改 Critic Agent prompt
- [ ] 修改 Director Agent rules
- [ ] 修改 Anti-Pattern Filter logic
- [ ] 修改 Reconstructor logic (cross-character)
- [ ] 修改 Drift Detector logic

### 2.4 Infrastructure

- [ ] 修改 K8s deployment yaml
- [ ] 修改 DB partition strategy
- [ ] 修改 CI/CD workflow
- [ ] 修改 Backup / DR strategy

---

## 3. Standard PR Review (任何 engineer 可 review)

以下情况 standard review 即可 (1 个 approval):

- [ ] Pure boilerplate (SQLAlchemy models, type stubs, migrations)
- [ ] Bug fix that doesn't touch personality logic
- [ ] Test additions
- [ ] Documentation updates (非 spec)
- [ ] Lint / formatting fixes
- [ ] Performance optimization (verified)
- [ ] Single-subsystem internal refactor (no interface change)

---

## 4. Reviewer 的 7 个灵魂拷问

每个 PR 必须问:

### Q1: Spec Compliance
```
这个 PR 引用了哪个 spec section?
代码是否真的符合那个 section 的描述?

如果 PR 没引用 spec → REJECT, 让作者补上
如果引用了但偏离 → 讨论或 REJECT
```

### Q2: Invariant 保护
```
这个 subsystem 的 INV-* invariants 仍然成立吗?

特别检查:
  - SS01: INV-1 (Anchor first), INV-2 (Anti-pattern)
  - SS02: INV-M-1 (no delete), INV-M-3 (Top-K), INV-M-6 (user_id filter)
  - SS03: INV-E-1 (inertia), INV-E-2 (active stack size)
  - SS04: INV-R-3 (max delta), INV-R-4 (asymmetric trust)
  - SS07: 各 hard gate
```

### Q3: 跨 Subsystem 影响
```
这个改动会影响其他 subsystem 吗?
- Event 是否变化?
- Interface 是否变化?
- Performance 影响?

如果跨 subsystem → Tech Lead review
```

### Q4: User Isolation
```
所有 DB query 都有 user_id filter 吗?
有跨用户访问的可能吗?

如果 N → REJECT (隐私事故)
```

### Q5: Cost Impact
```
这个改动会增加 LLM 调用吗?
是否在 hot path 引入新的 main LLM call?
Critic sampling 是否被改?

如果不合理增加成本 → REJECT
```

### Q6: Soul-Sensitivity
```
是否触及"她"的表达 / 内心 / 行为?
- Prompt 改动?
- voice_dna 应用?
- 主动消息生成?
- Anti-pattern?

如果 Y → 第 1 类立即 reject, 或 Tech Lead approve
```

### Q7: Verification
```
- Tests added?
- Tests pass?
- Golden tests still pass (if SS01-06)?
- Spec validator 跑了吗?

如果任一 N → REJECT
```

---

## 5. PR 模板 (强制使用)

`.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## What
<简短描述>

## Why
<引用 spec section 或 issue>

## Spec References
- runtime_specs/0X_*.md §<section>
- (其他 spec)

## Touches
- backend/heart/...
- (其他文件)

## Personality-Sensitive?
- [ ] No, this is pure plumbing
- [ ] Yes, requires Tech Lead approval (see HUMAN_REVIEW_CHECKLIST §1-2)

## Verification
- [ ] Unit tests pass
- [ ] Integration tests pass  
- [ ] Golden tests pass (if SS01-06 affected)
- [ ] Spec validator pass
- [ ] Performance check (if applicable)
- [ ] Cost impact analyzed

## Reviewer Notes
<给 reviewer 的提示>
```

---

## 6. Reviewer 签字

```markdown
# 完成 review 后, comment:

Reviewer: <name>
Date: 2026-XX-XX

Spec Compliance: ✅ / ❌
Invariants: ✅ / ❌
Cross-subsystem Impact: ✅ / ❌
User Isolation: ✅ / ❌
Cost: ✅ / ❌
Soul-sensitivity: ✅ / N/A
Verification: ✅ / ❌

Decision: APPROVE / REQUEST_CHANGES / REJECT
```

---

## 7. 紧急 Hotfix 流程

```
Critical production bug:
  1. 通知 Tech Lead (in 5 min)
  2. Quick fix branch
  3. Minimum tests (just enough)
  4. Tech Lead "emergency approve" with comment
  5. Deploy
  6. Within 24h: PROPER PR with full tests

Hotfix only for:
  - User safety issue
  - Production crash
  - Critical data corruption
  
NOT for:
  - "AI 觉得不够好"
  - 性能小优化
  - Cosmetic changes
```
