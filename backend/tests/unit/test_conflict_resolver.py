"""
Tests for ConflictResolver — SS05 §3.3 step 2 + §6.4

Covers every row in the precedence matrix (CR-1 through CR-13) plus:
- Care Path always wins (CR-9 + CR-13 fire under PURPLE regardless of
  any other content concern, and before the standard matrix loop)
- Failure modes: missing variant → gap + MASK; missing care_path_voice
  → gap + loud log (CR-13)
- Determinism: same inputs ⇒ same trace + same layer list
- The resolver is pure: the caller's input is not mutated
- DEFER ordering moves the loser behind the winner in injection order
- No-op rows (CR-6) emit a trace entry only when SS03 signals translation
"""

from __future__ import annotations

from heart.ss05_composer.conflict_resolver import (
    AggregatedLayers,
    ConflictResolutionEntry,
    resolve,
)
from heart.ss05_composer.layer_aggregator import LAYER_PRIORITIES, PromptLayer

# ============================================================
# Layer factories — minimal layers per subsystem
# ============================================================


def make_anchor(
    *,
    hard_never: list[str] | None = None,
    care_path_voice: dict | None = None,
    default_tone: str | None = "default_cold",
    cognitive_style_max: str | None = None,
    variants: dict[str, str] | None = None,
    content: str = "[ANCHOR]",
    character_id: str = "rin",
) -> PromptLayer:
    return PromptLayer(
        layer_id="anchor-1",
        source_subsystem="SS01",
        layer_type="anchor_full",
        priority=LAYER_PRIORITIES["anchor_full"],
        position_constraint="first",
        content=content,
        metadata={
            "hard_never": hard_never or [],
            "care_path_voice": care_path_voice,
            "default_tone": default_tone,
            "cognitive_style_max": cognitive_style_max,
            "character_id": character_id,
        },
        variants=variants or {},
    )


def make_memory(
    *,
    episodes: list[dict] | None = None,
    preferred_reply_shape: str | None = None,
    token_count_estimate: int = 100,
    content: str = "[MEMORY]",
) -> PromptLayer:
    return PromptLayer(
        layer_id="memory-1",
        source_subsystem="SS02",
        layer_type="memory_context",
        priority=LAYER_PRIORITIES["memory_context"],
        content=content,
        token_count_estimate=token_count_estimate,
        metadata={
            "episodes": episodes or [],
            "preferred_reply_shape": preferred_reply_shape,
        },
        is_compressible=True,
    )


def make_emotion(
    *,
    emotion_name: str = "neutral",
    intensity: float = 0.0,
    variants: dict[str, str] | None = None,
    stage_variants: dict[str, str] | None = None,
    resistance_translated: bool = False,
    original_emotion: str | None = None,
    content: str = "[EMOTION]",
) -> PromptLayer:
    return PromptLayer(
        layer_id="emotion-1",
        source_subsystem="SS03",
        layer_type="emotion_context",
        priority=LAYER_PRIORITIES["emotion_context"],
        content=content,
        metadata={
            "emotion_name": emotion_name,
            "intensity": intensity,
            "stage_variants": stage_variants or {},
            "resistance_translated": resistance_translated,
            "original_emotion": original_emotion,
        },
        variants=variants or {},
    )


def make_relationship(
    *,
    stage: str = "STRANGER",
    behavioral_envelope: set[str] | None = None,
    content: str = "[REL]",
) -> PromptLayer:
    return PromptLayer(
        layer_id="rel-1",
        source_subsystem="SS04",
        layer_type="relationship_context",
        priority=LAYER_PRIORITIES["relationship_context"],
        content=content,
        metadata={
            "stage": stage,
            "behavioral_envelope": behavioral_envelope,
        },
    )


def make_inner_state(
    *,
    availability: str | None = None,
    sub_suggestions: list[str] | None = None,
    intensity: float | None = None,
    romantic: bool = False,
    variants: dict[str, str] | None = None,
    content: str = "[INNER]",
) -> PromptLayer:
    return PromptLayer(
        layer_id="inner-1",
        source_subsystem="SS06",
        layer_type="inner_state",
        priority=LAYER_PRIORITIES["inner_state"],
        content=content,
        metadata={
            "availability": availability,
            "sub_suggestions": sub_suggestions or [],
            "intensity": intensity,
            "romantic": romantic,
        },
        variants=variants or {},
    )


def make_safety(*, level: str = "GREEN", content: str = "[SAFETY]") -> PromptLayer:
    return PromptLayer(
        layer_id="safety-1",
        source_subsystem="SS07",
        layer_type="safety",
        priority=LAYER_PRIORITIES["safety"],
        content=content,
        metadata={"level": level},
    )


def make_scene(*, scene: str, content: str = "[SCENE]") -> PromptLayer:
    return PromptLayer(
        layer_id="scene-1",
        source_subsystem="SS05",
        layer_type="scene_context",
        priority=LAYER_PRIORITIES["scene_context"],
        content=content,
        metadata={"scene": scene},
    )


def _entry(trace: list[ConflictResolutionEntry], rule_id: str) -> ConflictResolutionEntry | None:
    return next((e for e in trace if e.rule_applied == rule_id), None)


# ============================================================
# CR-1: Stage > Memory (mask stage-gated episodes)
# ============================================================


def test_cr_1_masks_stage_gated_episodes():
    """Episodes whose min_stage > current stage are masked from memory; rest kept."""
    layers = AggregatedLayers(
        memory=make_memory(episodes=[
            {"id": "ep-pre-romance", "min_stage": "ROMANTIC_INTEREST"},
            {"id": "ep-everyday", "min_stage": "STRANGER"},
        ]),
        relationship=make_relationship(stage="ACQUAINTANCE"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-1")
    assert entry is not None, "CR-1 should fire"
    assert "ep-pre-romance" in entry.metadata["masked_ids"]
    assert "ep-everyday" not in entry.metadata["masked_ids"]

    # Memory layer's episodes now contain only the kept one.
    mem = next(L for L in result.layers if L.layer_type == "memory_context")
    kept_ids = {e["id"] for e in mem.metadata["episodes"]}
    assert kept_ids == {"ep-everyday"}


def test_cr_1_no_op_when_no_stage_gated_episodes():
    """If no episodes are stage-gated above current stage, CR-1 emits nothing."""
    layers = AggregatedLayers(
        memory=make_memory(episodes=[{"id": "ep-1", "min_stage": "STRANGER"}]),
        relationship=make_relationship(stage="LOVER"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-1") is None


# ============================================================
# CR-2: Stage > Emotion (心动 in pre-romantic stage)
# ============================================================


def test_cr_2_switches_xindong_to_tenderness_in_pre_romantic():
    layers = AggregatedLayers(
        emotion=make_emotion(
            emotion_name="心动",
            intensity=0.6,
            variants={"tenderness": "[EMO tenderness]"},
            content="[EMO 心动]",
        ),
        relationship=make_relationship(stage="ACQUAINTANCE"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-2")
    assert entry is not None
    assert "SWITCH_VARIANT" in entry.resolution

    emo = next(L for L in result.layers if L.layer_type == "emotion_context")
    assert emo.content == "[EMO tenderness]"
    assert emo.metadata["active_variant"] == "tenderness"


def test_cr_2_no_op_when_already_romantic():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="心动", variants={"tenderness": "x"}),
        relationship=make_relationship(stage="LOVER"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-2") is None


# ============================================================
# CR-3: Soul.hard_never > Inner State sub-suggestion
# ============================================================


def test_cr_3_drops_sub_suggestions_matching_hard_never():
    layers = AggregatedLayers(
        anchor=make_anchor(hard_never=["撒娇", "宝贝"]),
        inner_state=make_inner_state(sub_suggestions=[
            "试着对用户撒娇",
            "保持冷静的关心",
            "用宝贝称呼用户",
        ]),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-3")
    assert entry is not None
    assert len(entry.metadata["dropped"]) == 2
    inner = next(L for L in result.layers if L.layer_type == "inner_state")
    assert inner.metadata["sub_suggestions"] == ["保持冷静的关心"]


def test_cr_3_no_op_when_no_matches():
    layers = AggregatedLayers(
        anchor=make_anchor(hard_never=["宝贝"]),
        inner_state=make_inner_state(sub_suggestions=["保持冷静"]),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-3") is None


# ============================================================
# CR-4: L4 > L3 within Memory
# ============================================================


def test_cr_4_masks_l4_contradicted_l3_episodes():
    layers = AggregatedLayers(
        memory=make_memory(episodes=[
            {"id": "l3-old", "contradicted_by_l4": True},
            {"id": "l3-good", "contradicted_by_l4": False},
        ]),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-4")
    assert entry is not None
    assert entry.metadata["contradicted_ids"] == ["l3-old"]
    mem = next(L for L in result.layers if L.layer_type == "memory_context")
    assert [e["id"] for e in mem.metadata["episodes"]] == ["l3-good"]


# ============================================================
# CR-5: Soul.cognitive_style > Memory shape
# ============================================================


def test_cr_5_attenuates_long_memory_to_short_fragments():
    layers = AggregatedLayers(
        anchor=make_anchor(cognitive_style_max="short"),
        memory=make_memory(preferred_reply_shape="long"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-5")
    assert entry is not None
    assert "ATTENUATE" in entry.resolution
    mem = next(L for L in result.layers if L.layer_type == "memory_context")
    assert mem.metadata["preferred_reply_shape"] == "short_fragments"
    assert mem.is_compressible is True


def test_cr_5_no_op_when_style_unconstrained():
    layers = AggregatedLayers(
        anchor=make_anchor(cognitive_style_max="long"),
        memory=make_memory(preferred_reply_shape="long"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-5") is None


# ============================================================
# CR-6: Soul > Emotion (SS03 already resolved — trace-only no-op)
# ============================================================


def test_cr_6_logs_noop_when_ss03_signaled_translation():
    layers = AggregatedLayers(
        emotion=make_emotion(
            emotion_name="coldness",
            resistance_translated=True,
            original_emotion="anger",
        ),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-6")
    assert entry is not None
    assert "NOOP" in entry.resolution
    assert entry.metadata["original_emotion"] == "anger"
    assert entry.metadata["translated_to"] == "coldness"


def test_cr_6_silent_when_no_translation_signal():
    layers = AggregatedLayers(emotion=make_emotion(emotion_name="anger"))
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-6") is None


# ============================================================
# CR-7: Relationship envelope > Emotion (jealousy not in envelope)
# ============================================================


def test_cr_7_switches_emotion_when_outside_envelope():
    layers = AggregatedLayers(
        emotion=make_emotion(
            emotion_name="jealousy",
            variants={"aggrieved_worry": "[EMO aggrieved+worry]"},
        ),
        relationship=make_relationship(
            behavioral_envelope={"sadness", "joy", "aggrieved_worry"},
        ),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-7")
    assert entry is not None
    emo = next(L for L in result.layers if L.layer_type == "emotion_context")
    assert emo.content == "[EMO aggrieved+worry]"


def test_cr_7_no_op_when_emotion_in_envelope():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="joy"),
        relationship=make_relationship(behavioral_envelope={"joy", "sadness"}),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-7") is None


def test_cr_7_missing_variant_falls_back_to_mask_and_emits_gap():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="jealousy"),  # no variants
        relationship=make_relationship(behavioral_envelope={"sadness"}),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-7")
    assert entry is not None
    assert "MASK" in entry.resolution
    assert any(g.rule_id == "CR-7" and g.reason == "missing_variant" for g in result.gaps)


# ============================================================
# CR-8: Modality > Memory (voice + long)
# ============================================================


def test_cr_8_defers_long_memory_in_voice_mode():
    mem = make_memory(token_count_estimate=400)
    layers = AggregatedLayers(memory=mem, modality="voice")
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-8")
    assert entry is not None
    assert "DEFER" in entry.resolution


def test_cr_8_no_op_in_text_mode():
    layers = AggregatedLayers(memory=make_memory(token_count_estimate=400), modality="text")
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-8") is None


def test_cr_8_defer_orders_memory_behind_other_anywhere_layers():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="joy"),
        memory=make_memory(token_count_estimate=600),
        modality="voice",
    )
    result = resolve(layers)
    types = [L.layer_type for L in result.layers]
    # Memory must come after emotion (deferred behind it).
    assert types.index("memory_context") > types.index("emotion_context")


# ============================================================
# CR-9: Safety > Inner State (romantic frame dropped under Care Path)
# ============================================================


def test_cr_9_drops_romantic_frame_under_purple():
    layers = AggregatedLayers(
        anchor=make_anchor(care_path_voice={"markers": ["……我在。"]}),
        inner_state=make_inner_state(romantic=True),
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-9")
    assert entry is not None
    assert "DROP" in entry.resolution
    inner = next(L for L in result.layers if L.layer_type == "inner_state")
    assert inner.metadata["romantic"] is False


def test_cr_9_also_fires_under_orange():
    layers = AggregatedLayers(
        inner_state=make_inner_state(romantic=True),
        safety=make_safety(level="ORANGE"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-9") is not None


def test_cr_9_no_op_under_green_or_yellow():
    for level in ("GREEN", "YELLOW"):
        layers = AggregatedLayers(
            inner_state=make_inner_state(romantic=True),
            safety=make_safety(level=level),
        )
        result = resolve(layers)
        assert _entry(result.conflicts_resolved, "CR-9") is None, f"CR-9 should not fire under {level}"


def test_cr_9_idempotent_when_already_applied():
    """CR-9 runs once under PURPLE; the non-PURPLE re-call inside the loop is a no-op."""
    layers = AggregatedLayers(
        anchor=make_anchor(care_path_voice={"markers": ["……"]}),
        inner_state=make_inner_state(romantic=True),
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)
    cr9_entries = [e for e in result.conflicts_resolved if e.rule_applied == "CR-9"]
    assert len(cr9_entries) == 1, "CR-9 should appear exactly once even when PURPLE"


# ============================================================
# CR-10: Scene > Inner State (office attenuates high intensity)
# ============================================================


def test_cr_10_attenuates_high_intensity_in_office():
    layers = AggregatedLayers(
        inner_state=make_inner_state(intensity=0.9),
        scene=make_scene(scene="office"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-10")
    assert entry is not None
    assert "ATTENUATE" in entry.resolution
    inner = next(L for L in result.layers if L.layer_type == "inner_state")
    assert inner.metadata["intensity"] == 0.3


def test_cr_10_no_op_when_intensity_low():
    layers = AggregatedLayers(
        inner_state=make_inner_state(intensity=0.2),
        scene=make_scene(scene="office"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-10") is None


def test_cr_10_no_op_outside_office():
    layers = AggregatedLayers(
        inner_state=make_inner_state(intensity=0.9),
        scene=make_scene(scene="home"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-10") is None


# ============================================================
# CR-11: Stage envelope > Emotion (anger in intimate stage)
# ============================================================


def test_cr_11_switches_anger_to_vulnerable_anger_in_lover_stage():
    layers = AggregatedLayers(
        emotion=make_emotion(
            emotion_name="anger",
            intensity=0.7,
            variants={"vulnerable_anger": "[EMO vulnerable]"},
        ),
        relationship=make_relationship(stage="LOVER"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-11")
    assert entry is not None
    assert entry.metadata["original_intensity"] == 0.7
    assert entry.metadata["variant_intensity"] == 0.7  # preserved per design §5
    emo = next(L for L in result.layers if L.layer_type == "emotion_context")
    assert emo.content == "[EMO vulnerable]"


def test_cr_11_prefers_stage_specific_variant_when_published():
    """If SS03 published stage_variants[LOVER] explicitly, use that key."""
    layers = AggregatedLayers(
        emotion=make_emotion(
            emotion_name="anger",
            intensity=0.7,
            stage_variants={"LOVER": "anger_for_lovers"},
            variants={
                "anger_for_lovers": "[EMO for lovers]",
                "vulnerable_anger": "[EMO generic]",
            },
        ),
        relationship=make_relationship(stage="LOVER"),
    )
    result = resolve(layers)
    emo = next(L for L in result.layers if L.layer_type == "emotion_context")
    assert emo.content == "[EMO for lovers]"


def test_cr_11_no_op_below_threshold_intensity():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="anger", intensity=0.3,
                             variants={"vulnerable_anger": "x"}),
        relationship=make_relationship(stage="LOVER"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-11") is None


def test_cr_11_no_op_below_romantic_stage():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="anger", intensity=0.7,
                             variants={"vulnerable_anger": "x"}),
        relationship=make_relationship(stage="STRANGER"),
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-11") is None


def test_cr_11_missing_variant_emits_gap_and_masks():
    layers = AggregatedLayers(
        emotion=make_emotion(emotion_name="anger", intensity=0.7),  # no variants
        relationship=make_relationship(stage="LOVER"),
    )
    result = resolve(layers)

    assert _entry(result.conflicts_resolved, "CR-11") is not None
    assert any(g.rule_id == "CR-11" and g.reason == "missing_variant" for g in result.gaps)


# ============================================================
# CR-12: Acute event > InnerState busy
# ============================================================


def test_cr_12_switches_busy_to_interrupted_for_you():
    layers = AggregatedLayers(
        inner_state=make_inner_state(
            availability="busy",
            variants={"interrupted_for_you": "[INNER interrupted]"},
        ),
        turn_signals={"acute_stress": True, "acute_stress_level": 0.7},
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-12")
    assert entry is not None
    inner = next(L for L in result.layers if L.layer_type == "inner_state")
    assert inner.content == "[INNER interrupted]"


def test_cr_12_skipped_under_purple():
    """CR-12 is for the band BELOW PURPLE; PURPLE delegates to CR-9."""
    layers = AggregatedLayers(
        inner_state=make_inner_state(
            availability="busy",
            variants={"interrupted_for_you": "[INNER interrupted]"},
        ),
        safety=make_safety(level="PURPLE"),
        anchor=make_anchor(care_path_voice={"markers": ["x"]}),
        turn_signals={"acute_stress": True},
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-12") is None


def test_cr_12_no_op_without_acute_stress_signal():
    layers = AggregatedLayers(
        inner_state=make_inner_state(
            availability="busy",
            variants={"interrupted_for_you": "x"},
        ),
        turn_signals={},  # classifier absent → fail-quiet per design §6
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-12") is None


def test_cr_12_no_op_when_inner_state_already_available():
    layers = AggregatedLayers(
        inner_state=make_inner_state(
            availability="available",
            variants={"interrupted_for_you": "x"},
        ),
        turn_signals={"acute_stress": True},
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-12") is None


# ============================================================
# CR-13: Care Path (PURPLE) > Soul.default_tone (within Anchor)
# ============================================================


def test_cr_13_switches_default_tone_to_care_path_voice_under_purple():
    """Design §7: Safety can request the care register; identity stays Rin's."""
    care_voice = {
        "suppressed_markers": ["无聊", "幼稚"],
        "fallbacks": ["……我在。", "……说吧，我听着。"],
    }
    layers = AggregatedLayers(
        anchor=make_anchor(
            care_path_voice=care_voice,
            variants={"care_path_voice": "[ANCHOR care register]"},
        ),
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)

    entry = _entry(result.conflicts_resolved, "CR-13")
    assert entry is not None
    assert "SWITCH_VARIANT" in entry.resolution
    anchor = next(L for L in result.layers if L.layer_type == "anchor_full")
    assert anchor.metadata["active_tone"] == "care_path_voice"
    assert anchor.content == "[ANCHOR care register]"


def test_cr_13_no_op_outside_purple():
    layers = AggregatedLayers(
        anchor=make_anchor(care_path_voice={"x": 1}),
        safety=make_safety(level="ORANGE"),  # not Care Path register
    )
    result = resolve(layers)
    assert _entry(result.conflicts_resolved, "CR-13") is None


def test_cr_13_missing_care_path_voice_emits_loud_gap():
    """Design §10: missing care_path_voice must fail loud — not silent — under PURPLE."""
    layers = AggregatedLayers(
        anchor=make_anchor(care_path_voice=None, character_id="rin"),
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)

    # No trace entry — CR-13 bailed before applying.
    assert _entry(result.conflicts_resolved, "CR-13") is None
    # But a gap was emitted with the loud reason.
    gap = next((g for g in result.gaps if g.rule_id == "CR-13"), None)
    assert gap is not None
    assert gap.reason == "missing_care_path_voice"
    assert gap.detail["character_id"] == "rin"


def test_cr_13_runs_only_once_even_when_no_variant_in_anchor():
    """If anchor has care_path_voice metadata but no pre-rendered variant content,
    we still record the tone swap via active_tone — only one entry per turn."""
    layers = AggregatedLayers(
        anchor=make_anchor(care_path_voice={"markers": ["……"]}),  # no variants
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)

    cr13_entries = [e for e in result.conflicts_resolved if e.rule_applied == "CR-13"]
    assert len(cr13_entries) == 1


# ============================================================
# Care Path Always Wins — composite invariant
# ============================================================


def test_care_path_runs_before_other_rules_under_purple():
    """Under PURPLE, CR-9 and CR-13 must both appear in the trace, and CR-13
    appears before CR-9 (PURPLE branch runs in that order — care tone first,
    then strip the romantic frame)."""
    layers = AggregatedLayers(
        anchor=make_anchor(
            care_path_voice={"markers": ["……"]},
            variants={"care_path_voice": "[CARE]"},
        ),
        inner_state=make_inner_state(romantic=True),
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)

    rules_in_order = [e.rule_applied for e in result.conflicts_resolved]
    assert "CR-13" in rules_in_order
    assert "CR-9" in rules_in_order
    assert rules_in_order.index("CR-13") < rules_in_order.index("CR-9")


def test_care_path_neutralizes_inner_state_and_anchor_atomically():
    """Under PURPLE: anchor tone swapped AND inner_state romantic dropped — both."""
    layers = AggregatedLayers(
        anchor=make_anchor(
            care_path_voice={"markers": ["……"]},
            variants={"care_path_voice": "[CARE]"},
        ),
        inner_state=make_inner_state(romantic=True),
        safety=make_safety(level="PURPLE"),
    )
    result = resolve(layers)

    anchor = next(L for L in result.layers if L.layer_type == "anchor_full")
    inner = next(L for L in result.layers if L.layer_type == "inner_state")
    assert anchor.metadata["active_tone"] == "care_path_voice"
    assert inner.metadata["romantic"] is False


# ============================================================
# Determinism & purity
# ============================================================


def test_resolver_is_deterministic_same_input_same_trace():
    def fresh_inputs() -> AggregatedLayers:
        return AggregatedLayers(
            anchor=make_anchor(hard_never=["撒娇"]),
            inner_state=make_inner_state(sub_suggestions=["试着撒娇"]),
            emotion=make_emotion(
                emotion_name="anger",
                intensity=0.8,
                variants={"vulnerable_anger": "[V]"},
            ),
            relationship=make_relationship(stage="LOVER"),
        )

    r1 = resolve(fresh_inputs())
    r2 = resolve(fresh_inputs())

    rules1 = [e.rule_applied for e in r1.conflicts_resolved]
    rules2 = [e.rule_applied for e in r2.conflicts_resolved]
    assert rules1 == rules2

    contents1 = [(L.layer_type, L.content) for L in r1.layers]
    contents2 = [(L.layer_type, L.content) for L in r2.layers]
    assert contents1 == contents2


def test_resolver_does_not_mutate_input():
    """Resolver must deep-copy — caller's layers stay clean."""
    inner = make_inner_state(romantic=True)
    anchor = make_anchor(care_path_voice={"x": 1}, variants={"care_path_voice": "[C]"})
    layers = AggregatedLayers(
        anchor=anchor,
        inner_state=inner,
        safety=make_safety(level="PURPLE"),
    )

    original_anchor_content = anchor.content
    original_inner_metadata = dict(inner.metadata)

    resolve(layers)

    assert anchor.content == original_anchor_content, "Caller's anchor.content was mutated"
    assert inner.metadata == original_inner_metadata, "Caller's inner_state.metadata was mutated"


# ============================================================
# Resolver output shape & duration
# ============================================================


def test_resolver_records_duration_ms():
    result = resolve(AggregatedLayers())
    assert isinstance(result.duration_ms, float)
    assert result.duration_ms >= 0.0


def test_empty_input_yields_empty_output():
    result = resolve(AggregatedLayers())
    assert result.layers == []
    assert result.conflicts_resolved == []
    assert result.gaps == []


def test_aggregated_layers_from_layer_list_round_trip():
    """from_layer_list groups a flat list into the typed bundle by layer_type."""
    layers_in = [
        make_anchor(),
        make_memory(),
        make_emotion(emotion_name="joy"),
        make_relationship(stage="FRIEND"),
        make_inner_state(),
        make_safety(level="GREEN"),
    ]
    bundle = AggregatedLayers.from_layer_list(layers_in)
    assert bundle.anchor is not None
    assert bundle.memory is not None
    assert bundle.emotion is not None
    assert bundle.relationship is not None
    assert bundle.inner_state is not None
    assert bundle.safety is not None
