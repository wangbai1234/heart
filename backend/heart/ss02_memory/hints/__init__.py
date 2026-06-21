"""
SS02 Memory Hints — Regex-based auxiliary signals for the slow-path LLM Extractor.

These hints are NOT authoritative. They serve as lightweight regex-guessed
clues to help the LLM Extractor focus attention. The Extractor may confirm,
reject, or refine them.

Author: 心屿团队
"""

from .regex_hints import Hint, RegexHintsProvider

__all__ = ["Hint", "RegexHintsProvider"]
