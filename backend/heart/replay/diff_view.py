"""replay/diff_view.py — Side-by-side diff between raw LLM output and final response.

Uses Rich's built-in diff support for side-by-side comparison.
Anti-pattern differences are highlighted in red.
"""

from typing import Any

from .bundle_dump import PromptBundle  # noqa: F401


def render_diff(bundle: PromptBundle) -> None:
    """Render a side-by-side diff of raw_response vs final_response.

    The left side shows the raw LLM output.
    The right side shows the post-filtered final response.
    Anti-pattern matches that differ between the two are highlighted.
    """
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        _fallback_diff_print(bundle)
        return

    console = Console()
    raw = bundle.raw_response
    final = bundle.final_response

    table = Table(
        title=(
            f"[bold]Response Diff[/]  "
            f"[dim]raw LLM ← → post-filter final[/]\n"
            f"[dim]turn: {bundle.turn_id}[/]"
        ),
        title_style="bold white",
        show_header=True,
        header_style="bold",
    )
    table.add_column("[cyan]Raw LLM Output[/]", width=None, ratio=1)
    table.add_column("[green]Final Response[/]", width=None, ratio=1)

    raw_lines = raw.split("\n")
    final_lines = final.split("\n")
    max_lines = max(len(raw_lines), len(final_lines))

    ap_terms = set()
    for hit in bundle.anti_pattern_hits:
        term = hit.split(":", 1)[-1] if ":" in hit else hit
        ap_terms.add(term.lower())

    for i in range(max_lines):
        raw_line = raw_lines[i] if i < len(raw_lines) else ""
        final_line = final_lines[i] if i < len(final_lines) else ""

        raw_text = _highlight_terms(raw_line, ap_terms, "red", Text)
        final_text = _highlight_terms(final_line, ap_terms, "red", Text)

        if raw_line != final_line:
            if raw_text.cell_len:
                raw_text.stylize("yellow", 0, 1)
            if final_text.cell_len:
                final_text.stylize("yellow", 0, 1)

        table.add_row(raw_text, final_text)

    summary_parts = []
    if bundle.anti_pattern_hits:
        summary_parts.append(
            Text.assemble(
                ("Anti-pattern hits: ", "bold"),
                (", ".join(bundle.anti_pattern_hits), "red"),
            )
        )
    else:
        summary_parts.append(Text.assemble(("No anti-pattern hits", "green")))
    if bundle.blocked:
        summary_parts.append(Text.assemble((" [red bold](BLOCKED)[/]", "")))

    summary = Panel(
        Text.assemble(*summary_parts)
        if len(summary_parts) == 1
        else Text("\n").join(summary_parts)
        if summary_parts
        else Text("No changes"),
        title="Summary",
        border_style="dim",
    )

    console.print(table)
    console.print()
    console.print(summary)


def _highlight_terms(text: str, terms: set[str], color: str, text_cls: type) -> Any:  # noqa: C901
    """Highlight occurrences of anti-pattern terms in a line."""
    if not text or not terms:
        return text_cls(text or "")

    result = text_cls()
    lower = text.lower()

    matches: list[tuple[int, int, str]] = []
    for term in terms:
        pos = 0
        while True:
            idx = lower.find(term, pos)
            if idx < 0:
                break
            matches.append((idx, idx + len(term), text[idx : idx + len(term)]))
            pos = idx + 1

    if not matches:
        return text_cls(text)

    matches.sort(key=lambda x: x[0])
    filtered: list[tuple[int, int, str]] = []
    for start, end, match_text in matches:
        if not filtered or start >= filtered[-1][1]:
            filtered.append((start, end, match_text))

    pos = 0
    for start, end, match_text in filtered:
        if start > pos:
            result.append(text[pos:start])
        result.append(match_text, style=f"bold {color}")
        pos = end

    if pos < len(text):
        result.append(text[pos:])

    return result


def _fallback_diff_print(bundle: PromptBundle) -> None:
    """Plain-text fallback when Rich is not installed."""
    print("\n=== Raw vs Final Response — turn", bundle.turn_id, "===")
    print("\n--- Anti-pattern hits:", bundle.anti_pattern_hits or "none", "---")
    print("\n=== RAW LLM ===")
    print(bundle.raw_response)
    print("\n=== FINAL ===")
    print(bundle.final_response)
    if bundle.raw_response != bundle.final_response:
        print("\n⚠ Responses differ!")
