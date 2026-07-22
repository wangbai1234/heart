"""SS09 — Story/剧情 mode.

Turn-based interactive-fiction engine where the LLM acts as a GM (game master)
running an imported scenario. Deliberately independent of the persona chat
pipeline (ss05/ss07): a story turn is a plain ``ModelRouter.stream_for()`` call
with a GM system prompt, persisted in its own tables (``story_scenarios`` /
``story_runs`` / ``story_messages``, migration 042).
"""
