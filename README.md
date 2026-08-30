# Agents Collaboration Protocol

**Make Claude Code, Codex, Cursor, opencode, Qwen and chat-only models
collaborate on the same repository - without overwriting each other or
re-deciding settled questions.**

A file-based collaboration protocol for AI coding agents that do not share a
session, memory, or runtime. Zero dependencies, plain Markdown, one
standard-library Python CLI. Works with any agent that can read a file.

---

## The problem

Multiple agents on one repo fail in a specific way: they cannot see each other.
No shared conversation, no shared memory, no way to ask a quick question. Left
alone they overwrite each other's files, re-decide settled questions, and hand
the human the same problem three times in three different words.

Handing a summary from one session to the next does not fix this. That is
sequential baton-passing; this is the harder case - several agents working
in parallel, on different providers, over days, where the questions are
*who owns what*, *what was already decided*, and *who has to approve this*.

The agents here may never be running at the same time: a Claude Code session
today, a Codex session tomorrow. They coordinate through files that outlive
both, with an audit trail a human can still read months later.

## The two ideas everything else follows from

**Narrow the shared surface.** Each member owns directories nobody else touches.
Members meet only at a machine-readable contract and at the log. Where two
members must both write, the write is one table row, so a collision is one line.

**The log is evidence, not chat.** It is where a member finds out what was
decided and why, months later, without having been there. That is why the
owner's words are quoted rather than summarised, why timestamps are read from a
clock rather than guessed, and why decisions get copied into the spec the same
session.

---

## Install

Fastest, via the [skills CLI](https://github.com/vercel-labs/skills) - this
repo has `SKILL.md` at its root with no `skills/` subfolder, so the whole
repo installs as one skill:

```bash
npx skills add hieuphanhoang/agents-collaboration-protocol
```

Project-local by default; add `-g` to install to your home directory
instead, or `-a <agent>` to target a specific harness (`-a claude-code`
installs to `.claude/skills/`, others to `.agents/skills/`). Verified this
actually works end to end before writing it down. See the skills CLI's own
`--help` for the rest.

Or clone it directly and point your agent harness at it yourself:

```bash
git clone https://github.com/hieuphanhoang/agents-collaboration-protocol \
  ~/.agents/skills/agents-collaboration-protocol
```

Either way, the skill is self-contained and stdlib-only. No dependencies,
no build step.

## Quickstart

```bash
# scaffold the protocol into a target repository
uv run --no-project scripts/handoff.py init --root /path/to/repo
```

That writes `.handoff/PROTOCOL.md`, `.handoff/INDEX.md`,
`.handoff/ROSTER.md`, `.handoff/threads/`, the CLI at `.handoff/handoff.py`,
and an `AGENTS.md` pointer section. It is idempotent. `--state-dir <path>`
picks a different name if `.handoff/` doesn't suit a project - pass it on
every later command too, since only `.handoff/` is looked for automatically.

Then fill in `.handoff/ROSTER.md` - who the members are and **which directories
each one owns**. Ownership is the load-bearing part; everything else is
bookkeeping.

Day to day, from inside the target repo:

```bash
python .handoff/handoff.py waiting Opus                  # what is waiting on me
python .handoff/handoff.py summary                       # every live thread, not just mine
python .handoff/handoff.py new "Cache key" --frm Opus --to Codex \
       --type QUESTION --body-file question.md
python .handoff/handoff.py reply AGENT-001 --frm Codex \
       --body-stdin --status answered < answer.md
python .handoff/handoff.py sync                          # rebuild the index
python .handoff/handoff.py doctor                        # check for damage
python .handoff/handoff.py test                          # the regression suite
```

Pass long or quoted comments as `--body-file` or `--body-stdin`, never as
`--body "..."`. Shells disagree about quoting, and a comment mangled on its way
into the log is a lie in the record that nobody can spot later.

---

## What gets installed into a target repo

| File | Purpose |
|---|---|
| `.handoff/PROTOCOL.md` | How the log works. Every member reads it |
| `.handoff/ROSTER.md` | Who exists, who owns which directories |
| `.handoff/INDEX.md` | The index: awaiting-owner, open threads, conversation history, all messages |
| `.handoff/threads/` | One file per topic, `AGENT-###` between members, `ASK-###` to the owner |
| `.handoff/handoff.py` | The CLI, so every member can run it - not just the one whose skill folder holds it |

## Repository layout

| Path | What it is |
|---|---|
| `SKILL.md` | Skill entry point: the workflow and the rules that carry weight |
| `references/protocol.md` | The provider-neutral protocol, copied into repos as `.handoff/PROTOCOL.md` |
| `references/onboarding.md` | Adding or removing a member; the chat-only relay loop |
| `references/git.md` | Committing, branching and merging when several members share a repo |
| `references/task-fit.md` | Per-provider strengths and failure modes; a work-to-member routing table |
| `assets/` | Templates `init` writes |
| `scripts/handoff.py` | The CLI |
| `scripts/test_handoff.py` | The regression suite — the cases that have actually bitten |
| `.handoff/CONTRIBUTING.md` | How to work on this repository: the working agreement, invariants and open work |
| `.handoff/reviews/` | Recorded design critiques, kept as evidence |

## Development

```bash
uv run --no-project scripts/handoff.py test
```

Run it after any change to `scripts/`. [.handoff/CONTRIBUTING.md](.handoff/CONTRIBUTING.md) has the
full working agreement; two rules matter most:

- **A new test must fail against the old code.** Copy the tree, revert the fix
  in the copy, run the suite there. A test that passes either way documents
  nothing.
- **ASCII punctuation in anything `init` writes into a target repo** - that is
  `references/protocol.md`, `assets/*`, and any string the CLI emits. Providers
  transliterate em-dashes and arrows differently, and real changes disappear
  into that churn.

## Status

Working and tested; used across Claude Code, Codex and opencode. Licensed
under [MIT](LICENSE).
