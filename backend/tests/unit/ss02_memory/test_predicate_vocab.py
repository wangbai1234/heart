"""Unit tests for ss02_memory/predicate_vocab.py."""

from __future__ import annotations

import pytest

from heart.ss02_memory.predicate_vocab import build_embedding_text, normalize_predicate


class TestNormalizePredicate:
    def test_alias_concerned_about(self):
        assert normalize_predicate("concerned_about") == "worries_about"

    def test_alias_is_concerned_about(self):
        assert normalize_predicate("is_concerned_about") == "worries_about"

    def test_alias_has_upcoming_interview(self):
        assert normalize_predicate("has_upcoming_interview") == "has_interview"

    def test_alias_has_scheduled_interview(self):
        assert normalize_predicate("has_scheduled_interview") == "has_interview"

    def test_alias_located_at(self):
        assert normalize_predicate("located_at") == "location"

    def test_alias_located_in(self):
        assert normalize_predicate("located_in") == "location"

    def test_alias_is_located_in(self):
        assert normalize_predicate("is_located_in") == "location"

    def test_alias_has_sister(self):
        assert normalize_predicate("has_sister") == "has_sibling"

    def test_alias_likes_food(self):
        assert normalize_predicate("likes_food") == "likes"

    def test_alias_enjoys(self):
        assert normalize_predicate("enjoys") == "likes"

    def test_canonical_pass_through(self):
        assert normalize_predicate("worries_about") == "worries_about"

    def test_unknown_predicate_unchanged(self):
        assert normalize_predicate("made_up_predicate_xyz") == "made_up_predicate_xyz"

    def test_strip_whitespace(self):
        assert normalize_predicate("  concerned_about  ") == "worries_about"

    def test_case_insensitive(self):
        assert normalize_predicate("Concerned_About") == "worries_about"


class TestBuildEmbeddingText:
    def test_has_pet_contains_pet_gloss(self):
        text = build_embedding_text("user", "has_pet", "一只叫年糕的猫")
        assert "养了宠物" in text
        assert "年糕" in text

    def test_has_pet_alias_normalised(self):
        # owns_pet → has_pet → "养了宠物"
        text = build_embedding_text("user", "owns_pet", "一只叫年糕的猫")
        assert "养了宠物" in text

    def test_worries_about_gloss(self):
        text = build_embedding_text("user", "worries_about", "面试中的自我介绍")
        assert "担心" in text
        assert "面试中的自我介绍" in text

    def test_concerned_about_resolved_to_worries_about_gloss(self):
        text = build_embedding_text("user", "concerned_about", "面试")
        assert "担心" in text

    def test_has_interview_gloss(self):
        text = build_embedding_text("user", "has_interview", "下周二的技术面试")
        assert "有面试" in text

    def test_user_subject_prefix(self):
        text = build_embedding_text("user", "has_pet", "猫")
        assert text.startswith("用户")

    def test_non_user_subject_prefix(self):
        text = build_embedding_text("Alice", "has_pet", "猫")
        assert text.startswith("Alice")

    def test_unknown_predicate_falls_back_to_predicate_name(self):
        text = build_embedding_text("user", "some_unknown_pred_xyz", "某事")
        assert "some_unknown_pred_xyz" in text
        assert "某事" in text

    def test_object_value_always_in_output(self):
        text = build_embedding_text("user", "occupation", "程序员")
        assert "程序员" in text

    def test_location_gloss(self):
        text = build_embedding_text("user", "location", "苏州")
        assert "所在地" in text
        assert "苏州" in text
