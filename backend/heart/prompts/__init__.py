"""
SS02 Memory Runtime - Prompt Templates.

Covers:
- MEMORY_EXTRACTION_PROMPT (附录 A)
- EPISODE_SUMMARY_PROMPT (§3.6 Step 3)

Author: 心屿团队
"""

from .episode_summary import EPISODE_SUMMARY_PROMPT
from .memory_extraction import MEMORY_EXTRACTION_PROMPT

__all__ = ["MEMORY_EXTRACTION_PROMPT", "EPISODE_SUMMARY_PROMPT"]
