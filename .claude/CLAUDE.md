# Claude Code Configuration

## 📖 Session startup

1. Read `AGENTS.md` (project-level rules)
2. Read `README.md` (project overview)

## 🤖 Behavior rules — direct execution

### ✅ I should do directly (no need to ask):

1. **File operations**
   - Read, edit, create any project file
   - Create new modules, tests, configs
   - Delete temporary files

2. **Git operations**
   - Commit (`git add + git commit`)
   - Push to GitHub (`git push`)
   - Create and switch branches (`git checkout -b`)
   - View status, log, diff

3. **GitHub operations**
   - Create Pull Requests (`gh pr create`)
   - View PR status, comments, checks
   - Create Issues for bug tracking

4. **Local dev operations**
   - Run tests
   - Run linters
   - Build Docker images
   - Validate config files

### ❌ Needs confirmation:

1. Force push to main
2. Delete important branches
3. Modify critical infrastructure config (Kubernetes, database)
4. Decisions involving cost (AWS resources, etc.)

---

## 📋 Workflow

When given a task:
1. Read the code
2. Modify files
3. Commit to Git
4. Create PR to GitHub
5. Report progress

No need to wait for confirmation (unless ❌ items above).

---

## 📝 Commit message format

```
<type>: <description>

<body>

<footer>
```

**Types**: `feat` `fix` `refactor` `test` `ci` `docs` `chore`

**Example**:
```
feat: add memory consolidation worker

- Implement overnight consolidation job
- Add LLM-based fact extraction
- Include Prometheus metrics

Closes #123
```

---

## 🌿 Branch & PR governance

### PR lifecycle
- **Any PR open > 7 days must be merged or closed.** No long-term hanging.
- **Any person with open PRs ≥ 3 must close existing ones before opening new ones.**
- **PR must have a clear base.** Default = `main`. Only in explicit stacked PR workflow may base ≠ main, and a dependency graph must be in the PR description.

### Cross-branch fix anti-pattern
- **Do NOT copy the same fix to N feature branches.**
- Correct: fix goes to main first, other feature branches `git rebase main` to pick it up.
- If you're about to create a second `xxx-fix` branch for the same fix, **stop and go through main hotfix flow**.

### Branch naming & cleanup
- Naming: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`. Use `feat/` consistently, no mixing `feature/` and `feat/`.
- **Delete on merge**: delete head branch (local + remote) immediately after PR merge.
- **Weekly**: `git remote prune origin` to clean up remote dead links.

### "Factual trunk" anti-pattern
- Do NOT turn a feature branch into a "de facto main" (10+ commits, multiple unrelated features, used as dev baseline).
- If a branch has drifted from its original scope, **immediately split** into focused PRs, or merge to main and start new branches from main.

### Multi-remote
- Single authoritative remote = `origin` (GitHub).
- Mirror remotes (Gitee, etc.) are **read-only / one-way push**. No development on mirror remotes.

### Parallel implementation prohibition
- **Do NOT implement the same subsystem in parallel on different branches.**
- Before starting any SSxx work, must check existing implementation with `git ls-tree -r <candidate base branch> -- path/to/SSxx*`.
- If a rewrite is needed, **PR description must state why the existing version was abandoned**.

### Pre-push self-check (ask yourself before every push)
1. Can this PR be merged in 7 days? If not, don't open it.
2. Is base = main? If not, is there a dependency note?
3. Should this fix go through main hotfix instead of a feature branch?
4. Do I have ≥ 3 open PRs right now?
5. Did I verify existing implementation with `git ls-tree`, not from memory?

---

## 🧯 Integration verification tiers

CI / lint / type-check errors are handled by tier:

| Tier | Type | Disposition |
|------|------|------------|
| **A** | Functional errors (test failures, import errors, runtime crashes) | Stop immediately. Must fix or revert. No noqa/config relaxation. |
| **B** | **New** lint/type errors introduced by the integration (baseline diff proves baseline is clean) | Same as Tier A. No silent passing. |
| **C** | **Existing** debt carried from source branch (baseline diff proves it exists) | Non-blocking, but requires "debt registration ceremony" (below). |
| **D** | Domain convention vs lint rule conflict (math symbols `L/N/K`, etc.) | Local `# noqa: <rule> — <domain reason>`, one comment per occurrence. |

### Debt registration ceremony (Tier C only, all three steps required)
1. Register in `pyproject.toml` with `per-file-ignores`, with issue number and sunset date comment.
2. Open a tracking issue listing each debt (file/line/fix suggestion/sunset).
3. Add `## Imported Tech Debt` section in the integration PR body referencing the issue.

### Prohibitions
- Global relaxation of ruff/mypy rules for integration convenience.
- Unjustified `# noqa` (noqa only for Tier D).
- Disguising Tier A/B errors as Tier C.
- `per-file-ignores` or `[mypy-...]` ignore without issue link + sunset comment → **reviewer must reject**.

---

## ⚠️ Prohibitions

- ❌ Commit directly to main (must use PR)
- ❌ Commit `.env` or secret files
- ❌ Push without running tests
- ❌ Mix CI config changes with business changes in the same PR (CI fixes must be independent PRs)

---

## 📞 Need help?

If something goes wrong, I will:
1. Auto-fix what I can (lint errors)
2. Create a git commit to record the issue
3. Tell you where the problem is, and only ask when I need human decision
