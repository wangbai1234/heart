# LLM Providers Package - Status

**Current status**: Architecture placeholder — NOT ACTIVE in production code.

## Context

This package (`heart.infra.llm_providers`) was designed as a multi-provider LLM abstraction layer with:
- Provider registry system
- Circuit breaker integration
- Multiple provider support (DeepSeek Pro, DeepSeek Flash)
- Fake provider for testing

However, the active LLM routing layer is currently **`heart.infra.llm`**, which uses a simpler single-provider implementation.

## Architecture Decision (2026-05-24)

Per the 2026-05-23 architecture audit finding F16:

> Two parallel LLM packages exist; only one is wired. `infra/llm/` (router → single DeepSeekProvider) is what callers use. `infra/llm_providers/` (registry + multiple providers + circuit-breaker interface + fake.py) is orphan code.

**Decision**: Preserve `llm_providers/` as future-ready architecture but keep `llm/` as the active path.

**Rationale**:
- `llm/` is simpler and meets current MVP needs (single DeepSeek provider)
- `llm_providers/` has superior architecture (registry, failover, extensibility) for future multi-provider support
- Migration to `llm_providers` deferred until multi-provider need emerges (e.g., Anthropic fallback, cost optimization)

## When to Migrate

Migrate from `llm/` to `llm_providers/` when:
1. Need to add a second provider (Anthropic, OpenAI, etc.)
2. Need circuit breaker / failover logic
3. Need per-provider cost tracking beyond the current simple router

## Current Provider Implementations

- `deepseek_pro.py`: DeepSeek V4-pro (deepseek-reasoner) — high-quality, reasoning model
- `deepseek.py`: DeepSeek V4-flash (deepseek-chat) — fast, cheap model
- `fake.py`: Deterministic fake provider for testing (golden file replay)
- `base.py`: Abstract base + protocols

**Note**: `deepseek_pro.py` was previously misnamed `anthropic.py` (fixed 2026-05-24).

## For Future Maintainers

If you're adding a second LLM provider:
1. Do NOT add it to `infra/llm/provider.py`
2. Instead, add a new provider class here (`infra/llm_providers/<name>.py`)
3. Refactor `infra/llm/router.py` to use `ProviderRegistry.get_provider_for_model(...)`
4. Delete the old `infra/llm/provider.py`
5. Update this STATUS.md to mark the package as ACTIVE

---

**Last updated**: 2026-05-24
**Audit reference**: docs/audit/2026-05-23_architecture_audit.md, Finding F16
