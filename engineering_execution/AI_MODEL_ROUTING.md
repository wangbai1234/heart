# AI Model Routing — Quick Reference

> **目的**: 在 5 秒内决定一个任务用哪个 model
> **配套**: EXECUTION_PLAN.md §3
> **状态**: Canonical. 违反需要 Tech Lead override.

---

## 1. 30 秒 Decision Tree

```
                    [任务到达]
                        │
                        ▼
              触及"她"灵魂?  ──Y──→ HUMAN ONLY
              (Soul/voice_dna/Care/Anniversary)
                        │ N
                        ▼
              触及 Safety/Wellbeing 阈值? ──Y──→ HUMAN + OPUS analysis
                        │ N
                        ▼
              架构 / 跨 Subsystem 决策? ──Y──→ OPUS + HUMAN review
                        │ N
                        ▼
              复杂实现 (multi-file)? ──Y──→ SONNET
                        │ N
                        ▼
              Boilerplate (well-specced)? ──Y──→ HAIKU / DEEPSEEK
                        │ N
                        ▼
                     SONNET (default)
```

---

## 2. 完整路由表

### 🔴 100% HUMAN

| 任务 | 为什么 | 谁 |
|------|--------|-----|
| Soul Spec 内容写作 / 修改 | 角色 IP, AI 无法判断"像她" | 创作者 |
| Anti-pattern 列表 curation | 漏一个 = 角色被驯化 | 创作者 + 中文母语者 |
| Care Path response 文案 | 关乎生命安全 | 创作者 + 心理咨询师 |
| Anniversary / Ritual content | 角色专属内容 | 创作者 |
| Safety keyword lists | 关乎安全分类 | 安全 + 法律 + 心理 |
| Safety threshold tuning | False positive/negative trade-off | Tech Lead + 数据 |
| Wellbeing intervention 设计 | 影响脆弱用户 | 心理咨询师 + 法律 |
| Production deploy approval | 风险控制 | Tech Lead |
| Crisis response (PURPLE incident) | 法律风险 | 创始团队 |

### 🟠 HUMAN + OPUS (Opus 辅助 brainstorm, Human 决策)

| 任务 | Opus 的角色 |
|------|------------|
| Architecture decisions | 列出选项 + 分析 trade-off |
| New Subsystem design | 帮 brainstorm, 但不决定 |
| Spec changes (RFC) | 撰写初稿, 分析影响 |
| Cross-cutting refactor 决策 | 影响范围分析 |
| Wellbeing 阈值数据分析 | 跑分析, 推荐参数 |
| Memory decay 公式调整 | 数学分析, 推荐曲线 |

### 🟡 OPUS (with Human review)

| 任务 | 为什么 Opus |
|------|------------|
| Drift Detector 算法设计 | 需要深度推理 |
| Reconstructor template design | 需要理解 voice_dna 应用 |
| Streaming Anti-Pattern Filter 算法 | Cross-chunk 复杂 |
| Conflict Resolver Matrix 扩充 | 多 subsystem 交互理解 |
| Critic prompt design | Prompt 工程 |
| Care Path prompt | 关键 prompt |
| Initiative decision tree | 多 gate 协同 |
| Stage entry conditions 平衡 | UX trade-off |
| Anchor template design | Soul 重要表达 |
| Critical bug investigation (复杂) | 深度推理 |
| Performance optimization design | 多角度权衡 |

### 🟢 SONNET (主力, default)

| 任务 | 备注 |
|------|------|
| Subsystem service 实现 (按 spec) | 主要日常工作 |
| Memory Service core implementation | Spec 详细, 实施即可 |
| Phase Transition Engine | Rule engine, 标准实现 |
| Multi-file refactor | 跨文件理解 |
| Modality Adapter | Spec 详细 |
| Director Agent rules | Rule engine |
| Code review (PR 审查) | Spec compliance check |
| Integration test 设计 | 需理解交互 |
| Event Bus 实现 | Infrastructure code |
| Model Router 实现 | Critical infra |
| PG schema design | 查 spec |
| API endpoint 实现 | Standard |
| Activity pool YAML 翻译 (Human spec → YAML) | 格式转换 |

### 🔵 HAIKU / DEEPSEEK V3 (cheap, well-specced only)

| 任务 | 备注 |
|------|------|
| SQLAlchemy model boilerplate (from schema) | 纯翻译 |
| Alembic migration scripts | 标准模式 |
| Pydantic schema (from data structures) | 翻译 |
| Type annotations | 机械任务 |
| Docstring drafts | Boilerplate-ish |
| Unit test scaffolding (given fixtures) | Pattern-based |
| Dockerfiles / k8s YAML | 标准格式 |
| API documentation drafts | 从代码生成 |
| Lexicon files (emotion keywords) | 列表编纂 |
| Memory encoding (在 production hot path) | Cheap 必需 |
| Safety classification (在 production hot path) | Cheap 必需 |
| Critic Agent (在 production hot path) | Cheap 必需 |

### 🟣 CONTINUE + VSCode (inline completion)

| 任务 | 备注 |
|------|------|
| Inline autocomplete | 编辑时 |
| Import organization | 极琐碎 |
| Variable rename | 单文件 |
| Small function refactor | 局部 |

---

## 3. NEVER USE (绝对禁止)

| 任务 | 不能用 | 必须用 |
|------|--------|--------|
| Soul Spec 任何修改 | AI (含 Sonnet) | HUMAN |
| Safety keyword 修改 | AI 自主 | HUMAN |
| Memory decay 公式 | DeepSeek/Haiku | OPUS + HUMAN |
| Anti-pattern 增删 | 任何 AI 自主 | HUMAN |
| Critic prompt | Haiku/DeepSeek | SONNET + HUMAN review |
| Production Wellbeing 阈值 | AI 自主 | HUMAN + 数据 |
| Schema migration in production | AI 自主执行 | HUMAN approve |
| User data deletion (GDPR) | AI 自主 | HUMAN verify |

---

## 4. 成本速查

```
Per task estimated cost:

Boilerplate task (Haiku):     $0.001 - $0.005
Boilerplate task (DeepSeek):  $0.0001 - $0.0005
Standard impl (Sonnet):       $0.05 - $0.20
Complex impl (Sonnet):        $0.30 - $1.00
Architecture (Opus):          $0.50 - $5.00
Critical bug (Opus):          $2.00 - $20

Daily LLM budget per engineer:
  - Junior: $5-10 (mostly Haiku/DeepSeek + 偶尔 Sonnet)
  - Senior: $10-20 (Sonnet 主力)
  - Tech Lead: $30-50 (Opus + Sonnet)

Monthly team budget (5 engineers): $2000-4000 LLM
```

---

## 5. Routing 自检 (在 commit 前)

- [ ] 这个任务我用了正确级别的 model 吗?
- [ ] 是否有 "我用 Opus 写普通代码" 浪费?
- [ ] 是否有 "用 Haiku 做 critical" 风险?
- [ ] 是否触及 §1 决策树的 Human-only 范畴?
- [ ] 成本是否合理?

---

## 6. 紧急情况

```
当不确定时:
  - 默认 Sonnet
  - Ask Tech Lead
  - 检查 EXECUTION_PLAN.md §3 详细路由表

绝对不要:
  - "AI 应该懂" → 跳过路由检查
  - 用 Opus 因为"重要"而不是因为"复杂"
  - 在 production hot path 用 main LLM 做 cheap task
```
