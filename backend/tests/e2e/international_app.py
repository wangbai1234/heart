"""E2E-only model double; never imported by production entrypoints."""

from heart.api import wiring
from heart.api.main import create_app as production_app


class LanguageAwareTestRouter:
    def _reply(self, messages):
        system = messages[0]["content"]
        language = next(
            (
                language
                for language in ("English", "Japanese", "Korean")
                if f"OUTPUT LANGUAGE: Write all dialogue and narration in {language}." in system
            ),
            None,
        )
        if language is None:
            raise AssertionError("Generation preferences did not reach the model")
        replies = {
            "English": ("Smiles", "What story would you like to write?"),
            "Japanese": ("微笑む", "どんな物語を書きたいですか？"),
            "Korean": ("미소 짓는다", "어떤 이야기를 쓰고 싶으세요?"),
        }
        action, dialogue = replies[language]
        left, right = (
            ("*", "*")
            if "*action*" in system
            else ("（", "）")
            if "（action）" in system
            else ("(", ")")
        )
        return f"{left}{action}{right} {dialogue}"

    async def stream_for(self, model, messages, **kwargs):
        kwargs["meta"].update(served_model=model, degraded_to=None)
        yield self._reply(messages)

    async def call_cheap(self, messages, **kwargs):
        return (
            self._reply(messages) if kwargs.get("agent_name", "").startswith("Opening.") else "{}"
        )

    async def call_background(self, messages, **kwargs):
        return "{}"


def create_app():
    wiring.get_model_router = lambda: LanguageAwareTestRouter()
    return production_app()
