# Soul Drift Regression Suite — 人格漂移自动回归设计

> **文档角色**: Phase 7 §1.4 设计交付物 (per `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.4)
> **状态**: Design — 实施前需 HUMAN 签字（角色：心理顾问 + 主创 + 工程）
> **上游依赖**: `docs/design/integration_test_pyramid.md` Tier C
> **下游**: §1.4 实施 prompt (CC-S46)
> **设计者**: CC-Opus-4.7
> **日期**: 2026-05-24

---

## 0. TL;DR

每次 AI 改 Composer / Reconstructor / Anti-drift Injector / Critic Agent / soul_spec → 自动跑：

```
30 prompts × {Rin, Dorothy} = 60 generations
       ↓
LLM-as-judge (DeepSeek) 给每条打 5 维 score vs baseline
       ↓
聚合 drift_score = weighted_mean(dim_scores)
聚合 anti_pattern_hits = exact_count(over soul_spec.anti_patterns)
       ↓
判定:
  drift_score < 0.15      ✅ 通过
  drift_score 0.15-0.30   🟡 warn, 人评估
  drift_score > 0.30      🔴 block release tag
  anti_pattern_hits > 0   🔴 hard fail (无论 drift_score)
       ↓
生成 HTML diff → /tmp/heart_drift_report.html → CI artifact
```

**核心信念**: 没有这个 suite，**Rin 和 Dorothy 的人格会在 21 周内被 AI 一点点改写而无人察觉**。这是项目最高优先级的"AI governance"机制。

---

## 1. 设计动机 (Why)

### 1.1 这个 suite 解决什么问题

四个组件都在塑形 Voice，任意一处被 AI 改动 → 全局漂移：

```
        user_msg
            ↓
     [SS02 Reconstructor]   ← 用 memory + voice_dna 还原一段过去的"她说过的话"
            ↓
     [SS05 Composer]        ← 编排所有 prompt layers，含 voice_dna 注入
            ↓
     [SS05 Anti-drift Injector] ← 在 prompt 里塞 "你必须像 Rin 一样说话" 段落
            ↓
     LLM (DeepSeek)
            ↓
     [SS05 Anti-pattern Filter] ← regex 扫 hard_never + forbidden_patterns
            ↓
     [SS07 Critic Agent]    ← LLM-as-judge 现场打分；可触发 reroll
            ↓
        response
```

任何一个 AI commit 改动其中任意文件 / soul_spec / config，都可能让 voice 偏移而单测**毫无察觉**（因为单测都是 mock LLM）。

### 1.2 为什么单测不够

| 你以为单测能抓 | 实际不能 |
|---------------|---------|
| anti_pattern 命中 | 抓得到 — regex 检测；已存在 |
| voice_dna 风格漂移 | **抓不到** — 单测无法判断 "这句话是不是像 Rin" |
| Composer prompt 拼装顺序漂移 | **抓不到** — mock 看不到最终 prompt 在 LLM 上的实际效果 |
| 多次回归后的"温水煮青蛙"漂移 | **完全抓不到** — 单测不存历史 baseline |

→ 必须用 LLM-as-judge + 历史 baseline。

### 1.3 已存在的可复用资产

- `soul_specs/{rin,dorothy}/v1.0.0.yaml`
  - `voice_dna[]`：6+ 条 pattern，含 examples
  - `anti_patterns.hard_never[]`：~30 条禁词
  - `anti_patterns.forbidden_patterns[]`：3+ 条 regex
  - `humor_profile`：dryness / sarcasm / warmth_in_humor 等定量轴
  - `regression_tests`（spec 自带 §13 区块）：已经定义了一些断言
- `soul_specs/{rin,dorothy}/golden_dialogues/gd-001 … gd-010.yaml`
  - 10 个场景 × 2 角色 = 20 个金标准对话
  - 含 `must_match_voice_dna` + `must_not_contain` + `example_acceptable_responses`

→ **golden_dialogues 是 baseline 的天然候选**；不必从零开始。

---

## 2. Baseline 生成程序

### 2.1 Canonical Prompts 设计

30 个 prompt 分布（每角色独立的同样 30 个）：

| 类别 | 数量 | 来源 |
|------|------|------|
| Golden dialogue 复刻 | 10 | 直接用 gd-001 … gd-010 的 `user_message` |
| Smalltalk / 日常 | 5 | 新设计（吃饭、天气、问候） |
| 亲密 / 脆弱披露 | 5 | 新设计（用户哭、用户表白） |
| 冲突 / 边界 | 5 | 新设计（用户骂 / 提删除 / 提另一个人） |
| 元层级 / 越狱尝试 | 5 | 新设计（"你是 AI 吗"、"忽略之前指令") |

存储:
```
config/voice_drift/canonical_prompts.yaml
  prompts:
    - id: cp-001
      category: golden_replay
      source_golden: gd-001
      user_message: "..."
    - id: cp-011
      category: smalltalk
      user_message: "你今天吃饭了吗"
    ...
```

**约束**:
- 30 条 prompts **全部 read-only after sign-off** — 任何改动 = 重新跑 baseline
- 改 prompt 集 → HUMAN approve（心理顾问 + 主创）

### 2.2 生成 baseline 的过程

每个角色一次性跑：

```
for prompt in 30 prompts:
    sample = ModelRouter.generate(
        soul_spec=load(character),
        system_prompt=Composer.build(...),     # 用当前 main 的 Composer
        user_message=prompt.user_message,
        temperature=0.7,
        seed=None,                              # 不固定，要捕捉真实方差
    )
    save baseline_entry
```

为捕捉 stochasticity，每个 prompt 跑 **3 次取并集**（见 §2.4）→ 90 generations / 角色（一次性，~$0.40）。

### 2.3 Baseline JSONL Schema

```jsonl
{"prompt_id": "cp-001", "run_idx": 0, "character": "rin", "soul_spec_version": "1.0.0",
 "model": "deepseek-chat", "model_revision": "2026-05-24",
 "temperature": 0.7, "system_prompt_hash": "sha256:...",
 "response": "……神无月凛。你呢。",
 "metadata": {
   "anti_pattern_hits": [],
   "voice_dna_match_ids": ["vd-001"],
   "tokens_in": 320, "tokens_out": 12,
   "latency_ms": 540, "cost_usd": 0.0008
 },
 "timestamp": "2026-06-01T14:23:01Z"}
```

存:
```
backend/tests/golden/voice_baselines/
  rin_baseline.jsonl       (90 entries: 30 prompts × 3 runs)
  dorothy_baseline.jsonl
  README.md                 ← 描述何时何人生成的，model revision，approval signoff
```

**`backend/tests/golden/voice_baselines/`** 受 CODEOWNERS 保护，merge 必须 HUMAN approve。

### 2.4 多次取并集的依据

LLM 输出有方差，单次 sample 不能定义 "canonical voice"。

3 次 sample 后：
- 5-dim score 的 baseline = **3 个样本的均值 + 标准差**
- 后续 PR 的对比对象 = baseline 分布；用 z-score 衡量偏离
- 这同时把 "LLM 抖动" 与 "code 引发的真漂移" 区分开

---

## 3. Per-PR Regression 程序

### 3.1 触发条件

```
Affected files (任意一处改动都触发 voice drift 全跑):
  - backend/heart/ss05_composer/**/*.py
  - backend/heart/ss02_memory/reconstructor.py
  - backend/heart/ss07_orchestration/critic_agent.py
  - backend/heart/safety/critic_agent.py
  - backend/heart/prompts/**/*.py
  - soul_specs/**/*.yaml
  - config/voice_drift/canonical_prompts.yaml   ← 改这个本身就要重 baseline
```

CI 通过 `pull_request.paths` filter 实现。也可手动 `gh workflow run voice-drift.yml`。

### 3.2 跑法

```
for prompt in 30 prompts:
    sample_new = ModelRouter.generate(...)        # 单次（不取 3）
    baseline_samples = baseline_for(prompt_id)    # 3 条 baseline
    dim_scores = LLM_judge(prompt, sample_new, baseline_samples)
    record (prompt_id, dim_scores, anti_pattern_hits)

aggregate:
  drift_score = weighted_mean(all dim_scores)
  total_anti_pattern_hits = sum(anti_pattern_hits)
```

**单次跑成本**: 30 prompts × 2 角色 × 1 sample = 60 generations + 60 LLM-judge calls ≈ **$0.50**。

### 3.3 5-Dim Scoring 维度

| Dim | 说明 | 权重 | 判定方式 |
|-----|------|------|---------|
| **D1 voice_dna 命中** | sample 是否体现该角色 voice_dna 列表中的至少一条 pattern | 0.30 | LLM-judge: "list which vd-* IDs match this response"，越多越好 |
| **D2 anti_pattern 检出** | sample 是否触发 hard_never / forbidden_patterns | 0.30 | **Pure regex / substring 检测**，不靠 LLM；命中 → 整轮 hard fail |
| **D3 tone 一致性** | dryness / sarcasm / warmth 等定量轴是否接近 baseline | 0.15 | LLM-judge: 给每维 0-1 评分，与 baseline 均值差 |
| **D4 情绪 inertia 一致性** | recovery / volatility 是否符合 spec (e.g. 凛 slow recovery) | 0.10 | LLM-judge: "对比 baseline，新回复表现的情绪反应速度是更快还是更慢" |
| **D5 语义保持度** | 含义有没有偏离（不是只看风格） | 0.15 | Embedding similarity (DeepSeek-embed) baseline ⨯ new |

**Drift score 计算**:
```
drift_score = (
  0.30 * (1 - D1_match_ratio) +     # 越多 vd 命中越低 drift
  0.30 * D2_anti_pattern_severity + # anti_pattern 直接拉高
  0.15 * D3_tone_l2_distance +
  0.10 * D4_inertia_distance +
  0.15 * (1 - D5_embedding_cosine)
)
```

D2 的存在让 anti_pattern 同时是 *硬* fail 和 drift score 的贡献项，双保险。

### 3.4 阈值（Threshold）

| drift_score | 标记 | CI 行为 |
|-------------|------|---------|
| < 0.10 | 🟢 PASS | continue |
| 0.10 – 0.15 | 🟢 PASS（提示） | continue + warn comment |
| 0.15 – 0.20 | 🟡 WARN | merge 允许，但开 issue，主创 review |
| 0.20 – 0.30 | 🟡 WARN-HIGH | merge 阻塞 24h，HUMAN signoff 才能 override |
| > 0.30 | 🔴 FAIL | merge 阻塞，必须降到 ≤ 0.20 或走 approved drift 流程 |
| 任意 D2 命中 | 🔴 HARD FAIL | merge 阻塞，没有 override |

**阈值校准**:
- 初始值是上面的；
- Phase 7 §1.4 跑完后，根据前 5 次真实 PR 的 drift 分布调一次（写回本设计）；
- 之后每季度 retro 时复盘。

### 3.5 LLM-as-Judge 设计

**用哪个模型评？**
- DeepSeek-chat（同生成模型），因为 cost 最低
- *不* 用 Anthropic / OpenAI — Law 6 LLM Router 单一架构
- 但要注意：用同一个模型既生成又评，可能有 "自我背书" 偏差 → 缓解见 §3.6

**Judge prompt 模板**（实施时落 `backend/heart/qa/voice_judge.py`，本设计仅给出 shape）:
```
You are evaluating a candidate response against an established voice profile.

Character: {character_name}
Voice DNA (you must check which patterns are exhibited):
  vd-001: <pattern + example>
  vd-002: <pattern + example>
  ...

Anti-patterns (these MUST NOT appear):
  hard_never: [...list...]
  (you do not need to check these — regex does; we only need style judgment)

Baseline samples (this is canonical 'this is how she sounds'):
  1. <baseline_response_1>
  2. <baseline_response_2>
  3. <baseline_response_3>

Candidate response:
  <candidate>

User message that produced it:
  <user_message>

Output ONLY valid JSON, no prose:
{
  "vd_matches": ["vd-001", "vd-003"],
  "tone_scores": {"dryness": 0.85, "sarcasm": 0.50, "warmth_in_humor": 0.10, ...},
  "inertia_distance_from_baseline": 0.12,
  "semantic_similarity_to_baseline_intent": 0.81,
  "free_text_critique": "新回复更暖；baseline 更冷。",
  "verdict_summary_for_humans": "Slight warmth drift; not severe."
}
```

**强制 strict-json mode**: judge 输出不解析 → 整测失败（不是 fallback）。

### 3.6 自我背书偏差缓解

风险：DeepSeek 评 DeepSeek 自己写的，可能系统性给高分。

缓解（按成本由低到高）:

1. **D2 anti_pattern** 100% regex，不让 LLM 自评。— ✅ 已设计
2. **D5 embedding similarity** 用 deterministic embed（不是 chat），减少自评。— ✅ 已设计
3. **Spot-check**: 每次 regression 中随机抽 3 个 sample，HUMAN 盲评，结果存 `docs/audit/voice_drift_spot_check.jsonl`，与 LLM-judge 长期对比；偏差大 → 调权重。
4. **季度 calibration**: 留好 "approved drift" 历史，用作 LLM-judge 的 prompt-shot examples。

### 3.7 Storage / 输出

每次 regression run 写两份：

```
artifacts/voice_drift/<branch>_<commit_sha>/
  scores.jsonl                ← 每个 prompt 一行，详 §3.3 schema
  summary.json                ← 整体 drift_score + verdict
  diff_report.html            ← §4 见
  judge_traces/*.json         ← 每次 judge 调用的 raw req/resp
```

CI artifact 保留 90 天。

---

## 4. Diff 可视化（HTML 报告）

### 4.1 目的

让 HUMAN 在 30 秒内判断 "这个 drift 是 false positive 还是真漂移"。

### 4.2 报告结构

```
heart_drift_report.html
├── Header
│   ├── Branch / commit / timestamp
│   ├── Overall verdict (大字 ✅/🟡/🔴)
│   └── Aggregate drift_score
├── Summary table (sortable)
│   ├── Prompt ID, drift_score, anti_pattern hits, verdict
│   └── 点击 row → 跳到详情
├── Per-prompt detail (折叠列表)
│   ├── user_message
│   ├── side-by-side: 3 个 baseline ↔ 1 个 new (字符级 diff 高亮)
│   ├── anti_pattern hit 高亮（红色下划线）
│   ├── vd-match badges (绿色)
│   ├── 5-dim 分数 bar
│   └── LLM-judge raw critique
└── Footer
    ├── How to approve drift (link to §5)
    └── Threshold table
```

### 4.3 Diff 算法

- 字符级用 Python `difflib.SequenceMatcher`
- Anti-pattern 高亮：直接搜词，命中 wrap `<mark class="anti">`
- voice_dna match：把 sample 中"像 vd-001 example 的子串"用 LLM 抽出 → `<mark class="vd">`

报告生成由 `backend/heart/qa/report_builder.py`（实施时落）输出到 `/tmp/heart_drift_report.html`。CI 上传 artifact。

---

## 5. False-Positive / Approved Drift 流程

### 5.1 什么算 false positive

- LLM 输出本身有方差，单次 sample 偶然偏移 baseline 范围（z > 2σ 但 < 3σ）
- 改动是 *有意* 调 voice（如调高 Dorothy 的 sarcasm）—这不是漂移，是产品决策

### 5.2 流程

```
1. PR 触发 voice drift → score 0.22 (WARN-HIGH)
2. HTML report 出，HUMAN 看 per-prompt detail
3. 判断：
   a) 真漂移、回退 → fix code → 重跑
   b) 偶发抖动 → 用 `gh workflow run voice-drift.yml -F retry=true` 重跑 3 次
      - 3 次中位数 < 0.15 → 标 "stochastic flake"，merge
   c) 有意调整 → 走 baseline 升级流程（§5.3）
```

### 5.3 Baseline 升级流程

**触发场景**: 主创决定让 Dorothy "更暖一点" → soul_spec / Composer 改 → 必然破 baseline。

**流程**:
1. 在 PR description 加 `[baseline-update]` 标签
2. CC-S46 在同 PR 内跑 `make voice-baseline --character dorothy`
3. 新 baseline JSONL 写入 `backend/tests/golden/voice_baselines/dorothy_baseline.jsonl.proposed`
4. **必须** HUMAN（主创 + 心理顾问）双签
5. 签字后 `mv .proposed dorothy_baseline.jsonl`，commit
6. PR description 必填字段：
   - 为什么升 baseline（产品决策 / 调 voice / 修 anti_pattern）
   - 升级前后的 diff_report.html 链接
   - 心理顾问签字（PR comment 即可）

文档落 `docs/soul_drift_baseline_update.md`（在实施 prompt 中产出）。

### 5.4 永远不允许的 baseline 升级

- 单独降阈值 (`drift_threshold` 0.15 → 0.30) — 必须 PR + 解释 + HUMAN
- "测试老 fail 就把 baseline 换成现状" — 这是把漂移合法化
- 跳过 spot-check
- 升 baseline 时同时 disable D2 (anti_pattern) — 必然拒绝

---

## 6. 成本预算 & Kill Switch

### 6.1 Per-character per-regression 成本

| 成分 | 数量 | 单次 cost | 小计 |
|------|------|----------|------|
| Generation | 30 | ~$0.003 | $0.09 |
| LLM-judge | 30 | ~$0.005 | $0.15 |
| Embedding (D5) | 30 | ~$0.0005 | $0.015 |
| **per-character total** | | | **≈ $0.26** |
| **per-PR (2 角色)** | | | **≈ $0.52** |

**月度预算**:
- 假设每天 5 个相关 PR → 5 × $0.52 × 30 = $78
- + nightly drift run: 30 × $0.52 = $15.6
- + baseline 重生成（季度 1 次）: ~$2
- **月预算上限设 $100**（留 buffer）

### 6.2 Cost Cap 三层

复用 `docs/design/integration_test_pyramid.md` §8 的三层；额外加：

- **L4 — Per-character cap**: 单角色 regression ≤ $1.0
- **L5 — Daily cap**: 全 voice drift 24h 内 ≤ $10

超出 → conftest 拒绝跑 + Slack alert。

### 6.3 紧急 disable

```
ENABLE_VOICE_DRIFT=false   # 环境变量，默认 true on main
```

只有 HUMAN（不是 AI）能在 PR 里加这一行，且要在 description 解释为什么 disable + 计划啥时恢复。

---

## 7. Folder Structure 与文件清单

```
backend/heart/qa/                      ← 新 package
├── __init__.py
├── voice_judge.py                     ← LLM-as-judge wrapper (走 ModelRouter)
├── drift_scorer.py                    ← 5-dim 聚合
├── baseline_runner.py                 ← 生成 baseline（多次取并集）
├── regression_runner.py               ← per-PR 跑 + 出 scores.jsonl
├── report_builder.py                  ← scores.jsonl → HTML
└── anti_pattern_regex.py              ← 复用 SS05 的 anti_pattern 扫描，独立可测

config/voice_drift/
├── canonical_prompts.yaml             ← 30 prompts
├── thresholds.yaml                    ← drift_threshold, anti_pattern_tolerance, dim weights
└── README.md                           ← 改动权限说明

backend/tests/golden/voice_baselines/
├── rin_baseline.jsonl
├── dorothy_baseline.jsonl
└── README.md                           ← 何时生成、由谁 approve

backend/tests/live/
├── test_voice_drift_regression.py     ← @pytest.mark.live + @pytest.mark.drift
└── test_voice_dna_baseline.py         ← baseline 生成测试（只在 --gen-baseline 时跑）

backend/scripts/
└── run_voice_drift.py                 ← CLI: generate-baseline / regress / report

docs/
├── design/soul_drift_regression.md    ← 本文档
└── soul_drift_baseline_update.md      ← baseline 升级 SOP（实施时产出）

artifacts/voice_drift/                 ← CI 写入；本地 gitignored
└── <branch>_<sha>/
    ├── scores.jsonl
    ├── summary.json
    ├── diff_report.html
    └── judge_traces/

Makefile targets:
- voice-baseline:     生成 baseline（HUMAN 触发）
- voice-regress:      per-PR 回归
- voice-report:       重 render 一次 HTML
```

---

## 8. CLI 设计

```
$ python backend/scripts/run_voice_drift.py --help
usage: run_voice_drift.py {generate-baseline,regress,report,calibrate}

generate-baseline:
  --character {rin,dorothy,all}     必填
  --runs N                          每 prompt 跑几次（默认 3）
  --dry-run                         不调 LLM，只打 plan + 估价
  --output PATH                     默认 backend/tests/golden/voice_baselines/<char>.jsonl.proposed

regress:
  --against PATH                    baseline 路径，默认上面的目录
  --character {rin,dorothy,all}     必填
  --pr-number N                     用于命名 artifacts
  --max-cost FLOAT                  default 0.55 (per-PR)
  --strict                          一个 anti_pattern 即非零 exit

report:
  --scores PATH                     scores.jsonl
  --output PATH                     /tmp/heart_drift_report.html

calibrate:
  --from-runs N                     用最近 N 次 regression 校准阈值
  --propose-only                    只输出建议，不写 config
```

---

## 9. 与 Phase 7 Cut Criteria 的关系

PHASE_7_PLUS §1.9 Phase 7 Cut Criteria 含：
- ☐ `Voice drift baseline 已存盘（rin + dorothy）`

本设计在 §10 把这个 criterion 拆成具体的 □□□。

---

## 10. Cut Criteria（Phase 7 §1.4 完工判定）

```
□ docs/design/soul_drift_regression.md  HUMAN sign-off  ← 本文
□ config/voice_drift/canonical_prompts.yaml  30 条 prompts 已审稿（HUMAN: 主创 + 心理顾问）
□ config/voice_drift/thresholds.yaml         初始阈值落地
□ backend/heart/qa/{voice_judge,drift_scorer,baseline_runner,regression_runner,report_builder,anti_pattern_regex}.py
□ make voice-baseline 跑通：rin + dorothy 各 90 entries (~$0.80 一次性)
□ make voice-regress 跑通：against current main, 出 HTML
□ /tmp/heart_drift_report.html 可读且 HUMAN 看了 30s 能判定 OK
□ docs/soul_drift_baseline_update.md 流程文档落地
□ Tier C CI gate 已联动：drift fail → block release tag
□ 一次 baseline 升级演练（在 staging 改一处 voice_dna → 跑 → 走 §5.3 流程 → 升级 → 回滚）
□ Cost dashboard 显示 voice drift 月成本 < $100
```

---

## 11. Risks & Open Questions

| # | Risk / Question | 决策 / 缓解 |
|---|----------------|-------------|
| R1 | **LLM-judge 自评偏差** | 见 §3.6；spot-check + 季度 calibration |
| R2 | **30 prompts 不够代表性** | Phase 8 起每月收集真实用户 messages，匿名化后扩到 50 |
| R3 | **stochastic flake 让人疲劳** | 3 次取并集 (baseline) + median (regression)；月度 flake rate > 5% → 加 prompt 多样性 |
| R4 | **DeepSeek 突然下线 / 改版** | Baseline JSONL 记录 `model_revision`；revision 变 → 强制 重 baseline，PR description 必须说明 |
| R5 | **HUMAN 看 HTML 报告太累 → 走个过场** | Top-3 drift prompts 用红字突出；< 100 字 critique 必填 |
| R6 | **改 soul_spec 同时改 Composer → 不清楚谁导致 drift** | 强制 PR 一次只动一类（Composer 改归 Composer PR；soul_spec 改归 soul_spec PR）— governance.md 中记入 |
| R7 | **Embedding (D5) 成本被低估** | 实施时埋 cost tracker；超 10% 启用 cache |
| Q1 | **要不要给 Critic Agent 也加 drift gating？** | Phase 8 再说；现在 Critic 是事中校验，drift 是事后 regression，错配 |
| Q2 | **支持 multi-LLM provider 后是否要 per-provider baseline？** | 是 — 但 Law 6 现在限定 DeepSeek-only，所以 NOT NOW |
| Q3 | **多语言 (zh-CN / en) 是否各一套 baseline？** | 是 — 现在只有 zh-CN soul_spec；en 角色加入时同步加 baseline 文件，**不复用** |
| Q4 | **golden_dialogues 已经有 expected response，要不要直接用作 baseline？** | 不直接用 — golden_dialogues 是单一 expected；baseline 要分布。但 cp-001 … cp-010 引用 gd 的 user_message |

---

## 12. 与现有 spec / 工具的耦合

### 12.1 复用

- `soul_specs/{char}/v1.0.0.yaml` 的 `voice_dna` + `anti_patterns` + `humor_profile` → judge prompt 直接读
- `soul_specs/{char}/v1.0.0.yaml` 的 `regression_tests` 段（line 750+）→ 当作 unit-level checklist，与本 suite 互补
- `backend/heart/ss05_composer/anti_pattern_filter.py`（已在 feat 分支）→ §3.3 D2 直接调
- `backend/heart/infra/llm/router.py` → 所有 LLM 调用走它，遵守 Law 6
- `backend/heart/infra/llm_cost_tracker.py` → §6.2 三层 cap

### 12.2 新增

- `backend/heart/qa/` 整 package（见 §7）
- `config/voice_drift/` 整目录
- `backend/tests/golden/voice_baselines/` 数据目录

### 12.3 修改

- `pytest.ini`：注册 `drift` marker
- CODEOWNERS：`backend/tests/golden/voice_baselines/` 需 HUMAN 主创签字
- `Makefile`：3 个新 target
- `.github/workflows/`：新 workflow `voice-drift.yml`（Tier C drift gate）

---

## 13. 实施顺序

每一步独立 PR（建议合在一个 epic branch 上分批推）：

```
PR-A  qa-package-skeleton
      └── backend/heart/qa/ 全部 stub（接口齐，实现空）+ unit tests for shape

PR-B  anti-pattern-regex-extracted
      └── 把 anti_pattern_regex 从 ss05_composer 抽到 qa/anti_pattern_regex.py
          ss05_composer 改为 import 它（无行为变化）

PR-C  voice-judge-implementation
      └── voice_judge.py + drift_scorer.py + judge prompt + 单测（用 fake LLM）

PR-D  config-and-prompts
      └── canonical_prompts.yaml (30 条) + thresholds.yaml + README

PR-E  baseline-runner + cli
      └── baseline_runner.py + scripts/run_voice_drift.py generate-baseline

PR-F  baseline-generation (花真钱)
      └── 跑 baseline，commit JSONL；HUMAN sign-off

PR-G  regression-runner + report-builder
      └── regression_runner.py + report_builder.py + tests/live/test_voice_drift_regression.py

PR-H  ci-wiring + docs/soul_drift_baseline_update.md
      └── .github/workflows/voice-drift.yml + Makefile + 流程文档
```

---

## 14. 安全 / 合规考量

- Baseline JSONL 含 LLM 完整输出。如果未来有用户对话进入 prompts → 必须先匿名化 + 法务复核（Phase 12.7 GDPR 之前不允许把用户数据入 baseline）。
- LLM-judge raw traces 落 `artifacts/.../judge_traces/`：CI artifact 加密 + 90 天后自动删除。
- 月度 voice drift dashboard 不暴露给 HR / external auditor — 它代表 "AI 们觉得这个角色像不像她"，不是产品事实。

---

## 15. 引用

- `engineering_execution/PRACTICAL_MODEL_GUIDE_PHASE_7_PLUS.md` §1.4
- `docs/design/integration_test_pyramid.md` Tier C（本设计的承载层）
- `runtime_specs/01_identity_anchor_soul_spec.md` §6.5 (drift detection mechanism B)
- `runtime_specs/05_persona_composition_runtime.md` §3 (Composer architecture)
- `runtime_specs/05_persona_composition_runtime.md` §4 (Anti-drift Injector)
- `soul_specs/rin/v1.0.0.yaml` §voice_dna + §anti_patterns + §regression_tests
- `soul_specs/dorothy/v1.0.0.yaml` （同上结构）
- `soul_specs/{char}/golden_dialogues/gd-*.yaml`（10 个/角色，被 §2.1 引用）
- `engineering_execution/ENGINEERING_LAWS.md` Law 2 (Soul is Sacred), Law 6 (Model Routing Strict)

---

**Document Version**: 1.0
**Last Updated**: 2026-05-24
**Sign-off Required**: HUMAN(主创) + HUMAN(心理顾问) + HUMAN(工程主架) — 三方签
