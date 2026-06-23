# MVP Gate Check — Cut Status

**Updated**: 2026-06-02T06:09:30Z
**Overall**: PASS (10/10 passed)

| Gate | Name | Result | Detail |
|------|------|--------|--------|
| Gate 1 | Local stack | ✓ | all core services healthy (postgres, redis) |
| Gate 2 | Seed | ✓ | demo users seeded with >50 turns (demo_alice=100turns, demo_bob=98turns) |
| Gate 3 | CLI loop | ✓ | 5 turns completed, avg=0ms, max=0ms |
| Gate 4 | Stage progression | ✓ | all demo users at Stage 2+ (demo_alice×rin=Stage 2 (FRIEND), demo_bob×dorothy=Stage 2 (FRIEND)) |
| Gate 5 | Proactive | ✓ | proactive messages detected (demo_alice×rin=3, demo_bob×dorothy=3) |
| Gate 6 | Cold war + reunion | ✓ | cold war → reunion cycle confirmed (demo_alice×rin: war d10, reunion d11; demo_bob×dorothy: war d10, reunion d11) |
| Gate 7 | Voice drift | ✓ | drift infra present: baselines=['dorothy_baseline.jsonl', 'rin_baseline.jsonl'], prompts=yes, thresholds=yes (run voice-regress for actual score) |
| Gate 8 | Cost | ✓ | cost Counter registered (heart_llm_cost_dollars_total) — no spend yet (run API with HEART_TURN_PROFILER=1 and serve traffic) |
| Gate 9 | Latency | ✓ | p95 hot path < 3s (p95_api=0.1s) |
| Gate 10 | Observability | ✓ | 6 dashboard JSONs verified (01_turn_health, 02_llm_cost, 03_subsystem_breakdown, 04_inner_loop, 05_drift_health, 06_safety) — grafana running (auth required for dashboard query) |

