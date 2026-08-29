# agent-handoff

A file-based collaboration protocol that lets several AI agents from different
providers work the same repository without overwriting each other or re-deciding
settled questions.

It ships as a skill (`SKILL.md` plus `references/`, `assets/`, `scripts/`) and
installs into a target repo as four plain-markdown artefacts and a CLI.

---

## The problem

Multiple agents on one repo fail in a specific way: they cannot see each other.
No shared conversation, no shared memory, no way to ask a quick question. Left
alone they overwrite each other's files, re-decide settled questions, and hand
the human the same problem three times in three different words.

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

Clone, then point your agent harness at it. For Claude Code:

```bash
git clone <this repo> ~/.agents/skills/agent-handoff
```

The skill is self-contained and stdlib-only. No dependencies, no build step.

## Quickstart

```bash
# scaffold the protocol into a target repository
uv run --no-project scripts/handoff.py init --root /path/to/repo
```

That writes `.agents/PROTOCOL.md`, `.agents/CHATLOG.md`,
`.agents/ROSTER.md`, `.agents/chat_logs/`, the CLI at `.agents/handoff.py`,
and an `AGENTS.md` pointer section. It is idempotent.

Then fill in `.agents/ROSTER.md` - who the members are and **which directories
each one owns**. Ownership is the load-bearing part; everything else is
bookkeeping.

Day to day, from inside the target repo:

```bash
python .agents/handoff.py waiting Opus                  # what is waiting on me
python .agents/handoff.py summary                       # every live thread, not just mine
python .agents/handoff.py new "Cache key" --frm Opus --to Codex \
       --type QUESTION --body-file question.md
python .agents/handoff.py reply AGENT-001 --frm Codex \
       --body-stdin --status answered < answer.md
python .agents/handoff.py sync                          # rebuild the index
python .agents/handoff.py doctor                        # check for damage
python .agents/handoff.py test                          # the regression suite
```

Pass long or quoted comments as `--body-file` or `--body-stdin`, never as
`--body "..."`. Shells disagree about quoting, and a comment mangled on its way
into the log is a lie in the record that nobody can spot later.

---

## What gets installed into a target repo

| File | Purpose |
|---|---|
| `.agents/PROTOCOL.md` | How the log works. Every member reads it |
| `.agents/ROSTER.md` | Who exists, who owns which directories |
| `.agents/CHATLOG.md` | The index: awaiting-owner, open threads, conversation history, all messages |
| `.agents/chat_logs/` | One file per topic, `AGENT-###` between members, `ASK-###` to the owner |
| `.agents/handoff.py` | The CLI, so every member can run it - not just the one whose skill folder holds it |

## Repository layout

| Path | What it is |
|---|---|
| `SKILL.md` | Skill entry point: the workflow and the rules that carry weight |
| `references/protocol.md` | The provider-neutral protocol, copied into repos as `.agents/PROTOCOL.md` |
| `references/onboarding.md` | Adding or removing a member; the chat-only relay loop |
| `references/git.md` | Committing, branching and merging when several members share a repo |
| `references/task-fit.md` | Per-provider strengths and failure modes; a work-to-member routing table |
| `assets/` | Templates `init` writes |
| `scripts/handoff.py` | The CLI |
| `scripts/test_handoff.py` | The regression suite — the cases that have actually bitten |
| `.agents/CONTRIBUTING.md` | How to work on this repository: the working agreement, invariants and open work |
| `.agents/reviews/` | Recorded design critiques, kept as evidence |

## Development

```bash
uv run --no-project scripts/handoff.py test
```

Run it after any change to `scripts/`. [.agents/CONTRIBUTING.md](.agents/CONTRIBUTING.md) has the
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
