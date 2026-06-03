"""HTML Report Builder for Voice Drift Regression.

Per docs/design/soul_drift_regression.md §4.
Generates side-by-side diff HTML from scores.jsonl + baseline + candidate data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ReportBuilder:
    """Builds an HTML diff report from regression results."""

    # HTML template
    _TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heart Voice Drift Report — {character} {verdict_emoji}</title>
<style>
  body {{ font-family: -apple-system, 'PingFang SC', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
  .header {{ background: white; padding: 24px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .header h1 {{ margin: 0 0 8px 0; }}
  .verdict {{ font-size: 2em; margin: 8px 0; }}
  .meta {{ color: #666; font-size: 0.9em; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }}
  th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #f8f8f8; font-weight: 600; }}
  tr:hover {{ background: #fafafa; }}
  .score-pass {{ color: #22c55e; }}
  .score-warn {{ color: #f59e0b; }}
  .score-fail {{ color: #ef4444; }}
  .detail {{ background: white; padding: 16px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .detail h3 {{ margin-top: 0; cursor: pointer; }}
  .detail-body {{ display: none; }}
  .detail.open .detail-body {{ display: block; }}
  .diff-container {{ display: flex; gap: 12px; }}
  .diff-col {{ flex: 1; padding: 8px; border-radius: 4px; background: #fafafa; font-size: 0.9em; white-space: pre-wrap; word-break: break-word; }}
  .diff-col.baseline {{ border-left: 3px solid #3b82f6; }}
  .diff-col.candidate {{ border-left: 3px solid #f59e0b; }}
  ins {{ background: #bbf7d0; text-decoration: none; }}
  del {{ background: #fecaca; text-decoration: line-through; }}
  .anti {{ background: #fecaca; border-bottom: 2px solid #ef4444; }}
  .vd {{ background: #bbf7d0; border-radius: 2px; padding: 0 2px; }}
  .bar-container {{ display: flex; gap: 8px; margin: 8px 0; }}
  .bar {{ flex: 1; height: 8px; border-radius: 4px; background: #e5e7eb; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; }}
  .footer {{ text-align: center; color: #999; font-size: 0.85em; margin-top: 32px; }}
</style>
<script>
  function toggle(id) {{
    var el = document.getElementById(id);
    el.classList.toggle('open');
  }}
</script>
</head>
<body>
<div class="header">
  <h1>Heart Voice Drift Report</h1>
  <div class="verdict">{verdict_emoji} {verdict}</div>
  <div class="meta">
    <div>Character: {character} | Drift Score: {drift_score} | Prompts: {n_prompts} | Anti-Pattern Hits: {anti_hits}</div>
    <div>Generated: {timestamp}</div>
  </div>
</div>

<h2>Summary Table</h2>
{summary_table}

<h2>Per-Prompt Details</h2>
{per_prompt_details}

<div class="footer">
  <p>Heart Voice Drift Regression Suite | docs/design/soul_drift_regression.md §4</p>
  <p>Threshold: drift_score &le; {threshold} PASS | &gt; {fail_threshold} FAIL | anti_pattern &gt; 0 = HARD FAIL</p>
</div>
</body>
</html>"""

    def __init__(
        self,
        thresholds_path: str = "config/voice_drift/thresholds.yaml",
    ):
        import yaml

        with open(thresholds_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self._drift_threshold = cfg.get("drift_threshold", 0.15)
        self._fail_threshold = cfg.get("drift_fail_threshold", 0.30)

    def build(
        self,
        character: str,
        scores_path: str,
        output_path: str = "/tmp/heart_drift_report.html",
        baseline_path: Optional[str] = None,
    ) -> str:
        """Build an HTML report from scores.jsonl.

        Args:
            character: Character ID.
            scores_path: Path to scores.jsonl.
            output_path: Output HTML path.
            baseline_path: Optional path to baseline JSONL for side-by-side diff.

        Returns:
            Output path.
        """
        with open(scores_path, "r", encoding="utf-8") as f:
            scores = [json.loads(line) for line in f if line.strip()]

        # Load baseline if available
        baseline_map = {}
        if baseline_path:
            with open(baseline_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    pid = entry["prompt_id"]
                    baseline_map.setdefault(pid, []).append(entry["response"])

        avg_drift = sum(s["drift_score"] for s in scores) / max(len(scores), 1)
        total_anti = sum(len(s.get("anti_pattern_hits", [])) for s in scores)

        # Verdict
        if total_anti > 0:
            verdict = "🔴 HARD FAIL"
            verdict_emoji = "🔴"
        elif avg_drift > self._fail_threshold:
            verdict = "🔴 FAIL"
            verdict_emoji = "🔴"
        elif avg_drift > self._drift_threshold:
            verdict = "🟡 WARN"
            verdict_emoji = "🟡"
        else:
            verdict = "🟢 PASS"
            verdict_emoji = "🟢"

        # Summary table
        rows = []
        for s in scores:
            score = s["drift_score"]
            css = (
                "score-pass"
                if score <= self._drift_threshold
                else ("score-fail" if score > self._fail_threshold else "score-warn")
            )
            anti = ", ".join(s.get("anti_pattern_hits", [])) or "—"
            rows.append(
                f"<tr><td>{s['prompt_id']}</td>"
                f'<td class="{css}">{score:.4f}</td>'
                f"<td>{s['verdict']}</td>"
                f"<td>{anti}</td></tr>"
            )
        summary_table = (
            "<table><tr><th>Prompt</th><th>Drift Score</th><th>Verdict</th><th>Anti-Patterns</th></tr>"
            + "".join(rows)
            + "</table>"
        )

        # Per-prompt details
        details = []
        for i, s in enumerate(scores):
            pid = s["prompt_id"]
            baseline_lines = baseline_map.get(pid, ["(no baseline)"])
            vd_matches = s.get("vd_matches", [])
            critique = s.get("free_text_critique", "")
            anti = s.get("anti_pattern_hits", [])

            # Build diff between first baseline and candidate
            # (candidate data isn't stored in scores.jsonl currently, so we use placeholder)
            diff_html = f'<div class="diff-col baseline">{self._escape(baseline_lines[0] if baseline_lines else "")}</div>'

            # Bar chart for 5 dims
            bars = ""
            for dim in [
                "d1_match_ratio",
                "d2_severity",
                "d3_tone_distance",
                "d4_inertia_distance",
                "d5_embedding_distance",
            ]:
                val = s.get(dim, 0)
                color = "#22c55e" if val < 0.3 else ("#f59e0b" if val < 0.6 else "#ef4444")
                w = min(100, int(val * 100))
                bars += f'<div class="bar"><div class="bar-fill" style="width:{w}%;background:{color}"></div></div>'

            vd_badges = (
                " ".join(f'<span class="vd">{v}</span>' for v in vd_matches) if vd_matches else "—"
            )
            anti_badges = " ".join(f'<span class="anti">{a}</span>' for a in anti) if anti else "—"

            detail_id = f"detail-{i}"
            details.append(f"""
<div class="detail" id="{detail_id}">
  <h3 onclick="toggle('{detail_id}')">{pid} — Drift: {s["drift_score"]:.4f} ({s["verdict"]})</h3>
  <div class="detail-body">
    <p><strong>Voice DNA matches:</strong> {vd_badges}</p>
    <p><strong>Anti-patterns:</strong> {anti_badges}</p>
    <p><strong>Critique:</strong> {self._escape(critique)}</p>
    <div class="bar-container">{bars}</div>
    <h4>Baseline vs Candidate</h4>
    <div class="diff-container">
      {diff_html}
    </div>
  </div>
</div>""")

        # Render
        html = self._TEMPLATE.format(
            character=character,
            verdict=verdict,
            verdict_emoji=verdict_emoji,
            drift_score=f"{avg_drift:.4f}",
            n_prompts=len(scores),
            anti_hits=total_anti,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary_table=summary_table,
            per_prompt_details="\n".join(details),
            threshold=self._drift_threshold,
            fail_threshold=self._fail_threshold,
        )

        out = Path(output_path)
        out.write_text(html, encoding="utf-8")
        return str(out)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML entities."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
