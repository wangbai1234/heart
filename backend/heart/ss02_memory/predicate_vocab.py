"""Shared predicate vocabulary for SS02 memory L3 writes.

Provides two functions used by both write paths (memory_encoder.py Path A
and extractor/writer.py Path B):
  normalize_predicate — fold synonym predicates to a canonical form so
    deduplication compares canonical names, not raw LLM strings.
  build_embedding_text — produce a Chinese-language sentence used ONLY
    when generating semantic_vector; literal_text is unchanged so
    reconstructor / L4 snapshots / test fixtures are unaffected.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Synonym alias map (raw LLM predicate → canonical predicate)
# ---------------------------------------------------------------------------
# Only alias predicates that are truly synonymous; preserve information for
# distinct concepts (e.g. location_residence ≠ location_origin).
_PREDICATE_ALIASES: dict[str, str] = {
    # Worry / concern
    "concerned_about": "worries_about",
    "is_concerned_about": "worries_about",
    "anxious_about": "worries_about",
    # Interview / scheduled event
    "has_upcoming_interview": "has_interview",
    "has_scheduled_interview": "has_interview",
    "has_job_interview": "has_interview",
    # Location variants
    "located_at": "location",
    "located_in": "location",
    "is_located_in": "location",
    "is_in_location": "location",
    "lives_in": "location",
    "resides_in": "location",
    # Sibling / family
    "has_sister": "has_sibling",
    "has_brother": "has_sibling",
    # Generic likes
    "likes_food": "likes",
    "likes_color": "likes",
    "likes_to_go_to": "likes",
    "likes_doing": "likes",
    "enjoys": "likes",
    # Pet ownership
    "owns_pet": "has_pet",
    "has_a_pet": "has_pet",
}

# ---------------------------------------------------------------------------
# Chinese gloss map (canonical predicate → human-readable Chinese phrase)
# ---------------------------------------------------------------------------
# Covers all Path-A free predicates AND Path-B closed-enum Attribute values.
_PREDICATE_ZH: dict[str, str] = {
    # Path A — free predicates
    "has_pet": "养了宠物",
    "worries_about": "担心",
    "has_interview": "有面试",
    "location": "所在地",
    "has_sibling": "有兄弟姐妹",
    "likes": "喜欢",
    "occupation": "职业",
    "hobby": "爱好",
    "dislike": "不喜欢",
    "health_condition": "健康状况",
    "birthday": "生日",
    "anniversary": "纪念日",
    "has_friend": "有朋友",
    "has_family": "有家人",
    "lives_with": "和某人同住",
    "works_at": "在某处工作",
    "studies_at": "在某处学习",
    "graduated_from": "毕业于",
    "grew_up_in": "成长于",
    "speaks": "会说",
    "has_skill": "会",
    "has_goal": "目标是",
    "has_dream": "梦想是",
    "has_fear": "害怕",
    "has_value": "重视",
    "has_belief": "相信",
    "has_experience": "经历过",
    "has_habit": "习惯",
    "has_schedule": "日程",
    "has_achievement": "成就",
    "has_difficulty": "正在面临困难",
    "has_conflict": "有矛盾",
    "has_plan": "计划",
    "has_memory": "记得",
    # Path B — closed Attribute enum values
    "name": "名字",
    "nickname": "昵称",
    "age": "年龄",
    "color": "颜色",
    "breed": "品种",
    "relation": "关系",
    "location_residence": "居住地",
    "location_origin": "籍贯",
    "other": "其他信息",
}


def normalize_predicate(pred: str) -> str:
    """Return the canonical predicate for *pred*.

    Applies lower-case + strip then looks up _PREDICATE_ALIASES.
    Unknown predicates are returned unchanged so no information is lost.
    """
    key = pred.strip().lower()
    return _PREDICATE_ALIASES.get(key, key)


def build_embedding_text(subject: str, predicate: str, object_: str) -> str:
    """Produce a Chinese sentence used *only* for generating semantic_vector.

    The sentence is optimised for alignment with Chinese natural-language
    recall queries (e.g. "你记得我宠物叫什么").  literal_text is NOT
    changed — this function is only called when embedding.

    Examples:
      build_embedding_text("user", "has_pet", "一只叫年糕的猫")
        → "用户养了宠物：一只叫年糕的猫"
      build_embedding_text("user", "worries_about", "面试中的自我介绍")
        → "用户担心：面试中的自我介绍"
      build_embedding_text("user", "unknown_pred", "某事")
        → "用户unknown_pred：某事"
    """
    canonical = normalize_predicate(predicate)
    gloss = _PREDICATE_ZH.get(canonical, canonical)

    if subject.lower() in ("user", "用户"):
        prefix = "用户"
    else:
        prefix = subject

    return f"{prefix}{gloss}：{object_}"
