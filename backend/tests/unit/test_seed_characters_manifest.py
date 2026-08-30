from heart.ss01_soul.draft import CharacterDraft
from scripts.seed_characters import _PRESENTATION_KEYS, _build_draft


def test_workshop_seed_preserves_age_and_accepts_authored_ui_fields():
    entry = {
        "display_name": {"zh": "测试角色"},
        "gender": "male",
        "age_range": "25-30",
        "creation_mode": "workshop",
        "persona": "这是一个明确成年的测试角色，用于验证运营导入时的展示字段不会丢失。",
        "tags": ["女性向", "成年"],
        "custom_html": "<section>专属详情页</section>",
        "starter_config": {
            "type": "branched",
            "branches": [
                {"label": "追问", "lines": ["把真相告诉我"]},
                {"label": "离开", "lines": ["先让我想清楚"]},
            ],
        },
    }

    draft_dict = _build_draft(entry).model_dump(mode="json")
    for key in _PRESENTATION_KEYS:
        if key in entry:
            draft_dict[key] = entry[key]

    draft = CharacterDraft.model_validate(draft_dict)

    assert draft.age_range == "25-30"
    assert draft.creation_mode == "workshop"
    assert draft.custom_html == entry["custom_html"]
    assert draft.starter_config is not None


def test_seed_presentation_keys_include_age_range():
    assert "age_range" in _PRESENTATION_KEYS
