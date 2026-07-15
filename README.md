# Mythos — portable install

Drop this into any repo's root and Claude Code will pick up the Mythos agent immediately — no path edits needed.

## Install

1. Unzip so these land at your repo root, preserving the paths:
   ```
   your-repo/
     docs/FABLE5_INSTRUCTIONS.md
     docs/MYTHOS_INSTRUCTIONS.md
     .claude/agents/mythos.md
   ```
   (If `docs/` or `.claude/agents/` already exist, just merge the files in — nothing here overwrites unrelated content.)
2. Commit them.
3. In Claude Code, invoke with **"use the mythos agent"** (or reference it by name — see your Claude Code docs for the exact trigger phrasing in your version).

## What's in the box

- **`docs/FABLE5_INSTRUCTIONS.md`** — the portable core: trigger→action procedures for thinking through bugs (Part A), building new capabilities (Part B), and adapting the procedures to any module via a 5-slot table — RUN / TEST / REPRO / PRECEDENT / WIRING (Part C). Ends with a 7-item pre-send gate. Nothing in this file is domain-specific; it's meant to be identical across every project you drop it into.
- **`docs/MYTHOS_INSTRUCTIONS.md`** — the specialization layer. Ships with the rules and capabilities Mythos was built with (trading/fintech: money math, UTC time, exchange-API safety, secrets/live-trading gates, backtest lookahead checks). **Part 3 of this file is the adaptation guide** — read it first in a new project.
- **`.claude/agents/mythos.md`** — the agent definition. Loads both docs above and enforces their gates before every answer.

## Adapting Mythos to a project that isn't trading/fintech

`MYTHOS_INSTRUCTIONS.md` Part 1 (the R-series operating rules — inheritance, and the general discipline of "verify before claiming, grep before assuming") is domain-agnostic and should stay as-is. **Part 2 (the C-series capabilities) is trading-specific and won't fit a non-financial project out of the box.** Two ways to proceed:

- **Different domain (e.g. a content platform, a game, an internal tool):** replace Part 2's C-series sections with capabilities suited to *your* domain, following the same format each existing section uses — trigger→action rules, one worked example, the failure it prevents. Keep the R-series and the final-gate structure.
- **General-purpose, no specialization needed:** delete `MYTHOS_INSTRUCTIONS.md` and the agent file's reference to it, and just use `FABLE5_INSTRUCTIONS.md` directly (rename the agent, or invoke Fable's procedures without a named agent at all — they're plain instructions, not tool-gated).

Either way, re-fill the Part C module-adaptation table in `FABLE5_INSTRUCTIONS.md` for the new repo's actual stack (its own RUN/TEST commands, precedent files, wiring points) — that table is what keeps the procedures honest about what's actually runnable and tested in *this* codebase, not the one Mythos was born in.

## Where this came from

Built and refined across the CoinBase and FinSurfing repos. If you improve a rule in a way that isn't project-specific, consider porting the fix back to those repos' copies too — the R-series and Part A/B procedures are meant to converge, not drift.
