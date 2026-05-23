"""
SS05 Persona Composition Runtime

Core components:
- LayerAggregator: Parallel upstream layer aggregation (§3.2 + §10.3)
- PromptLayer: Standardized layer data structure (§5.1)
- ConflictResolver: Deterministic post-aggregation sanity pass (§3.3 step 2 + §6.4)
- AntiDriftInjector: Anchor mode decision + REINFORCE injection (§3.3 step 3 + §3.6)
- TokenBudgetAllocator: Priority-based budget allocation + compression (§3.3 step 4 + §10.5-10.6)
- ModalityAdapter: Adapt layers per delivery channel — text/voice/image-caption (§3.3 step 5)
- Composer: Final prompt assembly for the main LLM call (§3.3 step 6)

Author: 心屿团队
"""

from .anti_drift_injector import (
    AntiDriftInjector,
    InjectionResult,
    inject_anchor,
)
from .anti_pattern_filter import (
    AntiPatternFilter,
    FilterResult,
    FilterViolation,
    filter_text,
)

from .composer import (
    Composer,
    CompositionTrace,
    LayerInclusion,
    PromptBundle,
    _estimate_tokens,
    _format_layer,
    _order_layers,
    assemble,
)
from .conflict_resolver import (
    AggregatedLayers,
    ConflictResolutionEntry,
    ConflictResolutionGap,
    ConflictResolver,
    ResolutionVerb,
    ResolvedComposition,
    resolve,
)
from .layer_aggregator import (
    DEFAULT_LAYER_TIMEOUTS,
    LAYER_AGGREGATION_TIMEOUT,
    LAYER_MIN_TOKENS,
    LAYER_PRIORITIES,
    LayerAggregator,
    PromptLayer,
)
from .modality_adapter import (
    LLMCallParams,
    Modality,
    ModalityAwareComposition,
    ModalityDirectives,
    VALID_MODALITIES,
    VoiceDirectives,
    ImageCaptionDirectives,
    TextDirectives,
    adapt,
    get_llm_params,
)
from .reroll import (
    RerollHandler,
    RerollAttempt,
    RerollResult,
    get_fallback,
    list_fallback_categories,
)
from .streaming_anti_pattern import (
    StreamingPreFilter,
    PreFilterHalt,
    PreFilterStats,
    build_prefilter_from_soul,
)
from .token_budget import (
    AllocatedLayer,
    AllocatedLayers,
    LayerCompressor,
    TokenCounter,
    allocate,
)

__all__ = [
    # Layer Aggregator
    "LayerAggregator",
    "PromptLayer",
    "DEFAULT_LAYER_TIMEOUTS",
    "LAYER_AGGREGATION_TIMEOUT",
    "LAYER_PRIORITIES",
    "LAYER_MIN_TOKENS",
    # Anti-Drift Injector
    "AntiDriftInjector",
    "InjectionResult",
    "inject_anchor",
    # Anti-Pattern Filter
    "AntiPatternFilter",
    "FilterResult",
    "FilterViolation",
    "filter_text",
    # Conflict Resolver
    "ConflictResolver",
    "AggregatedLayers",
    "ResolvedComposition",
    "ConflictResolutionEntry",
    "ConflictResolutionGap",
    "ResolutionVerb",
    "resolve",
    # Token Budget
    "TokenCounter",
    "LayerCompressor",
    "AllocatedLayer",
    "AllocatedLayers",
    "allocate",
    # Modality Adapter
    "Modality",
    "VALID_MODALITIES",
    "ModalityAwareComposition",
    "ModalityDirectives",
    "VoiceDirectives",
    "ImageCaptionDirectives",
    "TextDirectives",
    "LLMCallParams",
    "adapt",
    "get_llm_params",
    # Composer
    "Composer",
    "PromptBundle",
    "LayerInclusion",
    "CompositionTrace",
    "assemble",
    # Reroll
    "RerollHandler",
    "RerollAttempt",
    "RerollResult",
    "get_fallback",
    "list_fallback_categories",
    # Streaming Anti-Pattern Pre-Filter
    "StreamingPreFilter",
    "PreFilterHalt",
    "PreFilterStats",
    "build_prefilter_from_soul",
]
