from copy import deepcopy

import pytest

from heart.localization.batch import digest, plan, validate
from heart.ss01_soul.draft import CharacterDraft, SoulProfileDraft


def examples():
    soul = {field: "A specific personal truth" for field in SoulProfileDraft.model_fields}
    soul["softening_triggers"] = ["A shared evening", "A sincere gesture"]
    draft = CharacterDraft(display_name={"en": "Mina"}, persona="An adult character with a distinctive background.",
        locale="en", backstory="A detailed childhood and career.", soul_profile=soul,
        speech_samples=["An individual voice."], catchphrases=["Stay close."],
        world_book="A secret at the end.")
    source = {"id": "source_test", "draft": draft.model_dump(mode="json")}
    task = plan([source], ["vi"])[0]
    candidate = {"task_id": task["task_id"], "draft": {**draft.model_dump(mode="json"),
        "locale": "vi", "response_language": "vi", "display_name": {"localized": {"vi": "Minh"}}},
        "editorial_notes": "Synthetic test fixture, never a real review."}
    return task, candidate


def approve_fixture(task, candidate):
    candidate["review"] = {"task_id": task["task_id"], "source_sha256": task["source_sha256"],
        "resource_version": task["resource_version"], "candidate_sha256": digest(candidate),
        "approved": True, "reviewer": "TEST FIXTURE ONLY", "reviewed_at": "2026-10-13T00:00:00Z",
        "checks": dict.fromkeys(["field_fidelity", "name_consistency", "safety", "output_format", "rights"], True)}


def test_task_identity_is_per_source_language_and_version():
    task, _ = examples()
    assert plan([task["source"]], ["vi"])[0] == task
    assert plan([task["source"]], ["bn"])[0]["task_id"] != task["task_id"]
    changed = deepcopy(task["source"]); changed["draft"]["backstory"] += " Changed."
    assert plan([changed], ["vi"])[0]["task_id"] != task["task_id"]


@pytest.mark.parametrize("field", ["backstory", "soul_profile", "speech_samples", "catchphrases", "world_book"])
def test_missing_source_content_rejected(field):
    task, candidate = examples()
    candidate["draft"].pop(field)
    with pytest.raises(ValueError):
        validate(task, candidate)


def test_overlong_text_rejected_without_clipping():
    task, candidate = examples()
    candidate["draft"]["tagline"] = "x" * 61
    with pytest.raises(ValueError):
        validate(task, candidate)
    assert len(candidate["draft"]["tagline"]) == 61


def test_complete_draft_and_bound_review():
    task, candidate = examples()
    assert validate(task, candidate).soul_profile is not None
    with pytest.raises(ValueError):
        validate(task, candidate, approved=True)
    approve_fixture(task, candidate)
    validate(task, candidate, approved=True)
    candidate["draft"]["backstory"] += " altered"
    with pytest.raises(ValueError, match="Review does not match"):
        validate(task, candidate, approved=True)


def test_stale_resource_or_source_rejected():
    task, candidate = examples()
    task["resource_version"] = "old"
    with pytest.raises(ValueError, match="Stale"):
        validate(task, candidate)
