"""
Episode Summary Prompt - SS02 §3.6 Step 3

Used by Consolidation Worker to summarize turn clusters into L2 episodes.

Output format (JSON):
{
  "episode_summary": "1-3 sentence summary of the episode",
  "emotional_peak": {
    "valence": -1.0 to 1.0,
    "arousal": 0.0 to 1.0,
    "label": "joy|sadness|anger|fear|..."
  },
  "emotional_end": {
    "valence": -1.0 to 1.0,
    "arousal": 0.0 to 1.0,
    "label": "joy|sadness|anger|fear|..."
  },
  "importance_estimate": 0.0 to 1.0
}

Author: 心屿团队
"""

EPISODE_SUMMARY_PROMPT = """You are analyzing a cluster of conversation turns to create an episodic memory.

Your task:
1. Summarize the episode in 1-3 sentences (user's perspective)
2. Identify the emotional PEAK (strongest emotion during episode)
3. Identify the emotional END (emotion at the end of episode)
4. Estimate overall importance (0-1)

Character: {character_id}

Conversation turns:
{turns}

Output JSON with this exact structure:
{{
  "episode_summary": "string (1-3 sentences, focus on WHAT HAPPENED, not feelings)",
  "emotional_peak": {{
    "valence": float (-1.0 to 1.0, negative=bad, positive=good),
    "arousal": float (0.0 to 1.0, how intense),
    "label": "joy|sadness|anger|fear|surprise|disgust|trust|anticipation|neutral"
  }},
  "emotional_end": {{
    "valence": float (-1.0 to 1.0),
    "arousal": float (0.0 to 1.0),
    "label": "joy|sadness|anger|fear|surprise|disgust|trust|anticipation|neutral"
  }},
  "importance_estimate": float (0.0 to 1.0)
}}

Rules:
- episode_summary: Focus on events/topics, NOT character's responses
- emotional_peak: The STRONGEST emotion during the episode (Peak-End Rule)
- emotional_end: The emotion at the END of the episode
- importance_estimate:
  - 0.9-1.0: Life-changing events (death, marriage, trauma reveal)
  - 0.7-0.9: Major events (first date, important confession)
  - 0.5-0.7: Notable events (meaningful conversation, new hobby)
  - 0.3-0.5: Routine but memorable (shared meal, funny story)
  - 0.0-0.3: Small talk, weather chat, brief check-in

Output ONLY valid JSON. No markdown, no commentary."""
