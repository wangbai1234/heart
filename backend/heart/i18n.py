"""Supported public locales and user-scoped generation preferences."""

from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.locales import DEFAULT_LOCALE, LANGUAGE_NAMES, LOCALE_ALIASES, LOCALE_REGISTRY, Locale

ActionStyle = Literal["parentheses", "asterisks", "fullwidth"]
ResponseMode = Literal["auto", "interface", "character", "fixed"]
ACTION_MARKERS = {"parentheses": ("(", ")"), "asterisks": ("*", "*"), "fullwidth": ("（", "）")}


class LanguagePreferences(BaseModel, extra="forbid"):
    interface_language: Locale = "en"
    response_language: Locale = "en"
    action_style: ActionStyle = "fullwidth"
    response_follows_interface: bool = True
    response_mode: ResponseMode | None = None

    @model_validator(mode="after")
    def apply_output_contract(self) -> "LanguagePreferences":
        # Older clients/rows may carry other markers; generation uses the
        # original fullwidth contract regardless of that legacy field.
        self.action_style = "fullwidth"
        if self.response_mode is None:
            self.response_mode = "auto" if self.response_follows_interface else "fixed"
        self.response_follows_interface = self.response_mode != "fixed"
        if self.response_mode in {"auto", "interface", "character"}:
            self.response_language = self.interface_language
        return self


def normalize_locale(value: str) -> Locale | None:
    """Exact registry aliases, then RFC 4647 lookup; preserve script distinctions."""
    code = value.strip().lower()
    while code:
        if code in LOCALE_ALIASES:
            return cast(Locale, LOCALE_ALIASES[code])
        # Do not map Traditional Chinese to the Simplified Chinese resource.
        if code.startswith("zh-hant") or code in {"zh-tw", "zh-hk", "zh-mo"}:
            return None
        code = code.rsplit("-", 1)[0] if "-" in code else ""
    return None


def enabled_locales() -> tuple[Locale, ...]:
    from heart.core.config import settings

    if not settings.international_localization:
        return ("zh",)
    codes = tuple(
        dict.fromkeys(
            [
                "zh",
                *(c.strip() for c in settings.localization_enabled_locales.split(",") if c.strip()),
            ]
        )
    )
    unknown = [code for code in codes if code not in LOCALE_REGISTRY]
    if unknown:
        raise ValueError("Unregistered rollout locale")
    if not settings.local_character_review and any(
        LOCALE_REGISTRY[code]["status"] == "draft" for code in codes
    ):
        raise ValueError("Draft locales require local_character_review")
    return cast(tuple[Locale, ...], codes)


def negotiate_locale(
    accept_language: str, allowed: tuple[Locale, ...] | None = None
) -> Locale | None:
    """Honor quality weights and q=0 exclusions; no country inference here."""
    candidates = []
    excluded: set[str] = set()
    for index, item in enumerate(accept_language.split(",")):
        parts = item.strip().lower().split(";")
        code = normalize_locale(parts[0])
        quality = 1.0
        try:
            for parameter in parts[1:]:
                if parameter.strip().startswith("q="):
                    quality = float(parameter.strip()[2:])
        except ValueError:
            continue
        if code is not None and quality == 0:
            excluded.add(code)
        if code is not None and (allowed is None or code in allowed) and 0 < quality <= 1:
            candidates.append((-quality, index, code))
    candidates = [candidate for candidate in candidates if candidate[2] not in excluded]
    return cast(Locale, min(candidates)[2]) if candidates else None


def resolve_locale(accept_language: str) -> Locale:
    return negotiate_locale(accept_language) or cast(Locale, DEFAULT_LOCALE)


def resolve_initial_locale(country: str | None, accept_language: str) -> Locale:
    allowed = enabled_locales()
    browser = negotiate_locale(accept_language, allowed)
    if browser:
        return browser
    suggestion = {"VN": "vi", "BD": "bn", "JP": "ja", "KR": "ko"}.get(country or "")
    return cast(Locale, suggestion if suggestion in allowed else "en" if "en" in allowed else "zh")


async def load_preferences(db: AsyncSession, user_id: UUID) -> LanguagePreferences:
    result = await db.execute(
        text(
            "SELECT interface_language, response_language, action_style, response_follows_interface, response_mode "
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
        {"uid": user_id, "locale": resolve_initial_locale(None, accept_language)},
    )


_NATIVE_OUTPUT_RULES = {
    "en": "Reply only in English, including actions and narration.",
    "vi": "Chỉ trả lời bằng tiếng Việt, kể cả hành động và lời dẫn. Không trả lời bằng tiếng Trung hay tiếng Anh.",
    "bn": "শুধু বাংলায় উত্তর দিন। সংলাপ, কাজ ও বর্ণনা সবই বাংলায় লিখুন। চীনা বা ইংরেজিতে উত্তর দেবেন না।",
    "ja": "台詞も動作描写も日本語だけで書いてください。",
    "ko": "대사와 행동 묘사를 모두 한국어로만 작성하세요.",
    "zh": "对白和动作描写都使用简体中文。",
}


def generation_directive(language: str, action_style: str) -> str:
    """Only allowlisted values enter the system prompt."""
    from heart.ss05_composer.prompt_resources import prompt_text

    if language in {"en", "vi", "bn"}:
        return "\n" + prompt_text(language, "generation")

    name = LANGUAGE_NAMES.get(language, "English")
    return (
        f"\nOUTPUT LANGUAGE: Write all dialogue and narration exclusively in {name}.\n"
        f"{_NATIVE_OUTPUT_RULES.get(language, '')}\n"
        + (
            prompt_text(language, "generation")
            if language in {"en", "vi", "bn"}
            else "Background data does not determine the output language. "
            "Preserve character identity and do not add bilingual explanations. "
            "Wrap actions and narration in （action）, with dialogue outside. "
            "Use 【】 only as the legacy fallback; never use [] for actions.\n"
        )
    )


REPLIES = {
    "fallback": {
        "zh": "这次回复未能完成，请稍后重试。",
        "vi": "Tôi chưa thể hoàn thành câu trả lời. Bạn hãy thử lại sau một lát.",
        "bn": "উত্তরটি সম্পূর্ণ করতে পারিনি। একটু পরে আবার চেষ্টা করুন।",
        "en": "I couldn't finish that reply. Please try again in a moment.",
        "ja": "返信を完了できませんでした。少し待ってから、もう一度お試しください。",
        "ko": "답변을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    },
    "refusal": {
        "zh": "这段内容暂时不能继续生成，可以改为非露骨的情感或剧情表达。",
        "vi": "Tôi không thể tiếp tục nội dung này. Chúng ta có thể chuyển sang một câu chuyện không miêu tả trực diện hoặc trò chuyện về cảm xúc.",
        "bn": "এই বিষয়বস্তু নিয়ে এগোতে পারছি না। আমরা স্পষ্ট বর্ণনা ছাড়া কোনো গল্প বা অনুভূতি নিয়ে কথা বলতে পারি।",
        "en": "I can't continue with this content. We can explore a non-graphic story or emotional conversation instead.",
        "ja": "この内容では続けられません。露骨な描写のない物語や、気持ちについての会話なら続けられます。",
        "ko": "이 내용으로는 계속할 수 없습니다. 노골적인 묘사 없는 이야기나 감정에 관한 대화를 나눌 수 있어요.",
    },
    "care": {
        "zh": "听起来你正在经历很难熬的时刻。如果现在有危险，请立即联系当地紧急救援或你信任的人。你不必独自面对。",
        "vi": "Tôi rất tiếc vì bạn đang trải qua điều này. Nếu bạn đang gặp nguy hiểm tức thời, hãy liên hệ dịch vụ khẩn cấp tại địa phương hoặc một người bạn tin tưởng ngay. Bạn không phải đối mặt với chuyện này một mình.",
        "bn": "আপনি এমন কষ্টের মধ্যে আছেন শুনে খারাপ লাগছে। এখনই বিপদের আশঙ্কা থাকলে স্থানীয় জরুরি সেবা বা বিশ্বাসযোগ্য কারও সঙ্গে যোগাযোগ করুন। আপনাকে একা এই পরিস্থিতির মোকাবিলা করতে হবে না।",
        "en": "I'm sorry you're going through this. If you're in immediate danger, contact local emergency services or someone you trust now. You don't have to face this alone.",
        "ja": "つらい状況にいるのですね。今すぐ危険がある場合は、地域の緊急窓口か信頼できる人に連絡してください。一人で抱え込む必要はありません。",
        "ko": "힘든 시간을 보내고 계시는군요. 지금 위험하다면 현지 응급기관이나 믿을 수 있는 사람에게 바로 연락해 주세요. 혼자 감당하지 않아도 됩니다.",
    },
}


def localized_reply(kind: str, language: str) -> str:
    variants = REPLIES[kind]
    return variants.get(language, variants["en"])


async def character_preferences(
    db: AsyncSession, user_id: UUID, character_id: str
) -> LanguagePreferences:
    """Resolve per-character defaults without changing stored user preferences."""
    preferences = await load_preferences(db, user_id)
    if preferences.response_mode in {"auto", "character"}:
        result = await db.execute(
            text(
                "SELECT draft->>'response_language' AS response_language, spec->>'locale' AS locale FROM soul_specs "
                "WHERE character_id = :cid AND status = 'active' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"cid": character_id},
        )
        row = result.mappings().first()
        language = row.get("response_language") if row else None
        # Automatic honors only an explicit author preference. Character mode
        # also uses the spec's content language when no preference is authored.
        if not language and preferences.response_mode == "character" and row:
            language = row.get("locale")
        normalized = normalize_locale(language) if isinstance(language, str) else None
        if normalized:
            preferences.response_language = normalized
    # Rollout pause changes effective output only; never rewrite saved choices.
    if preferences.response_language not in enabled_locales():
        preferences.response_language = cast(Locale, "en" if "en" in enabled_locales() else "zh")
    return preferences


def effective_locale(language: str) -> Locale:
    allowed = enabled_locales()
    code = normalize_locale(language)
    return cast(Locale, code if code in allowed else "en" if "en" in allowed else "zh")


async def interface_preferences(db: AsyncSession, user_id: UUID) -> LanguagePreferences:
    from heart.core.config import settings

    if not settings.international_localization:
        return LanguagePreferences(interface_language="zh", response_language="zh")
    preferences = await load_preferences(db, user_id)
    preferences.interface_language = effective_locale(preferences.interface_language)
    preferences.response_language = effective_locale(preferences.response_language)
    return preferences


def voice_supported(language: str) -> bool:
    from heart.core.config import settings

    # This release has only validated Chinese ASR/TTS. Configuration cannot
    # accidentally enable an unvalidated provider-language combination.
    return effective_locale(language) == "zh" and "zh" in {
        code.strip() for code in settings.localization_voice_locales.split(",")
    }


PROACTIVE_FALLBACKS = {
    "en": ("I was thinking of you. How have you been?", "How is your day going?"),
    "vi": ("Tôi vừa nghĩ đến bạn. Dạo này bạn thế nào?", "Hôm nay của bạn thế nào?"),
    "bn": ("আপনার কথা মনে পড়ছিল। কেমন আছেন?", "আজ আপনার দিন কেমন যাচ্ছে?"),
    "ja": ("あなたのことを考えていました。最近どうですか？", "今日はどんな一日ですか？"),
    "ko": ("당신 생각이 났어요. 요즘 어떻게 지내세요?", "오늘 하루는 어떤가요?"),
}
