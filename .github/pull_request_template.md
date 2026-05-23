<!--
心屿 (Heart) — Pull Request

Fill every field. PRs missing required fields will be blocked by CI.
See docs/GOVERNANCE.md for what each field means.
-->

## Summary

<!-- 1–3 sentences. What does this PR do? Why now? -->

## Spec Reference

<!--
Cite the runtime_specs section this PR implements / changes / depends on.
Format: runtime_specs/0X_<name>.md §N.N
If "no spec touched", write "N/A — internal refactor / infra only".
-->

- Spec:
- Section(s):

## Invariants Touched

<!--
List every INV-X-N this PR touches or depends on.
"None" is acceptable only for non-runtime PRs (CI, docs, tooling).
-->

- [ ] None
- INV-X-N:

## State / Topology Changes

| Question                                              | Yes / No | Detail |
|-------------------------------------------------------|----------|--------|
| Database schema change (Alembic migration added)?     |          |        |
| Cross-subsystem contract change?                      |          |        |
| Agent / orchestration topology change?                |          |        |
| PromptBundle structure change?                        |          |        |
| Soul Spec / voice_dna change?                         |          |        |
| Safety / care_path / wellbeing config change?         |          |        |
| Cost model change (LLM provider, model, route)?       |          |        |

Any "Yes" above ⇒ HUMAN review required (see engineering_execution/HUMAN_REVIEW_CHECKLIST.md).

## Tests

| Tier        | Added | Modified | Notes |
|-------------|-------|----------|-------|
| Unit        |       |          |       |
| Contract    |       |          |       |
| Integration |       |          |       |
| Live (real DeepSeek, cost-capped) |  |  |   |
| Property (Hypothesis)              |  |  |  |

- [ ] `pytest tests/unit -q` passes locally
- [ ] `make lint` passes locally
- [ ] No new test marked `@pytest.mark.skip` without a tracking issue

## AI Provenance

<!--
Per docs/AI_CONTEXT.md §7 + engineering_execution/AI_MODEL_ROUTING.md.
-->

- Primary model: <!-- e.g. CC-S46 / CC-Opus / Codex-DeepSeek -->
- Session ID(s): <!-- if applicable -->
- Token est: <!-- rough k-tokens -->
- Anything surprising the AI produced (judgment calls, non-obvious tradeoffs)?

## Drift Risk Self-Assessment

| Dimension               | Risk (low / med / high) | Mitigation |
|-------------------------|-------------------------|------------|
| Soul voice drift        |                         |            |
| Architecture drift      |                         |            |
| State invariant drift   |                         |            |
| Prompt drift            |                         |            |

Any `high` ⇒ link the drift-detection test or audit that justifies merging.

## STATUS.md Update

- [ ] `STATUS.md` `Last updated` bumped
- [ ] `STATUS.md` §2 next-task table updated (if this PR closes a listed task)

## Governance Checklist

- [ ] No new root-level `.md` files (except README/STATUS/AGENTS)
- [ ] No `*_IMPLEMENTATION_SUMMARY.md` / `*_COMPLETION_REPORT.md` / `*_CHANGES_SUMMARY.md` introduced
- [ ] No direct `import anthropic` / `import openai` (Law 6 — must go through `ModelRouter`)
- [ ] No edits to `runtime_specs/**`, `soul_specs/**`, `config/safety_keywords.yaml`, `config/care_path_responses/**`, `.claude/CLAUDE.md`, `docs/GOVERNANCE.md` (these require HUMAN approval — flag explicitly if intentional)

## Reviewer Notes

<!-- What should the reviewer look at first? Where is the risk concentrated? -->
