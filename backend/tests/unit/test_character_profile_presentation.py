from heart.api.routes_characters import _derive_profile_presentation


def test_legacy_quick_profile_suppresses_repeated_persona_fallbacks():
    persona = "寡言的急诊科医生，习惯用行动表达关心。"

    result = _derive_profile_presentation({}, {"persona": persona}, is_builtin=False)

    assert result["tagline"] == persona
    assert result["intro"] == ""
    assert result["one_liner"] == ""


def test_enriched_quick_profile_preserves_distinct_section_copy():
    draft = {
        "persona": "寡言的急诊科医生，习惯用行动表达关心。",
        "tagline": "他总在最忙的夜里保持清醒",
        "intro": "沈砚是急诊科医生，判断果断，不擅长解释关心，却会记住身边人的每一个小习惯。",
        "one_liner": "一场旧事故因你的到来再次浮出水面。",
        "archetype_label": "急诊科医生",
    }

    result = _derive_profile_presentation({}, draft, is_builtin=False)

    assert result["tagline"] == draft["tagline"]
    assert result["intro"] == draft["intro"]
    assert result["one_liner"] == draft["one_liner"]
    assert result["archetype_label"] == "急诊科医生"
