# ROSTER - <PROJECT>

Who is on this project and what each one owns. Every member reads this first.
Keep it current: a stale roster is how two agents end up editing the same file.

---

## Members

| Name | Model / harness | File access | Owns | Reads instructions from |
|---|---|---|---|---|
| <Owner> | human (Cursor / IDE) | direct | final say on scope, licensing, cost | - |
| <Name> | Claude Opus / Claude Code | direct | `frontend/`, the contract | `AGENTS.md` |
| <Name> | GPT / Codex CLI | direct | `ci/`, `tests/` | `AGENTS.md` |
| <Name> | Qwen3.8 / opencode | direct | `backend/workers/` | `AGENTS.md` |
| <Name> | Grok (browser) | **relay only** | advisory - no directories | briefing paste |

**File access** is either `direct` (the agent can read and write the repo) or
`relay only` (a human pastes briefings in and answers back out - see
`PROTOCOL.md` section 3 and the skill's `references/onboarding.md`).

It is set by the **harness, not the model**. The same model is a relay member in
a browser tab and a full member under a CLI that can write files.

A member with `relay only` access should not own directories. They cannot see
the code, so they cannot be responsible for it.

The owner's own editor belongs in this table too. It is not a member and owns
nothing, but it is the reason a file can change under a member who is mid-edit -
see `PROTOCOL.md` section 6.

---

## Why the split is drawn this way

One line per member: what they are good at that made this their territory, and
how they usually go wrong so the others know what to check. Keep it honest;
this is what a new member reads to understand the shape of the team.

| Name | Assigned here because | Usual failure to watch for |
|---|---|---|
| <Name> | | |

The skill's `references/task-fit.md` has current per-provider profiles and a
routing table. Revisit this section whenever a member changes model generation.

---

## Shared, jointly owned

| Path | Purpose | Change rule |
|---|---|---|
| `<contract path>` | The machine-readable interface every member generates code from | Needs review from every affected member |
| `CHATLOG.md` | The index | Add one row; do not restructure alone |
| `PROTOCOL.md` | How we work | Owner decides changes |

---

## The boundary rule

**Never edit a directory you do not own.** If you need something from another
member's area, propose a contract change or open an `AGENT-` thread. Do not
reach across, and do not guess at another member's implementation.

This is what makes parallel work possible: each member has a complete,
authoritative description of the others that never requires reading their code.

---

## Unassigned

Anything not listed above has no owner yet. **Claim it in a thread before
working in it**, so the others find out from the log rather than from a
collision.
