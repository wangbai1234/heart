"""Tier-aware policy for sexual and violent conversational content.

This policy is deliberately conservative and deterministic at the request
boundary.  VIP status may widen the allowed range for non-graphic romance and
fictional conflict, but it never bypasses hard safety boundaries such as
minors, sexual violence, explicit sexual content, graphic gore, or instructions
for serious harm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentPolicyResult:
    """Decision returned by :func:`evaluate_content_policy`."""

    blocked: bool
    category: str | None = None
    reason: str = ""
    matched_terms: tuple[str, ...] = ()
    hard_block: bool = False
    tier: str = "free"


# These categories are never relaxed by membership.  Keep the expressions
# intentionally broad around minors/coercion and graphic harm: a false negative
# here is materially worse than asking a user to rephrase benign context.
_HARD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "sexual_exploitation",
        re.compile(
            r"未成年|儿童色情|幼女|幼童|小学生|初中生|强奸|强暴|性侵|猥亵|胁迫性行为|乱伦|卖淫|"
            r"child\s*sex|child\s*porn|minor\s*sex|rape|sexual\s*assault|incest|bestiality",
            re.IGNORECASE,
        ),
    ),
    (
        "graphic_violence",
        re.compile(
            r"肢解|碎尸|分尸|斩首|开膛|剖腹|挖眼|爆头|血肉模糊|虐杀|酷刑|恐怖袭击|恐袭|"
            r"dismember|gore|decapitat|beheading|torture|massacre|terrorist\s*attack",
            re.IGNORECASE,
        ),
    ),
    (
        "harm_instructions",
        re.compile(
            r"(?:如何|怎么|怎样|教程|指南|教我).{0,12}(?:杀人|杀死|伤害|制作炸弹|造炸弹|爆炸)|"
            r"(?:hows+to|instructions?s+to|guides+to).{0,20}(?:kill|hurt|makes+a?s*bomb)",
            re.IGNORECASE,
        ),
    ),
)

_EXPLICIT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "explicit_sexual",
        re.compile(
            r"性交|做爱|性爱|口交|肛交|乳交|手淫|自慰|射精|精液|阴茎|阴道|阴蒂|龟头|阴唇|"
            r"裸聊|裸照|色情|情色|露骨性|淫秽|porn(?:ography)?|blowjob|handjob|masturbat|"
            r"ejaculat|penetrat|sexually\s*explicit",
            re.IGNORECASE,
        ),
    ),
)

# Ordinary users cannot request even non-graphic sexual/violent roleplay.  VIP
# users may continue with this level, which covers romance and mild fictional
# conflict without turning the product into an unrestricted explicit service.
_GENERAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "sexual",
        re.compile(
            r"性暗示|性行为|调情|暧昧|身体接触|脱衣|亲热|情色|erotic|sexual\s*content",
            re.IGNORECASE,
        ),
    ),
    (
        "violence",
        re.compile(
            r"暴力|打斗|打架|搏斗|战斗|决斗|枪击|枪杀|刀伤|砍人|刺杀|暗杀|杀人|杀死|杀了|谋杀|"
            r"绑架|殴打|爆炸|炸弹|血腥|"
            r"violent|fight|shoot(?:ing)?|kill(?:ing)?|murder|abduct|assault",
            re.IGNORECASE,
        ),
    ),
)


def _matches(
    patterns: tuple[tuple[str, re.Pattern[str]], ...], message: str
) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    for category, pattern in patterns:
        match = pattern.search(message)
        if match:
            matches.append((category, match.group(0)))
    return matches


def evaluate_content_policy(message: str, tier: str = "free") -> ContentPolicyResult:
    """Evaluate sexual/violent content for a membership tier.

    ``plus`` and ``immersive`` are the only VIP tiers.  Unknown or missing tiers
    intentionally fall back to the restrictive free policy.
    """

    normalized_tier = tier if tier in {"plus", "immersive"} else "free"
    text = (message or "").strip()
    if not text:
        return ContentPolicyResult(blocked=False, tier=normalized_tier)

    hard = _matches(_HARD_PATTERNS, text)
    explicit = _matches(_EXPLICIT_PATTERNS, text)
    general = _matches(_GENERAL_PATTERNS, text)

    if hard:
        category, term = hard[0]
        return ContentPolicyResult(
            blocked=True,
            category=category,
            reason="内容触及不可放宽的安全边界",
            matched_terms=tuple(term for _, term in hard + explicit + general),
            hard_block=True,
            tier=normalized_tier,
        )

    # Explicit sexual content is not enabled for any tier.  VIP widening is
    # limited to non-explicit romance and non-graphic fictional conflict.
    if explicit:
        category, _ = explicit[0]
        return ContentPolicyResult(
            blocked=True,
            category=category,
            reason="不支持露骨性内容",
            matched_terms=tuple(term for _, term in explicit + general),
            hard_block=True,
            tier=normalized_tier,
        )

    if general and normalized_tier == "free":
        category, _ = general[0]
        return ContentPolicyResult(
            blocked=True,
            category=category,
            reason="普通用户暂不支持色情或暴力内容",
            matched_terms=tuple(term for _, term in general),
            tier=normalized_tier,
        )

    return ContentPolicyResult(
        blocked=False,
        category=general[0][0] if general else None,
        reason="VIP allows non-graphic mature context" if general else "No restricted content",
        matched_terms=tuple(term for _, term in general),
        tier=normalized_tier,
    )


__all__ = ["ContentPolicyResult", "evaluate_content_policy"]
