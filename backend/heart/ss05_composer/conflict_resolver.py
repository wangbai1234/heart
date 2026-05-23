"""
Conflict Resolver — SS05 Persona Composition Runtime §3.3 step 2 + §6.4

Step 2 of the per-turn composition flow: after the Layer Aggregator returns
the parallel block fetch, decide deterministically what survives when two
layers carry instructions that cannot both be honored in a single response.

Design contract (see docs/design/conflict_resolver.md):
- Deterministic: same inputs ⇒ same resolved layer list.
- No LLM calls (PC-12). No Chinese paraphrasing. Only pre-rendered variants,
  masks, drops, attenuations, defers.
- Auditable: every decision writes a ConflictResolutionEntry to the trace.
- Single direction per row: matrix is keyed by (winner, loser); winners do not
  change; losers are adjusted or dropped.
- Care Path Always Wins: when safety.level == "PURPLE", CR-9 + CR-13 run
  unconditionally and take precedence over any other content concern.

Resolution verbs (the only five permitted; see §3 of design doc):
  DROP            — remove loser layer / sub-suggestion entirely
  MASK            — strip a sub-segment from the loser; keep the rest
  SWITCH_VARIANT  — replace loser content with a pre-declared variant
  ATTENUATE       — lower an intensity field on the loser
  DEFER           — move loser behind winner in injection order

If a conflict cannot be resolved by one of the five verbs (e.g. variant
missing), a ConflictResolutionGap is emitted and the resolver falls back
to PC-2 with DROP. Failure mode is explicit, never silent.

Author: 心屿团队
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from heart.ss05_composer.layer_aggregator import PromptLayer

logger = structlog.get_logger()


# ============================================================
# Resolution Verbs
# ============================================================


class ResolutionVerb:
    DROP = "DROP"
    MASK = "MASK"
    SWITCH_VARIANT = "SWITCH_VARIANT"
    ATTENUATE = "ATTENUATE"
    DEFER = "DEFER"
    NOOP = "NOOP"  # CR-6: trust upstream subsystem


# ============================================================
# Stage Ordering — for stage-gated decisions
# ============================================================

STAGE_ORDER: dict[str, int] = {
    "STRANGER": 0,
    "ACQUAINTANCE": 1,
    "FRIEND": 2,
    "CONFIDANT": 3,
    "ROMANTIC_INTEREST": 4,
    "ROMANTIC": 4,  # alias used in design doc
    "LOVER": 5,
    "BONDED": 6,
}


def _stage_rank(stage: Optional[str]) -> int:
    """Numeric ordering for a stage label. Unknown stage → 0 (STRANGER)."""
    if stage is None:
        return 0
    return STAGE_ORDER.get(stage.upper(), 0)


# ============================================================
# Safety Levels — escalation order
# ============================================================

SAFETY_ORDER: dict[str, int] = {
    "GREEN": 0,
    "YELLOW": 1,
    "ORANGE": 2,
    "PURPLE": 3,
}

CARE_PATH_LEVELS: frozenset[str] = frozenset({"PURPLE"})
"""Safety levels that activate the Care Path (CR-9 + CR-13 hard-coded high priority)."""


# ============================================================
# Trace Entries
# ============================================================


@dataclass
class ConflictResolutionEntry:
    """One row in CompositionTrace.conflicts_resolved (§4.2).

    Format matches the design doc §5 example trace entry.
    """

    layer_a: str  # winner (higher PC-2 precedence)
    layer_b: str  # loser
    rule_applied: str  # e.g. "CR-1", "CR-11"
    resolution: str  # human-readable, e.g. "SWITCH_VARIANT(anger → vulnerable_anger)"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictResolutionGap:
    """A conflict the resolver detected but could not resolve.

    Emitted when a needed variant is missing, when a required Soul field is
    absent, etc. The resolver falls back to PC-2 + DROP and continues; this
    record is the audit trail of "we knew, we logged, we coped."
    """

    rule_id: str
    reason: str  # e.g. "missing_variant", "missing_care_path_voice"
    detail: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Inputs / Outputs
# ============================================================


@dataclass
class AggregatedLayers:
    """Resolver input — the bundle returned by LayerAggregator + cross-layer
    signals that PC-2 forces but parallel fetching prevents joining at source.

    Layer carriers (each is an optional PromptLayer from the aggregator):
      anchor       — SS01 Anchor Block
      memory       — SS02 Memory Context Block
      emotion      — SS03 Emotion Context Block
      relationship — SS04 Relationship / Stage Envelope
      inner_state  — SS06 Inner State Block
      safety       — SS07 Safety Layer (carries metadata["level"])
      scene        — Scene Detector output

    plus position-pinned layers that the resolver never modifies:
      user_message, response_directive

    plus cross-cutting signals:
      turn_signals — e.g. {"acute_stress": bool, "acute_stress_level": float}
      modality     — "text" | "voice"
    """

    anchor: Optional[PromptLayer] = None
    memory: Optional[PromptLayer] = None
    emotion: Optional[PromptLayer] = None
    relationship: Optional[PromptLayer] = None
    inner_state: Optional[PromptLayer] = None
    safety: Optional[PromptLayer] = None
    scene: Optional[PromptLayer] = None
    user_message: Optional[PromptLayer] = None
    response_directive: Optional[PromptLayer] = None

    turn_signals: dict[str, Any] = field(default_factory=dict)
    modality: str = "text"

    @classmethod
    def from_layer_list(
        cls,
        layers: list[PromptLayer],
        *,
        turn_signals: Optional[dict[str, Any]] = None,
        modality: str = "text",
    ) -> "AggregatedLayers":
        """Convenience constructor from the flat list returned by LayerAggregator."""
        bag: dict[str, PromptLayer] = {}
        for layer in layers:
            bag.setdefault(layer.layer_type, layer)
        return cls(
            anchor=bag.get("anchor_full") or bag.get("anchor_light") or bag.get("anchor_reinforce"),
            memory=bag.get("memory_context"),
            emotion=bag.get("emotion_context"),
            relationship=bag.get("relationship_context"),
            inner_state=bag.get("inner_state"),
            safety=bag.get("safety"),
            scene=bag.get("scene_context"),
            user_message=bag.get("user_message"),
            response_directive=bag.get("response_directive"),
            turn_signals=turn_signals or {},
            modality=modality,
        )


@dataclass
class ResolvedComposition:
    """Resolver output — the post-resolution layer list + audit records.

    `layers` is the canonical ordered list (PC-1 first, position-pinned last,
    DEFER applied as ordering hint). `conflicts_resolved` and `gaps` populate
    CompositionTrace §4.2.
    """

    layers: list[PromptLayer]
    conflicts_resolved: list[ConflictResolutionEntry] = field(default_factory=list)
    gaps: list[ConflictResolutionGap] = field(default_factory=list)
    duration_ms: float = 0.0


# ============================================================
# Resolver
# ============================================================


class ConflictResolver:
    """Deterministic post-aggregation sanity pass (§3.3 step 2).

    Stateless — `resolve()` is pure given the inputs.

    Usage::

        resolver = ConflictResolver()
        composition = resolver.resolve(aggregated)
        for entry in composition.conflicts_resolved:
            ...   # write to CompositionTrace
    """

    def resolve(self, layers: AggregatedLayers) -> ResolvedComposition:
        """Apply the precedence matrix to the aggregated layer bundle.

        Returns a ResolvedComposition with the post-resolution layer list,
        the audit trail (`conflicts_resolved`), and any unresolvable conflict
        gaps. The input `layers` is treated as immutable: each PromptLayer
        the resolver modifies is deep-copied first so callers see no
        spooky-action-at-a-distance.
        """
        start = time.monotonic()

        # Snapshot — never mutate caller's layers.
        bundle = _copy_bundle(layers)
        trace: list[ConflictResolutionEntry] = []
        gaps: list[ConflictResolutionGap] = []

        # ─── Care Path Always Wins: PURPLE-gated rules first ──────────
        # Per design §7 + §10: when safety.level == PURPLE, CR-13 rewrites
        # the Anchor's default_tone to care_path_voice, and CR-9 drops
        # romantic sub-fields from InnerState. These take precedence over
        # every content-level concern that follows.
        safety_level = _safety_level(bundle.safety)
        if safety_level in CARE_PATH_LEVELS:
            self._apply_cr_13(bundle, trace, gaps)
            self._apply_cr_9(bundle, trace, gaps)

        # ─── Standard matrix in CR-id order ───────────────────────────
        self._apply_cr_1(bundle, trace, gaps)
        self._apply_cr_2(bundle, trace, gaps)
        self._apply_cr_3(bundle, trace, gaps)
        self._apply_cr_4(bundle, trace, gaps)
        self._apply_cr_5(bundle, trace, gaps)
        # CR-6 is a no-op (trust SS03), recorded only for observability when
        # the resolver can detect it would have triggered upstream.
        self._apply_cr_6(bundle, trace, gaps)
        self._apply_cr_7(bundle, trace, gaps)
        self._apply_cr_8(bundle, trace, gaps)
        # CR-9 already applied above when PURPLE; safe to re-call (idempotent
        # via guard inside the method). For non-PURPLE Care Path levels
        # (e.g. ORANGE → spec CR-9 row), it runs here.
        if safety_level not in CARE_PATH_LEVELS:
            self._apply_cr_9(bundle, trace, gaps)
        self._apply_cr_10(bundle, trace, gaps)
        self._apply_cr_11(bundle, trace, gaps)
        self._apply_cr_12(bundle, trace, gaps)
        # CR-13 already applied above when PURPLE.

        # ─── Assemble final layer list ────────────────────────────────
        result_layers = _flatten_bundle(bundle)
        result_layers = _apply_defer_ordering(result_layers)

        duration_ms = (time.monotonic() - start) * 1000.0

        logger.info(
            "conflict_resolver_complete",
            rules_applied=len(trace),
            gaps=len(gaps),
            duration_ms=round(duration_ms, 3),
            safety_level=safety_level,
        )

        return ResolvedComposition(
            layers=result_layers,
            conflicts_resolved=trace,
            gaps=gaps,
            duration_ms=duration_ms,
        )

    # ─── CR-1: Stage > Memory ─────────────────────────────────────────
    def _apply_cr_1(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """Mask memory episodes whose `min_stage` exceeds the current stage."""
        if bundle.memory is None or bundle.relationship is None:
            return
        stage = bundle.relationship.metadata.get("stage")
        if stage is None:
            return
        episodes = bundle.memory.metadata.get("episodes")
        if not episodes:
            return
        cur_rank = _stage_rank(stage)
        masked_ids: list[str] = []
        kept: list[dict[str, Any]] = []
        for ep in episodes:
            min_stage = ep.get("min_stage")
            if min_stage and _stage_rank(min_stage) > cur_rank:
                masked_ids.append(ep.get("id", "<unknown>"))
            else:
                kept.append(ep)
        if not masked_ids:
            return
        bundle.memory.metadata["episodes"] = kept
        bundle.memory.metadata["masked_episode_ids"] = (
            bundle.memory.metadata.get("masked_episode_ids", []) + masked_ids
        )
        trace.append(ConflictResolutionEntry(
            layer_a="SS04.stage_envelope",
            layer_b="SS02.memory_context",
            rule_applied="CR-1",
            resolution=f"MASK({len(masked_ids)} stage-gated episode(s))",
            metadata={"stage": stage, "masked_ids": masked_ids},
        ))

    # ─── CR-2: Stage > Emotion (心动 in pre-romantic) ─────────────────
    def _apply_cr_2(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """If emotion is 心动 / fluttered and stage < ROMANTIC_INTEREST, switch to tenderness variant."""
        if bundle.emotion is None or bundle.relationship is None:
            return
        emotion_name = bundle.emotion.metadata.get("emotion_name")
        stage = bundle.relationship.metadata.get("stage")
        if emotion_name not in ("心动", "fluttered"):
            return
        if _stage_rank(stage) >= STAGE_ORDER["ROMANTIC_INTEREST"]:
            return
        self._switch_variant(
            layer=bundle.emotion,
            variant_key=_first_present(bundle.emotion.variants, ("tenderness", "心动_tenderness")),
            rule_id="CR-2",
            winner_label="SS04.stage_envelope",
            loser_label="SS03.emotion_context",
            verb_detail="心动 → tenderness",
            trace=trace,
            gaps=gaps,
            on_missing_metadata={"emotion_name": emotion_name, "stage": stage},
        )

    # ─── CR-3: Soul.hard_never > Inner State sub-suggestion ──────────
    def _apply_cr_3(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """Drop InnerState sub-suggestions that match a Soul.hard_never pattern."""
        if bundle.anchor is None or bundle.inner_state is None:
            return
        hard_never = bundle.anchor.metadata.get("hard_never") or []
        if not hard_never:
            return
        subs = bundle.inner_state.metadata.get("sub_suggestions")
        if not subs:
            return
        dropped: list[str] = []
        kept: list[str] = []
        for s in subs:
            if any(pat in s for pat in hard_never):
                dropped.append(s)
            else:
                kept.append(s)
        if not dropped:
            return
        bundle.inner_state.metadata["sub_suggestions"] = kept
        bundle.inner_state.metadata["dropped_sub_suggestions"] = (
            bundle.inner_state.metadata.get("dropped_sub_suggestions", []) + dropped
        )
        trace.append(ConflictResolutionEntry(
            layer_a="SS01.soul_hard_never",
            layer_b="SS06.inner_state",
            rule_applied="CR-3",
            resolution=f"DROP({len(dropped)} sub-suggestion(s))",
            metadata={"dropped": dropped, "matched_patterns": hard_never},
        ))

    # ─── CR-4: L4 > L3 within Memory ─────────────────────────────────
    def _apply_cr_4(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """Mask L3 episodes flagged `contradicted_by_l4=True`."""
        if bundle.memory is None:
            return
        episodes = bundle.memory.metadata.get("episodes")
        if not episodes:
            return
        masked: list[str] = []
        kept: list[dict[str, Any]] = []
        for ep in episodes:
            if ep.get("contradicted_by_l4"):
                masked.append(ep.get("id", "<unknown>"))
                # Keep a marker — the audit log shows we dropped it.
                continue
            kept.append(ep)
        if not masked:
            return
        bundle.memory.metadata["episodes"] = kept
        bundle.memory.metadata["l3_contradicted_ids"] = (
            bundle.memory.metadata.get("l3_contradicted_ids", []) + masked
        )
        trace.append(ConflictResolutionEntry(
            layer_a="SS02.l4_identity",
            layer_b="SS02.l3_recall",
            rule_applied="CR-4",
            resolution=f"MASK({len(masked)} L4-contradicted L3 episode(s))",
            metadata={"contradicted_ids": masked},
        ))

    # ─── CR-5: Soul.cognitive_style > Memory shape ───────────────────
    def _apply_cr_5(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """If Soul.cognitive_style_max == 'short' and Memory expects long reply, attenuate."""
        if bundle.anchor is None or bundle.memory is None:
            return
        style_max = bundle.anchor.metadata.get("cognitive_style_max")
        memory_shape = bundle.memory.metadata.get("preferred_reply_shape")
        if style_max != "short" or memory_shape not in ("long", "medium"):
            return
        prev = bundle.memory.metadata.get("preferred_reply_shape")
        bundle.memory.metadata["preferred_reply_shape"] = "short_fragments"
        bundle.memory.is_compressible = True
        trace.append(ConflictResolutionEntry(
            layer_a="SS01.cognitive_style",
            layer_b="SS02.memory_context",
            rule_applied="CR-5",
            resolution="ATTENUATE(reply_shape: " + str(prev) + " → short_fragments)",
            metadata={"cognitive_style_max": style_max, "previous_shape": prev},
        ))

    # ─── CR-6: Soul > Emotion (no-op, SS03 handles) ──────────────────
    def _apply_cr_6(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """SS03 has already translated anger→coldness when shock_resistance=high.

        The resolver only records the no-op when it detects the upstream
        translation happened (emotion.metadata["resistance_translated"]).
        Otherwise this method is silent — CR-6 says: trust SS03.
        """
        if bundle.emotion is None:
            return
        if not bundle.emotion.metadata.get("resistance_translated"):
            return
        trace.append(ConflictResolutionEntry(
            layer_a="SS01.shock_resistance",
            layer_b="SS03.emotion_context",
            rule_applied="CR-6",
            resolution="NOOP(resolved upstream in SS03)",
            metadata={
                "original_emotion": bundle.emotion.metadata.get("original_emotion"),
                "translated_to": bundle.emotion.metadata.get("emotion_name"),
            },
        ))

    # ─── CR-7: Relationship envelope > Emotion (jealousy not allowed) ─
    def _apply_cr_7(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """If emotion is not in the stage's behavioral_envelope, switch to envelope-allowed variant."""
        if bundle.emotion is None or bundle.relationship is None:
            return
        emotion_name = bundle.emotion.metadata.get("emotion_name")
        envelope = bundle.relationship.metadata.get("behavioral_envelope")
        if not emotion_name or not envelope:
            return
        if emotion_name in envelope:
            return
        # Need to find an envelope-allowed variant. Convention from spec §6.4:
        # "jealousy → aggrieved+worry". The variant carries the alternate
        # rendering; the resolver does NOT synthesize one.
        variant_key = _first_present(
            bundle.emotion.variants,
            (f"{emotion_name}_envelope_safe", "envelope_safe", "aggrieved_worry"),
        )
        self._switch_variant(
            layer=bundle.emotion,
            variant_key=variant_key,
            rule_id="CR-7",
            winner_label="SS04.behavioral_envelope",
            loser_label="SS03.emotion_context",
            verb_detail=f"{emotion_name} → envelope-safe variant",
            trace=trace,
            gaps=gaps,
            on_missing_metadata={"emotion_name": emotion_name, "envelope": list(envelope)},
        )

    # ─── CR-8: Modality > Memory (voice + long) ──────────────────────
    def _apply_cr_8(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """In voice mode, defer the (long) memory layer behind tighter blocks.

        The resolver only flags via DEFER; actual compression is the Token
        Budget Allocator's job (next composition step).
        """
        if bundle.memory is None:
            return
        if bundle.modality != "voice":
            return
        if bundle.memory.token_count_estimate <= 200:
            return
        bundle.memory.metadata["defer"] = True
        trace.append(ConflictResolutionEntry(
            layer_a="composer.modality_voice",
            layer_b="SS02.memory_context",
            rule_applied="CR-8",
            resolution="DEFER(voice mode + long memory)",
            metadata={"token_count_estimate": bundle.memory.token_count_estimate},
        ))

    # ─── CR-9: Safety > Inner State (romantic in Care Path) ──────────
    def _apply_cr_9(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """When Care Path is active (or ORANGE escalation), drop romantic InnerState frames.

        Idempotent: if it has already run (marked via metadata flag), no-op.
        """
        if bundle.inner_state is None or bundle.safety is None:
            return
        level = _safety_level(bundle.safety)
        if level not in ("ORANGE", "PURPLE"):
            return
        if bundle.inner_state.metadata.get("_cr_9_applied"):
            return
        had_romantic = bool(bundle.inner_state.metadata.get("romantic"))
        if not had_romantic:
            return
        # DROP the romantic frame. The InnerState layer itself stays; we just
        # neutralize the romantic sub-field. CR-13 handles the Anchor's
        # care_path_voice in parallel.
        bundle.inner_state.metadata["romantic"] = False
        bundle.inner_state.metadata["_cr_9_applied"] = True
        bundle.inner_state.metadata["dropped_frames"] = (
            bundle.inner_state.metadata.get("dropped_frames", []) + ["romantic"]
        )
        trace.append(ConflictResolutionEntry(
            layer_a="SS07.safety",
            layer_b="SS06.inner_state",
            rule_applied="CR-9",
            resolution="DROP(romantic frame, care path active)",
            metadata={"safety_level": level},
        ))

    # ─── CR-10: Scene > Inner State (office + deep yearning) ─────────
    def _apply_cr_10(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """Office scene attenuates high-intensity InnerState frames."""
        if bundle.inner_state is None or bundle.scene is None:
            return
        scene_label = bundle.scene.metadata.get("scene")
        if scene_label != "office":
            return
        intensity = bundle.inner_state.metadata.get("intensity")
        if intensity is None or intensity <= 0.5:
            return
        bundle.inner_state.metadata["intensity"] = 0.3
        trace.append(ConflictResolutionEntry(
            layer_a="scene_context",
            layer_b="SS06.inner_state",
            rule_applied="CR-10",
            resolution=f"ATTENUATE(intensity: {intensity} → 0.3)",
            metadata={"scene": scene_label, "previous_intensity": intensity},
        ))

    # ─── CR-11: Stage envelope > Emotion (anger in intimate stage) ───
    def _apply_cr_11(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """Strong anger + stage ≥ ROMANTIC_INTEREST → vulnerable_anger variant.

        Per design §5: anger does not vanish in intimate stages, it acquires
        a different surface form. SWITCH_VARIANT preserves continuity.
        """
        if bundle.emotion is None or bundle.relationship is None:
            return
        emotion_name = bundle.emotion.metadata.get("emotion_name")
        intensity = bundle.emotion.metadata.get("intensity", 0.0)
        stage = bundle.relationship.metadata.get("stage")
        if emotion_name not in ("anger", "愤怒"):
            return
        if intensity < 0.5:
            return
        if _stage_rank(stage) < STAGE_ORDER["ROMANTIC_INTEREST"]:
            return
        # Prefer the variant published by SS03 for this exact stage; else
        # fall back to the generic intimate variant.
        stage_variants = bundle.emotion.metadata.get("stage_variants") or {}
        variant_key = stage_variants.get(stage)
        if variant_key is None or variant_key not in bundle.emotion.variants:
            variant_key = _first_present(
                bundle.emotion.variants,
                ("vulnerable_anger", "anger_intimate"),
            )
        self._switch_variant(
            layer=bundle.emotion,
            variant_key=variant_key,
            rule_id="CR-11",
            winner_label="SS04.stage_envelope",
            loser_label="SS03.emotion_context",
            verb_detail="anger → vulnerable_anger",
            trace=trace,
            gaps=gaps,
            extra_trace_metadata={
                "stage": stage,
                "original_intensity": intensity,
                "variant_intensity": intensity,  # intensity preserved
            },
            on_missing_metadata={"emotion_name": emotion_name, "stage": stage},
        )

    # ─── CR-12: Acute event > InnerState busy ────────────────────────
    def _apply_cr_12(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """Acute-stress in user message + InnerState busy/working → interrupted_for_you.

        Skipped under PURPLE — CR-9 already neutralized the layer; CR-12 is
        for the band *below* PURPLE.
        """
        if bundle.inner_state is None:
            return
        if not bundle.turn_signals.get("acute_stress"):
            return
        availability = bundle.inner_state.metadata.get("availability")
        if availability not in ("busy", "working", "low_energy"):
            return
        # Skip if PURPLE — care path has already taken over.
        if _safety_level(bundle.safety) == "PURPLE":
            return
        variant_key = _first_present(
            bundle.inner_state.variants,
            ("interrupted_for_you",),
        )
        self._switch_variant(
            layer=bundle.inner_state,
            variant_key=variant_key,
            rule_id="CR-12",
            winner_label="turn_signals.acute_stress",
            loser_label="SS06.inner_state",
            verb_detail="busy → interrupted_for_you",
            trace=trace,
            gaps=gaps,
            extra_trace_metadata={"availability": availability},
            on_missing_metadata={"availability": availability},
        )

    # ─── CR-13: Care Path > Soul.default_tone (within Anchor) ────────
    def _apply_cr_13(self, bundle: _Bundle, trace: list[ConflictResolutionEntry], gaps: list[ConflictResolutionGap]) -> None:
        """PURPLE active → replace default_tone with care_path_voice inside Anchor.

        identity.archetype, hard_never, voice_dna.markers all stay untouched.
        Failure mode (missing care_path_voice) is loud, not silent: see §10.
        """
        if bundle.anchor is None:
            return
        if bundle.anchor.metadata.get("_cr_13_applied"):
            return
        care_path_voice = bundle.anchor.metadata.get("care_path_voice")
        if care_path_voice is None:
            gaps.append(ConflictResolutionGap(
                rule_id="CR-13",
                reason="missing_care_path_voice",
                detail={"character_id": bundle.anchor.metadata.get("character_id")},
            ))
            logger.error(
                "conflict_resolver_gap",
                rule_id="CR-13",
                reason="missing_care_path_voice",
                character_id=bundle.anchor.metadata.get("character_id"),
            )
            # Fail loud — the caller (Composer) is expected to escalate.
            return
        prev_tone = bundle.anchor.metadata.get("default_tone")
        # Replace the tone surface. We do not touch content directly because
        # the Anchor's `content` is a serialized whole — the per-field swap
        # is exposed via metadata for downstream renderers (§7 design doc).
        bundle.anchor.metadata["active_tone"] = "care_path_voice"
        bundle.anchor.metadata["active_tone_payload"] = care_path_voice
        bundle.anchor.metadata["_cr_13_applied"] = True
        # If the Anchor pre-rendered a care_path_voice variant of its content,
        # swap it in. Otherwise leave content as-is and let the renderer use
        # active_tone_payload.
        if "care_path_voice" in bundle.anchor.variants:
            bundle.anchor.content = bundle.anchor.variants["care_path_voice"]
        trace.append(ConflictResolutionEntry(
            layer_a="SS07.safety_purple",
            layer_b="SS01.soul_default_tone",
            rule_applied="CR-13",
            resolution="SWITCH_VARIANT(default_tone → care_path_voice)",
            metadata={"previous_tone": prev_tone},
        ))

    # ─── Internal: SWITCH_VARIANT helper ─────────────────────────────
    def _switch_variant(
        self,
        *,
        layer: PromptLayer,
        variant_key: Optional[str],
        rule_id: str,
        winner_label: str,
        loser_label: str,
        verb_detail: str,
        trace: list[ConflictResolutionEntry],
        gaps: list[ConflictResolutionGap],
        on_missing_metadata: Optional[dict[str, Any]] = None,
        extra_trace_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Common SWITCH_VARIANT implementation with miss → gap + MASK fallback.

        Per design §10: variant lookup miss is the documented spec-gap mode.
        We MASK the loser (clear content) and emit a gap so on-call can see.
        """
        if not variant_key or variant_key not in layer.variants:
            gaps.append(ConflictResolutionGap(
                rule_id=rule_id,
                reason="missing_variant",
                detail={
                    "requested": variant_key,
                    "available": list(layer.variants.keys()),
                    **(on_missing_metadata or {}),
                },
            ))
            # Fallback: MASK the loser per §10 table row 1.
            layer.metadata["masked_by_resolver"] = True
            layer.content = ""
            trace.append(ConflictResolutionEntry(
                layer_a=winner_label,
                layer_b=loser_label,
                rule_applied=rule_id,
                resolution=f"MASK(variant missing: {variant_key})",
                metadata={"previous_content_hash": layer.content_hash, "fallback": "MASK"},
            ))
            return

        layer.content = layer.variants[variant_key]
        layer.metadata["active_variant"] = variant_key
        meta: dict[str, Any] = {"variant": variant_key}
        if extra_trace_metadata:
            meta.update(extra_trace_metadata)
        trace.append(ConflictResolutionEntry(
            layer_a=winner_label,
            layer_b=loser_label,
            rule_applied=rule_id,
            resolution=f"SWITCH_VARIANT({verb_detail})",
            metadata=meta,
        ))


# ============================================================
# Module-level entry point: resolve()
# ============================================================


def resolve(layers: AggregatedLayers) -> ResolvedComposition:
    """Module-level convenience: build a resolver and run it.

    `resolver = ConflictResolver(); return resolver.resolve(layers)`.
    """
    return ConflictResolver().resolve(layers)


# ============================================================
# Internal helpers
# ============================================================


# A _Bundle is just an alias for AggregatedLayers used inside the resolver —
# kept as a name to make the "we work on a copy" invariant explicit at every
# call site.
_Bundle = AggregatedLayers


def _safety_level(safety: Optional[PromptLayer]) -> Optional[str]:
    """Read the safety level off the safety layer's metadata."""
    if safety is None:
        return None
    level = safety.metadata.get("level")
    if isinstance(level, str):
        return level.upper()
    return None


def _first_present(d: dict[str, Any], candidates: tuple[str, ...]) -> Optional[str]:
    """Return the first key from `candidates` present in `d`, or None."""
    for k in candidates:
        if k in d:
            return k
    return None


def _copy_layer(layer: Optional[PromptLayer]) -> Optional[PromptLayer]:
    """Deep-enough copy of a PromptLayer: clone metadata + variants dicts so
    resolver mutations don't leak back to the caller. Content text is immutable
    so a shallow assignment is fine."""
    if layer is None:
        return None
    return PromptLayer(
        layer_id=layer.layer_id,
        source_subsystem=layer.source_subsystem,
        layer_type=layer.layer_type,
        priority=layer.priority,
        position_constraint=layer.position_constraint,
        content=layer.content,
        token_count_estimate=layer.token_count_estimate,
        min_token_count=layer.min_token_count,
        is_compressible=layer.is_compressible,
        generated_at=layer.generated_at,
        cache_key=layer.cache_key,
        content_hash=layer.content_hash,
        conflicts_with=list(layer.conflicts_with),
        variants=dict(layer.variants),
        metadata=dict(layer.metadata),
    )


def _copy_bundle(b: AggregatedLayers) -> AggregatedLayers:
    return AggregatedLayers(
        anchor=_copy_layer(b.anchor),
        memory=_copy_layer(b.memory),
        emotion=_copy_layer(b.emotion),
        relationship=_copy_layer(b.relationship),
        inner_state=_copy_layer(b.inner_state),
        safety=_copy_layer(b.safety),
        scene=_copy_layer(b.scene),
        user_message=_copy_layer(b.user_message),
        response_directive=_copy_layer(b.response_directive),
        turn_signals=dict(b.turn_signals),
        modality=b.modality,
    )


def _flatten_bundle(b: AggregatedLayers) -> list[PromptLayer]:
    """Convert the bundle back to an ordered layer list.

    Skips Nones and masked layers (`masked_by_resolver=True`). Position pins
    (anchor=first, user_message+response_directive=last) are preserved.
    """
    candidates = [
        b.anchor,
        b.safety,
        b.relationship,
        b.emotion,
        b.inner_state,
        b.memory,
        b.scene,
        b.user_message,
        b.response_directive,
    ]
    return [L for L in candidates if L is not None and not L.metadata.get("masked_by_resolver")]


def _apply_defer_ordering(layers: list[PromptLayer]) -> list[PromptLayer]:
    """Move any layers marked metadata['defer']=True behind their non-deferred peers.

    Position-pinned layers (first / last) are not subject to defer reordering.
    """
    pinned_first = [L for L in layers if L.position_constraint == "first"]
    pinned_last = [L for L in layers if L.position_constraint == "last"]
    middle = [L for L in layers if L.position_constraint == "anywhere"]
    deferred = [L for L in middle if L.metadata.get("defer")]
    middle = [L for L in middle if not L.metadata.get("defer")] + deferred
    return pinned_first + middle + pinned_last
