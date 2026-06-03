"""Regression Runner — compares new generation vs baseline.

Per docs/design/soul_drift_regression.md §3.
Runs 30 prompts through current code, judges each vs baseline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
import yaml

from .baseline_runner import BaselineRunner
from .drift_scorer import DriftResult, DriftScorer, PromptDriftResult
from .voice_judge import VoiceJudge, VoiceJudgment, scan_anti_patterns

logger = structlog.get_logger()


class RegressionRunner:
    """Runs voice drift regression: generate + judge + score.

    Usage:
        runner = RegressionRunner(router, baseline_dir="config/voice_drift/baselines")
        result = await runner.regress("rin")
    """

    def __init__(
        self,
        model_router,
        prompts_path: str = "config/voice_drift/canonical_prompts.yaml",
        thresholds_path: str = "config/voice_drift/thresholds.yaml",
        baseline_dir: str = "config/voice_drift/baselines",
        soul_spec_dir: str = "soul_specs",
    ):
        self._router = model_router
        self._prompts_path = Path(prompts_path)
        self._baseline_dir = Path(baseline_dir)
        self._soul_spec_dir = Path(soul_spec_dir)

        # Load configs
        with open(self._prompts_path, "r", encoding="utf-8") as f:
            self._prompts_cfg = yaml.safe_load(f)
        with open(thresholds_path, "r", encoding="utf-8") as f:
            self._thresholds_cfg = yaml.safe_load(f)

        self._prompts = self._prompts_cfg.get("prompts", [])

        # Init sub-components
        self._judge = VoiceJudge(model_router)
        self._scorer = DriftScorer(
            dimension_weights=self._thresholds_cfg.get("dimension_weights"),
            drift_threshold=self._thresholds_cfg.get("drift_threshold", 0.15),
            drift_fail_threshold=self._thresholds_cfg.get("drift_fail_threshold", 0.30),
            anti_pattern_tolerance=self._thresholds_cfg.get("anti_pattern_tolerance", 0),
        )
        self._baseline_runner = BaselineRunner(
            model_router,
            prompts_path=prompts_path,
            soul_spec_dir=soul_spec_dir,
        )
        self._max_cost = self._thresholds_cfg.get("max_cost_per_character", 1.0)

    def load_soul_spec(self, character: str) -> dict:
        return self._baseline_runner.load_soul_spec(character)

    def load_baseline(self, character: str) -> dict[str, list]:
        """Load baseline JSONL and group by prompt_id.

        Returns dict: prompt_id → list of entries.
        """
        baseline_path = self._baseline_dir / f"{character}_baseline.jsonl"
        if not baseline_path.exists():
            raise FileNotFoundError(
                f"Baseline not found: {baseline_path}. Run 'make voice-baseline CHARACTER={character}' first."
            )

        entries: dict[str, list] = {}
        with open(baseline_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                pid = entry["prompt_id"]
                entries.setdefault(pid, []).append(entry)
        return entries

    async def regress(
        self,
        character: str,
        output_dir: Optional[str] = None,
    ) -> DriftResult:
        """Run full regression for one character.

        Args:
            character: Character ID.
            output_dir: Directory for artifacts. Defaults to artifacts/voice_drift/<timestamp>.

        Returns:
            DriftResult with aggregate score and verdict.
        """
        soul_spec = self.load_soul_spec(character)
        baseline = self.load_baseline(character)
        voice_dna_ids = [vd["id"] for vd in soul_spec.get("voice_dna", [])]

        if output_dir is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output_dir = f"artifacts/voice_drift/{character}_{ts}"
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        prompt_results: list[PromptDriftResult] = []
        judgments: list[VoiceJudgment] = []
        total_cost = 0.0

        for prompt in self._prompts:
            prompt_id = prompt["id"]
            user_msg = prompt["user_message"]

            baseline_entries = baseline.get(prompt_id, [])
            baseline_responses = [e["response"] for e in baseline_entries]

            if not baseline_responses:
                logger.warning("no baseline for prompt", prompt_id=prompt_id)
                continue

            # Generate new response
            system_prompt = self._baseline_runner._build_system_prompt(
                soul_spec, soul_spec.get("display_name", {}).get("zh", character)
            )

            try:
                response = await self._router.call_main(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.7,
                    agent_name=f"regress_{character}",
                )
            except Exception as e:
                logger.error("regression generation failed", prompt_id=prompt_id, error=str(e))
                response = f"[ERROR: {e}]"

            # Scan anti_patterns (deterministic, runs first)
            anti_hits = scan_anti_patterns(response, soul_spec)

            # Judge vs baseline
            judgment = await self._judge.evaluate(
                prompt_id=prompt_id,
                character=character,
                soul_spec=soul_spec,
                user_message=user_msg,
                baseline_responses=baseline_responses[:3],  # max 3 baseline
                candidate_response=response,
            )
            judgment.anti_pattern_hits = anti_hits
            judgments.append(judgment)

            # Score
            pr = self._scorer.compute_prompt_score(judgment, voice_dna_ids)
            prompt_results.append(pr)

            total_cost += 0.008  # ~$0.003 gen + ~$0.005 judge

            # Enforce cost cap
            if total_cost > self._max_cost:
                logger.error("cost cap exceeded", cost=total_cost, cap=self._max_cost)
                break

        # Aggregate
        result = self._scorer.aggregate(prompt_results, character)

        # Write artifacts
        # scores.jsonl
        scores_path = out / "scores.jsonl"
        with open(scores_path, "w", encoding="utf-8") as f:
            for j, pr in zip(judgments, prompt_results, strict=False):
                record = {
                    "prompt_id": pr.prompt_id,
                    "drift_score": pr.drift_score,
                    "anti_pattern_hits": pr.anti_pattern_hits,
                    "d1_match_ratio": pr.d1_match_ratio,
                    "d2_severity": pr.d2_severity,
                    "d3_tone_distance": pr.d3_tone_distance,
                    "d4_inertia_distance": pr.d4_inertia_distance,
                    "d5_embedding_distance": pr.d5_embedding_distance,
                    "verdict": pr.verdict,
                    "vd_matches": j.vd_matches,
                    "free_text_critique": j.free_text_critique,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # summary.json
        summary_path = out / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "character": character,
                    "drift_score": result.drift_score,
                    "total_anti_pattern_hits": result.total_anti_pattern_hits,
                    "verdict": result.verdict,
                    "verdict_color": result.verdict_color,
                    "prompts_evaluated": len(prompt_results),
                    "estimated_cost_usd": round(total_cost, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "regression complete",
            character=character,
            drift_score=round(result.drift_score, 4),
            verdict=result.verdict,
            prompts=len(prompt_results),
            cost=round(total_cost, 4),
        )

        return result
