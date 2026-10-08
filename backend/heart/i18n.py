"""Supported public locales and user-scoped generation preferences."""

from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

Locale = Literal["en", "ja", "ko"]
ActionStyle = Literal["parentheses", "asterisks", "fullwidth"]
LANGUAGE_NAMES = {"en": "English", "ja": "Japanese", "ko": "Korean"}
ACTION_MARKERS = {"parentheses": ("(", ")"), "asterisks": ("*", "*"), "fullwidth": ("（", "）")}


class LanguagePreferences(BaseModel, extra="forbid"):
    interface_language: Locale = "en"
    response_language: Locale = "en"
    action_style: ActionStyle = "fullwidth"
    response_follows_interface: bool = True

    @model_validator(mode="after")
    def apply_output_contract(self) -> "LanguagePreferences":
        # Older clients/rows may carry other markers; generation uses the
        # original fullwidth contract regardless of that legacy field.
        self.action_style = "fullwidth"
        if self.response_follows_interface:
            self.response_language = self.interface_language
        return self


def resolve_locale(accept_language: str) -> Locale:
    """Honor browser quality weights; unsupported languages fall back to English."""
    candidates = []
    for index, item in enumerate(accept_language.split(",")):
        parts = item.strip().lower().split(";")
        code = parts[0].split("-")[0]
        quality = 1.0
        try:
            for parameter in parts[1:]:
                if parameter.strip().startswith("q="):
                    quality = float(parameter.strip()[2:])
        except ValueError:
            continue
        if code in LANGUAGE_NAMES and 0 < quality <= 1:
            candidates.append((-quality, index, code))
    return cast(Locale, min(candidates)[2]) if candidates else "en"


def resolve_initial_locale(country: str | None, accept_language: str) -> Locale:
    if country:
        return cast(Locale, {"JP": "ja", "KR": "ko"}.get(country, "en"))
    return resolve_locale(accept_language)


async def load_preferences(db: AsyncSession, user_id: UUID) -> LanguagePreferences:
    result = await db.execute(
        text(
            "SELECT interface_language, response_language, action_style, response_follows_interface "
            "FROM user_language_preferences WHERE user_id = :uid"
        ),
        {"uid": user_id},
    )
    row = result.mappings().first()
    return LanguagePreferences(**dict(row)) if row else LanguagePreferences()


async def initialize_preferences(db: AsyncSession, user_id: UUID, accept_language: str) -> None:
    """Initialize signup in its transaction, without overwriting saved choices."""
    await db.execute(
        text(
            "INSERT INTO user_language_preferences "
            "(user_id, interface_language, response_language, action_style) "
            "VALUES (:uid, :locale, :locale, 'fullwidth') "
            "ON CONFLICT (user_id) DO NOTHING"
        ),
        {"uid": user_id, "locale": resolve_locale(accept_language)},
    )


def generation_directive(language: str, action_style: str) -> str:
    """Only allowlisted values enter the system prompt."""
    name = LANGUAGE_NAMES.get(language, "English")
    return (
        f"\nOUTPUT LANGUAGE: Write all dialogue and narration in {name}. "
        "Background notes, memories and examples may use other languages; "
        "they do not set the output language. Preserve the character's identity and voice. "
        "Do not include Chinese translations or bilingual explanations.\n"
        "ACTION FORMAT: Wrap each action or narration in （action）. "
        "Keep spoken dialogue outside action markers. Use 【】 only as the legacy fallback. "
        "Never use ASCII square brackets [] for actions; these are reserved for voice controls. "
        "This output convention supersedes formatting in background examples.\n"
    )


REPLIES = {
    "fallback": {
        "en": "I couldn't finish that reply. Please try again in a moment.",
        "ja": "返信を完了できませんでした。少し待ってから、もう一度お試しください。",
        "ko": "답변을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    },
    "refusal": {
        "en": "I can't continue with this content. We can explore a non-graphic story or emotional conversation instead.",
        "ja": "この内容では続けられません。露骨な描写のない物語や、気持ちについての会話なら続けられます。",
        "ko": "이 내용으로는 계속할 수 없습니다. 노골적인 묘사 없는 이야기나 감정에 관한 대화를 나눌 수 있어요.",
    },
    "care": {
        "en": "I'm sorry you're going through this. If you're in immediate danger, contact local emergency services or someone you trust now. You don't have to face this alone.",
        "ja": "つらい状況にいるのですね。今すぐ危険がある場合は、地域の緊急窓口か信頼できる人に連絡してください。一人で抱え込む必要はありません。",
        "ko": "힘든 시간을 보내고 계시는군요. 지금 위험하다면 현지 응급기관이나 믿을 수 있는 사람에게 바로 연락해 주세요. 혼자 감당하지 않아도 됩니다.",
    },
}


def localized_reply(kind: str, language: str) -> str:
    variants = REPLIES[kind]
    return variants.get(language, variants["en"])
