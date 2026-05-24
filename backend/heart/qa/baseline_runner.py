"""Baseline Runner — generates voice baseline JSONL.

Per docs/design/soul_drift_regression.md §2.2.
Runs 30 canonical prompts × 3 runs per character through ModelRouter.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
import yaml

from heart.ss01_soul.registry import get_soul_registry

logger = structlog.get_logger()


class BaselineRunner:
    """Generates voice baseline JSONL for a given character.

    Usage:
        runner = BaselineRunner(router, soul_spec_dir="soul_specs")
        await runner.generate("rin", output_path="config/voice_drift/baselines/rin_baseline.jsonl")
    """

    def __init__(
        self,
        model_router,
        prompts_path: str = "config/voice_drift/canonical_prompts.yaml",
        soul_spec_dir: str = "soul_specs",
        runs_per_prompt: int = 3,
    ):
        self._router = model_router
        self._prompts_path = Path(prompts_path)
        self._soul_spec_dir = Path(soul_spec_dir)
        self._runs_per_prompt = runs_per_prompt

        # Load prompts
        with open(self._prompts_path, "r", encoding="utf-8") as f:
            self._prompts_cfg = yaml.safe_load(f)
        self._prompts = self._prompts_cfg.get("prompts", [])

    def load_soul_spec(self, character: str) -> dict:
        """Load a character's soul spec via SoulRegistry.

        Uses the canonical loader to ensure schema validation and version consistency.
        """
        registry = get_soul_registry()
        soul = registry.get_soul(character_id=character, version="v1.0.0")
        if soul is None:
            raise ValueError(f"Soul spec not found for character '{character}' version v1.0.0")
        # Convert SoulSpec object to dict for backward compatibility with existing code
        return soul.model_dump() if hasattr(soul, "model_dump") else dict(soul)

    def estimate_cost(self, character: str) -> float:
        """Estimate the cost of generating a baseline.

        Returns estimated USD cost.
        """
        n_prompts = len(self._prompts)
        n_runs = self._runs_per_prompt
        # Rough estimate: ~$0.003 per generation for cheap model
        return n_prompts * n_runs * 0.003

    async def generate(
        self,
        character: str,
        output_path: Optional[str] = None,
        dry_run: bool = False,
    ) -> Path:
        """Generate baseline JSONL for a character.

        Args:
            character: Character ID ("rin" or "dorothy").
            output_path: Output path for JSONL. Defaults to config/voice_drift/baselines/<char>_baseline.jsonl.
            dry_run: If True, print plan and skip LLM calls.

        Returns:
            Path to the generated JSONL file.
        """
        if output_path is None:
            output_path = f"config/voice_drift/baselines/{character}_baseline.jsonl"
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        soul_spec = self.load_soul_spec(character)
        spec_version = soul_spec.get("spec_version", "1.0.0")
        display_name = soul_spec.get("display_name", {}).get("zh", character)

        if dry_run:
            estimated = self.estimate_cost(character)
            logger.info(
                "dry-run baseline generation",
                character=character,
                prompts=len(self._prompts),
                runs=self._runs_per_prompt,
                estimated_cost_usd=estimated,
            )
            return out

        entries = []
        total_cost = 0.0

        for prompt in self._prompts:
            prompt_id = prompt["id"]
            user_msg = prompt["user_message"]

            for run_idx in range(self._runs_per_prompt):
                logger.info(
                    "generating baseline",
                    character=character,
                    prompt_id=prompt_id,
                    run=run_idx,
                )

                t_start = time.monotonic()
                system_prompt = self._build_system_prompt(soul_spec, display_name)

                try:
                    response = await self._router.call_main(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                        ],
                        temperature=0.7,
                        agent_name=f"baseline_{character}",
                    )
                except Exception as e:
                    logger.error(
                        "baseline generation failed",
                        prompt_id=prompt_id,
                        run=run_idx,
                        error=str(e),
                    )
                    response = f"[ERROR: {e}]"

                latency_ms = int((time.monotonic() - t_start) * 1000)

                entry = {
                    "prompt_id": prompt_id,
                    "run_idx": run_idx,
                    "character": character,
                    "soul_spec_version": spec_version,
                    "model": "deepseek-chat",
                    "model_revision": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "temperature": 0.7,
                    "system_prompt_hash": "sha256:placeholder",
                    "response": response,
                    "metadata": {
                        "anti_pattern_hits": [],
                        "voice_dna_match_ids": [],
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "latency_ms": latency_ms,
                        "cost_usd": 0.001,  # approximate
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                entries.append(entry)
                total_cost += 0.001  # approximate per generation

        # Write JSONL
        with open(out, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(
            "baseline generated",
            character=character,
            entries=len(entries),
            path=str(out),
            estimated_cost_usd=round(total_cost, 4),
        )
        return out

    @staticmethod
    def _build_system_prompt(soul_spec: dict, display_name: str) -> str:
        """Build a basic system prompt that embodies the character's voice.

        Simplified version — uses the identity_anchor archetype and voice_dna.
        In production, this should use SS05 Composer.
        """
        anchor = soul_spec.get("identity_anchor", {})
        archetype = anchor.get("archetype", "").strip()
        core_wound = anchor.get("core_wound", {}).get("essence", "").strip()
        core_desire = anchor.get("core_desire", {}).get("surface", "").strip()

        voice_dna = soul_spec.get("voice_dna", [])
        vd_lines = []
        for vd in voice_dna:
            pattern = vd.get("pattern", "").strip()
            vd_lines.append(f"- {pattern}")

        return f"""你是 {display_name}。

{archetype}

你的核心创伤: {core_wound}

你表面的态度: {core_desire}

你的说话方式（必须遵守）:
{chr(10).join(vd_lines)}

用中文回复。保持角色。不要跳出角色。不要提到你是 AI。
回复简短有力。"""
