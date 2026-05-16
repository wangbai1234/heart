# LLM Provider Abstraction

**Status**: ✅ Implemented and tested (16/16 tests passing)  
**Spec Reference**: SS07 §3.5 + §6.1  
**MVP Strategy**: DeepSeek-only (simplified, cost-effective)

---

## Overview

Unified abstraction layer for LLM providers supporting:

- **Streaming and non-streaming calls**
- **Cost estimation**
- **Circuit breaker integration**
- **Provider registry and failover**
- **Type-safe interface**

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         LLM Provider Abstraction            │
├─────────────────────────────────────────────┤
│                                             │
│  base.py                                    │
│  ├─ LLMProvider (abstract)                  │
│  ├─ LLMRequest / LLMResponse                │
│  ├─ StreamChunk / CostEstimate              │
│  └─ CircuitBreakerInterface                 │
│                                             │
│  Implementations:                           │
│  ├─ anthropic.py → DeepSeekV4ProProvider    │
│  │   (deepseek-reasoner, high quality)     │
│  └─ deepseek.py → DeepSeekV4FlashProvider   │
│      (deepseek-chat, fast & cheap)         │
│                                             │
│  registry.py                                │
│  └─ ProviderRegistry (lookup + init)        │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Environment Setup

Add to `.env`:

```bash
DEEPSEEK_API_KEY=sk-xxx...xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
MAIN_LLM_MODEL=deepseek-reasoner
CHEAP_LLM_MODEL=deepseek-chat
```

### 2. Initialize Registry

```python
from heart.infra.llm_providers.registry import initialize_registry

# Initialize once at app startup
registry = initialize_registry()
```

### 3. Make LLM Calls

#### Non-streaming (main response)

```python
from heart.infra.llm_providers import get_provider_for_model, LLMRequest, Message, MessageRole

# Get provider
provider = get_provider_for_model("deepseek-reasoner")

# Build request
request = LLMRequest(
    messages=[
        Message(role=MessageRole.SYSTEM, content="You are a helpful AI companion."),
        Message(role=MessageRole.USER, content="Hello!"),
    ],
    model="deepseek-reasoner",
    temperature=0.7,
    max_tokens=500,
)

# Call
response = await provider.call(request)
print(response.content)
print(f"Cost: ${response.usage['total_tokens'] * 0.00055}")
```

#### Streaming (main response)

```python
# Stream response
async for chunk in provider.stream(request):
    if chunk.content:
        print(chunk.content, end="", flush=True)
    
    # Final chunk has usage stats
    if chunk.finish_reason:
        print(f"\n\nTokens used: {chunk.usage['total_tokens']}")
```

#### Cheap model (classification, encoding)

```python
# Get flash provider for cheap operations
provider = get_provider_for_model("deepseek-chat")

request = LLMRequest(
    messages=[
        Message(role=MessageRole.USER, content="Classify: 'I love this!'"),
    ],
    model="deepseek-chat",
    temperature=0.3,
    json_mode=True,  # JSON output
)

response = await provider.call(request)
result = json.loads(response.content)
```

---

## API Reference

### LLMProvider (Abstract Base)

All providers implement:

```python
class LLMProvider:
    async def call(request: LLMRequest) -> LLMResponse
    async def stream(request: LLMRequest) -> AsyncIterator[StreamChunk]
    def estimate_cost(prompt_tokens, completion_tokens, model) -> CostEstimate
    def count_tokens(text: str, model: str) -> int
```

### LLMRequest

```python
@dataclass
class LLMRequest:
    messages: List[Message]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stream: bool = False
    json_mode: bool = False
    metadata: Dict[str, Any] = {}
```

### LLMResponse

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    finish_reason: str
    usage: Dict[str, int]  # {prompt_tokens, completion_tokens, total_tokens}
    provider: str
    metadata: Dict[str, Any]
```

### StreamChunk

```python
@dataclass
class StreamChunk:
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
```

---

## Cost Estimation

### Pricing (per 1M tokens)

| Model | Input | Output | Use Case |
|-------|-------|--------|----------|
| `deepseek-reasoner` (V4-pro) | $0.55 | $2.19 | Main responses |
| `deepseek-chat` (V4-flash) | $0.14 | $0.28 | Cheap operations |

### Estimate Before Call

```python
provider = get_provider_for_model("deepseek-reasoner")

# Estimate cost
cost = provider.estimate_cost(
    prompt_tokens=100,
    estimated_completion_tokens=50,
    model="deepseek-reasoner",
)

print(f"Estimated cost: ${cost.total_cost_usd:.6f}")
# Estimated cost: $0.000165
```

### Actual Cost After Call

```python
response = await provider.call(request)

# Calculate actual cost
input_cost = (response.usage['prompt_tokens'] / 1_000_000) * 0.55
output_cost = (response.usage['completion_tokens'] / 1_000_000) * 2.19
total = input_cost + output_cost

print(f"Actual cost: ${total:.6f}")
```

---

## Circuit Breaker Integration

The provider interface includes circuit breaker hooks (implementation by SS07):

```python
class CircuitBreakerInterface:
    def record_success(provider: str, model: str) -> None
    def record_failure(provider: str, model: str, error: Exception) -> None
    def is_open(provider: str, model: str) -> bool
```

Providers automatically:
- Check breaker state before calls
- Record successes/failures
- Raise `ProviderError(retriable=True)` when circuit is open

---

## Error Handling

### ProviderError

```python
try:
    response = await provider.call(request)
except ProviderError as e:
    print(f"Provider: {e.provider}")
    print(f"Model: {e.model}")
    print(f"Status: {e.status_code}")
    print(f"Retriable: {e.retriable}")
    
    if e.retriable:
        # Retry with exponential backoff
        await retry_with_backoff(...)
```

### Retriable Errors

HTTP status codes marked as retriable:
- `429` - Rate limit
- `500` - Internal server error
- `502` - Bad gateway
- `503` - Service unavailable
- `504` - Gateway timeout

---

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/unit/test_llm_providers.py -v
```

**Coverage**:
- ✅ Provider interface
- ✅ Non-streaming calls
- ✅ Streaming calls
- ✅ Cost estimation
- ✅ Circuit breaker integration
- ✅ Error handling
- ✅ Registry initialization
- ✅ JSON mode

---

## Integration with SS07

### Model Router (to be implemented)

The Model Router will use these providers:

```python
class ModelRouter:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
    
    async def call_main(self, messages, agent_name) -> str:
        """Main response using deepseek-reasoner."""
        provider = self.registry.get_provider_for_model("deepseek-reasoner")
        response = await provider.call(...)
        return response.content
    
    async def stream_main(self, messages, agent_name) -> AsyncIterator[str]:
        """Streaming main response."""
        provider = self.registry.get_provider_for_model("deepseek-reasoner")
        async for chunk in provider.stream(...):
            if chunk.content:
                yield chunk.content
    
    async def call_cheap(self, messages, json_mode=False, agent_name="") -> str:
        """Cheap operations using deepseek-chat."""
        provider = self.registry.get_provider_for_model("deepseek-chat")
        response = await provider.call(...)
        return response.content
```

---

## Migration Path

### Current (MVP)

```
All LLM calls → ProviderRegistry → DeepSeek (reasoner + chat)
```

### V1 (Add Fallback)

```
All LLM calls → ProviderRegistry → DeepSeek (primary)
                                   ↓ (if circuit breaker open)
                                  Claude (fallback)
```

**Changes needed**:
1. Add `anthropic_real.py` with Claude provider
2. Update `registry.py` to register fallback
3. **No changes to subsystems!** ✅

### V2 (Optimize Cost)

```
High creativity → Claude Sonnet
Normal tasks    → DeepSeek Chat  
Low cost        → Self-hosted model
```

**Changes needed**:
1. Add new provider implementations
2. Update router selection logic
3. **No changes to subsystems!** ✅

---

## Files Created

```
backend/heart/infra/llm_providers/
├── __init__.py                # Public API exports
├── base.py                    # Abstract base class + types
├── anthropic.py               # DeepSeek V4-pro provider
├── deepseek.py                # DeepSeek V4-flash provider
├── registry.py                # Provider registry + init
└── README.md                  # This file

backend/tests/unit/
└── test_llm_providers.py      # Unit tests (16 tests, all passing)
```

---

## Next Steps

1. ✅ **Done**: Provider abstraction implemented
2. **Next**: Implement Model Router (SS07 §3.5)
3. **Then**: Integrate into subsystems (SS02, SS03, SS05, SS07)
4. **Later**: Add cost tracking and alerting

---

## Related Documentation

- **Spec**: `/runtime_specs/07_agent_orchestration.md` §3.5, §6.1
- **Strategy**: `/CHANGES_SUMMARY.md`
- **Tests**: `tests/unit/test_llm_providers.py`

---

**Last Updated**: 2026-05-16  
**Status**: ✅ Ready for Model Router integration
