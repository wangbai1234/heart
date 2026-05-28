"""replay/layer_view.py — Rich tree view of composer layers.

Renders PromptBundle layers as a coloured tree:
    Soul ──────> identity anchor, archetype, core wound
    Memory ────> retrieved memories, L4 status
    Emotion ───> VAD, active emotions, mood
    ── ...
    Director ──> response directive

Anti-pattern matches are highlighted in red.
"""

from .bundle_dump import PromptBundle  # noqa: F401


def render_layer_tree(bundle: PromptBundle) -> None:  # noqa: C901
    """Render a Rich Tree of composer layers with their content.

    Side effects: prints to the active Rich Console.
    """
    try:
        from rich.console import Console
        from rich.tree import Tree
    except ImportError:
        _fallback_layer_print(bundle)
        return

    console = Console()
    tree = Tree(
        f"[bold]🔬 Prompt Bundle — turn [cyan]{bundle.turn_id}[/][/]",
        guide_style="dim",
    )

    # System prompt summary
    sys_branch = tree.add("[bold blue]System Prompt[/]")
    sys_branch.add(f"[dim]{len(bundle.system_prompt)} chars[/]")
    for line in bundle.system_prompt.split("\n")[:12]:
        if line.strip():
            sys_branch.add(line.strip()[:120])
    if len(bundle.system_prompt.split("\n")) > 12:
        sys_branch.add("[dim]… (truncated)[/]")

    # Messages
    msg_branch = tree.add(f"[bold blue]Messages[/] ({len(bundle.messages)} total)")
    for _i, msg in enumerate(bundle.messages):
        role_color = {"system": "yellow", "user": "green", "assistant": "magenta"}
        c = role_color.get(msg.get("role", ""), "white")
        preview = (msg.get("content", "") or "")[:80].replace("\n", " ")
        msg_branch.add(f"[{c}]{msg['role']}[/]: {preview}")

    # Layers (from recorded snapshots)
    layer_order = [
        ("soul", "Soul (SS01)", "cyan"),
        ("memory", "Memory (SS02)", "green"),
        ("emotion", "Emotion (SS03)", "magenta"),
        ("relationship", "Relationship (SS04)", "yellow"),
        ("inner_state", "Inner State (SS06)", "blue"),
        ("director", "Director / Hard Constraints", "red"),
    ]

    for key, label, color in layer_order:
        if key not in bundle.layers:
            continue
        layer = bundle.layers[key]
        branch = tree.add(f"[bold {color}]{label}[/]")
        content = layer.content
        if content:
            for line in content.split("\n")[:6]:
                if line.strip():
                    branch.add(line.strip()[:120])
        if layer.token_count:
            branch.add(f"[dim]~{layer.token_count} tokens[/]")
        if layer.metadata:
            for mk, mv in layer.metadata.items():
                branch.add(f"[dim]{mk}:[/] {mv}")

    # Anti-pattern section
    ap_branch = tree.add(
        f"[bold ]Anti-Pattern Filter[/] — {len(bundle.anti_pattern_hits)} hit(s)"
    )
    if bundle.anti_pattern_hits:
        for hit in bundle.anti_pattern_hits:
            ap_branch.add(f"[red]✗ {hit}[/]")
        # Highlight matched substrings in final response
        final = bundle.final_response
        for hit in bundle.anti_pattern_hits:
            term = hit.split(":", 1)[-1] if ":" in hit else hit
            idx = final.lower().find(term.lower())
            if idx >= 0:
                snippet = final[max(0, idx - 20):idx + len(term) + 20]
                ap_branch.add(
                    f"[red]…{snippet.replace(term, f'[bold red]{term}[/]')}…[/]"
                )
    else:
        ap_branch.add("[green]✓ clean[/]")

    # Critic
    critic_branch = tree.add("[bold]Critic Agent[/]")
    if bundle.critic_score is not None:
        score_color = "green" if bundle.critic_score >= 0.7 else "yellow"
        critic_branch.add(f"Score: [{score_color}]{bundle.critic_score:.2f}[/]")
        if bundle.critic_feedback:
            critic_branch.add(f"[dim]{bundle.critic_feedback[:200]}[/]")
    else:
        critic_branch.add("[dim]not sampled[/]")

    # Metadata footer
    footer = tree.add("[bold]Metadata[/]")
    footer.add(f"Model: {bundle.model_name}")
    footer.add(f"Latency: {bundle.latency_ms}ms")
    footer.add(f"Tokens: {bundle.token_count}")
    footer.add(f"Character: {bundle.character_id}")

    console.print(tree)


def _fallback_layer_print(bundle: PromptBundle) -> None:
    """Plain-text fallback when Rich is not installed."""
    print(f"\n=== Prompt Bundle — turn {bundle.turn_id} ===")
    print(f"\n--- System Prompt ({len(bundle.system_prompt)} chars) ---")
    print(bundle.system_prompt[:500])
    print(f"\n--- Messages ({len(bundle.messages)}) ---")
    for msg in bundle.messages:
        print(f"  [{msg['role']}] {msg['content'][:100]}")
    print("\n--- Layers ---")
    for key, layer in bundle.layers.items():
        print(f"\n  [{key}]")
        if layer.content:
            print(f"    {layer.content[:200]}")
    print(f"\n--- Anti-Pattern Hits ({len(bundle.anti_pattern_hits)}) ---")
    for hit in bundle.anti_pattern_hits:
        print(f"  ✗ {hit}")
    if bundle.critic_score is not None:
        print(f"\n--- Critic Score: {bundle.critic_score:.2f} ---")
    print("\n--- Metadata ---")
    print(f"  Model: {bundle.model_name}  Latency: {bundle.latency_ms}ms  Tokens: {bundle.token_count}")
