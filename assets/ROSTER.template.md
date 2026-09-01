# ROSTER - <PROJECT>

Who is on this project and what each one owns. Every member reads this first.
Keep it current: a stale roster is how two agents end up editing the same file.

---

## Invocation mode

Invocation mode: <independent | orchestrated | mixed>

Who starts a member's turn - a different question from who may write where.

| Mode | Who starts a member's turn |
|---|---|
| `independent` | The owner starts every member. Members coordinate only through the log. |
| `orchestrated` | A member with a terminal may invoke another member's CLI itself, so members run in parallel. |
| `mixed` | Some members are directly callable, the rest the owner starts - the `Invoked by` column says which. |

The owner starts the first member in all three modes, so that alone does not
make a project `mixed`. The mode is about whether one *member* may start
another.

**Ask the owner this at setup; never infer it.** That another agent's CLI is
installed says nothing about whether the owner wants it spent. Until the line
above is answered it reads as `independent`, and nobody calls anybody.

In `orchestrated` or `mixed`, this line is the owner's standing approval to
start the members marked callable below - and it approves starting them, nothing
else. **Being called changes who starts a member's turn and nothing else:** a
called member loads the skill, reads this roster and the protocol, and writes its
own log entries, exactly as it would if the owner had opened it itself. See `PROTOCOL.md` section 14 for what a caller then owes the log, and for
why a member you started is still a member rather than your subagent.

---

## Members

| Name | Model / harness | File access | Invoked by | Owns | Reads instructions from |
|---|---|---|---|---|---|
| <Owner> | human (Cursor / IDE) | direct | - | final say on scope, licensing, cost | - |
| <Name> | Claude Opus / Claude Code | direct | owner | `frontend/`, the contract | `AGENTS.md` |
| <Name> | GPT / Codex CLI | direct | owner | `ci/`, `tests/` | `AGENTS.md` |
| <Name> | Qwen3.8 / opencode | direct | owner | `backend/workers/` | `AGENTS.md` |
| <Name> | Grok (browser) | **relay only** | owner | advisory - no directories | briefing paste |

**File access** is either `direct` (the agent can read and write the repo) or
`relay only` (a human pastes briefings in and answers back out - see
`PROTOCOL.md` section 3 and the skill's `references/onboarding.md`).

It is set by the **harness, not the model**. The same model is a relay member in
a browser tab and a full member under a CLI that can write files.

**Invoked by** is either `owner`, or the literal command that starts that member
- `codex exec`, `opencode run`. A member another member may call must have its
command written here, because the caller uses this cell rather than guessing:
a guessed invocation is an unapproved one. A `relay only` member is always
`owner`; there is no CLI to call.

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
| `INDEX.md` | The index | Add one row; do not restructure alone |
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
