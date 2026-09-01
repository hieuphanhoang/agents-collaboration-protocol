---
name: agents-collaboration-protocol
description: Multi-agent collaboration and coordination for AI coding agents that do not share a session, memory, or runtime. Set up and run a file-based protocol so several agents from different providers (Claude Code, ChatGPT/Codex, opencode, Qwen, Cursor, Grok, and chat-only models) can work the same repository together without overwriting each other or duplicating work. Use this whenever the user mentions working with another AI model on a project, agent teamwork or collaboration, handing work off between agents, adding a member to a project, splitting a codebase between agents, a shared log between agents, or asks how two AIs should coordinate — even if they never say "protocol" or "handoff". Also use it when deciding which agent should own or do what, when deciding whether one agent may call another agent directly or the user starts each one, and when a repo already has .handoff/INDEX.md and .handoff/threads/ and a thread needs writing, answering, or the index resyncing, and when onboarding a new agent to an existing multi-agent project.
---

# Agents Collaboration Protocol

Multiple agents on one repo fail in a specific way: they cannot see each other.
No shared conversation, no shared memory, no way to ask a quick question. Left
alone they overwrite each other's files, re-decide settled questions, and hand
the human the same problem three times in three different words.

This skill installs a protocol that fixes that with plain files in the repo.
Any agent that can read markdown can take part, whatever provider it runs on.

## The two ideas everything else follows from

**1. Narrow the shared surface.** Each member owns directories nobody else
touches. Members meet only at a machine-readable contract (an OpenAPI spec, a
schema, a typed interface) and at the log. Where two members must both write,
the write is one table row, not a paragraph — so a collision is trivially
merged.

**2. The log is evidence, not chat.** It is where a member goes to find out
what was decided and why, months later, without having been there. That is why
the owner's words are quoted rather than summarised, why timestamps are read
from a clock rather than guessed, and why decisions get copied into the spec the
same session.

## Workflow

**Arriving at a repo that already has a state directory?** Read `ROSTER.md`
before anything else, and look at its `Invocation mode:` line. It tells you
whether you may start another member yourself or only write to the log. If the
line is missing or still a placeholder, ask the owner the question in step 3
below and record their answer — until then the mode is `independent` and you
call nobody.

### Setting up a new project

1. Read `references/protocol.md` — the protocol you are installing.
2. Run `uv run --no-project <skill>/scripts/handoff.py init --root <repo>`.
   It writes `PROTOCOL.md`, `INDEX.md`, `ROSTER.md`, `CONTRIBUTING.md`,
   `threads/` and the CLI into the project's **state directory**, and
   registers the protocol in whatever instruction file the project already has.
   It is idempotent: existing files are left alone.
   (`--no-project` because the script is stdlib-only and the target repo may
   have a `pyproject.toml` of its own that `uv` would otherwise try to sync.)

   **Where the state goes.** `.handoff/`, always — vendor-neutral, no
   collision with any tool's own config directory, no special-casing for
   any other name. `--state-dir <path>` picks something else if a project
   needs it; pass it explicitly on every later command too, since only
   `.handoff/` is ever looked for automatically.

   **What registration is.** A short pointer appended to `AGENTS.md` and
   `CLAUDE.md` — both, if both exist — saying handoff mode is active and where
   the state directory is. **If the project has neither, `init` creates
   neither.** A repository with no instruction file may have chosen that, and
   adding one uninvited is the same overreach as editing a directory you do not
   own. `--no-instructions` skips registration entirely.
3. **Ask the owner how members get started.** This is the one question the
   protocol cannot answer from the machine, and it has to be asked before
   anybody acts, because one agent starting another is an action on the owner's
   machine (`references/protocol.md` section 14). Put it to them plainly:

   > Should the agents call each other directly, or will you start each one
   > yourself?
   >
   > - **independent** — you open each agent; they coordinate only through the
   >   log. Safe default, and right for most projects.
   > - **orchestrated** — an agent with a terminal may run another agent's CLI
   >   itself, so they work in parallel without you relaying.
   > - **mixed** — some are callable, the rest you start.

   Record the answer on the `Invocation mode:` line in `ROSTER.md` now; the
   per-member commands go in alongside the members themselves, in the next step.
   **Never infer this from what is installed** — that a CLI exists on the machine
   says nothing about whether the owner wants it spent. Unanswered reads as
   `independent`.

4. Fill in `ROSTER.md` in the state directory, with the human interviewing the
   user: who the members are, which model each runs on, whether each has
   filesystem access, who starts each one's turn (the `Invoked by` column — a
   literal command for a callable member, `owner` otherwise), and **which
   directories each one owns**. Ownership is the load-bearing part — vague
   ownership is how two agents end up editing the same file. Read
   `references/task-fit.md` before drawing the boundaries: providers differ in
   what they are reliably good at and in how they characteristically fail, and
   the split should put each member's usual failure inside its own territory.
5. **Register once, then leave those files alone.** `AGENTS.md` and `CLAUDE.md`
   are entry points that route a harness into the state directory; they are not
   workspace. Everything the protocol produces afterwards — roster, log,
   threads, working conventions — lives in the state directory. Project-specific
   working conventions go in `CONTRIBUTING.md` there: the checks to run before
   handing work to another member, and the conventions that have bitten you.
   Where a harness reads something else (Cursor's `.cursor/rules/`), put a
   pointer there too, never a second copy. Agents follow the file their harness
   loads; a protocol nobody is told to read gets ignored.

### Day-to-day

| Task | Command |
|---|---|
| See what is waiting on you | `handoff.py waiting Sol` |
| See every live thread, not just yours | `handoff.py summary` |
| Open a thread to another member | `handoff.py new "title" --frm Opus --to Sol --type QUESTION --body "..."` |
| Escalate to the owner | same, plus `--ask` |
| Reply in a thread | `handoff.py reply AGENT-004 --frm Sol --body-file reply.md --status answered` |
| Close a thread once the decision is in the code | `handoff.py close AGENT-004 --frm Sol --promoted-to path/to/changed/file.py` |
| Brief a relay member with no file access | `handoff.py brief Grok --out briefing.txt` (add `--compact` past their first briefing) |
| Rebuild the index | `handoff.py sync` |
| Check for damage | `handoff.py doctor` |
| Verify the tool itself after editing it | `handoff.py test` |

**Pass long or quoted comments as `--body-file <path>` or `--body-stdin`, not
`--body "..."`.** Shells disagree about quoting; a comment containing a quoted
command or a newline is the most common way a write to this log goes wrong, and
a mangled comment is a lie in the record that nobody can spot later.

`init` installs the CLI into the state directory, so members without this skill
folder — Codex, opencode — can run it too. Without that, `PROTOCOL.md` tells
every member to stamp with a tool only one of them has, and the rest are pushed
into the hand-editing the same document forbids.

The script reads the system clock for every stamp, so timestamps cannot drift
into invention, and it regenerates the index tables from the thread files, so
the index cannot drift out of sync with reality. Prefer it over hand-editing
`INDEX.md` — hand-maintaining sorted tables is exactly the tedious
work that gets skipped under pressure, and a stale index is worse than none
because it is believed.

Write the **Conversation history** prose by hand; only a participant knows what
a turn actually meant. Keep one row per speaker's turn, newest at the top, and
extend your own last row rather than adding another until someone else posts.

### Deciding who does what

The roster hands out directories, so a member's strengths only become an
assignment when they map onto a place in the tree. `references/task-fit.md`
carries current per-provider profiles — what each is reliably good at, and how
each characteristically goes wrong — plus a routing table.

Three things there are worth knowing even if you never open it:

- **Assign against the failure mode, not just the strength.** A good split puts
  each member's usual mistake inside its own territory, where its own tests
  catch it. A bad one lets one member's sprawl land in another's directory.
- **The reviewer is not the author.** Whoever wrote a change re-runs the same
  reasoning and reaches the same conclusion. Hand the diff to a member who did
  not write it; it costs one thread.
- **Rate limits are a scheduling constraint.** Keep the expensive or throttled
  member off the high-volume path, or the limit arrives mid-refactor.

### Calling another member

Only in `orchestrated` or `mixed` mode, and only a member whose `Invoked by`
cell names a command. The loop:

1. **Open the thread first.** The called member needs something to read and
   somewhere to answer. A call with no thread produces work with no record of
   what was asked.
2. **Call it with the command from the roster**, not one you composed. The task
   you give it points at this skill, the roster and the thread and tells it to
   read them — it is not a substitute for them. Name the directories it owns,
   and say plainly that it may disagree and write no code if it does.
3. **It writes its own log entries.** A called member is in handoff mode like
   any other: it posts its own comment, in its own words, and adds its own
   Conversation history row. Do not ask it for a draft you will paste. Only if a
   write genuinely fails do you relay — verbatim, attributed to it, stamped when
   it lands — and check that claim rather than inheriting it, because sandbox
   accounts are often created per run.
4. **Say in the thread that you made the call.** One line. Otherwise nobody can
   tell later whether that member was working in parallel or happened to wake up.
5. **Read the result in the log, not in its output.** Your job is to turn the
   request into a prompt, assign the task, wait, and then read the thread. The
   called member's transcript is not the deliverable and mining it is how its
   words stop reaching the log — you end up the only one who can see the work,
   which is the condition this protocol exists to remove. The one reason to look
   at its output is to find out why its log write failed.

**Being called changes who starts the turn and nothing else.** A member you
started loads this skill itself, owns its directories, decides technical
questions jointly with you, and may tell you that you are wrong. Starting a
process does not make you its reviewer: if you called a member to implement
something, someone who did not author it still has to review it.

**And you may not tell it to skip the discussion.** You write its task, so you
can waive steps that are not yours to waive — the first one to go is always the
design exchange the thread was opened for. Parallelism is for the work, not for
the agreement.

### Bringing in a member with no file access

Many useful models are a browser tab. Do not exclude them, and do not pretend
they are absent. But check the **harness, not the model**: Qwen in a browser is
a relay member, while the same Qwen under opencode reads and writes the repo
like any other member.

```
uv run --no-project <skill>/scripts/handoff.py brief Grok --out briefing.txt
```

This emits roster, protocol, every open thread, and a reply format. The user
pastes it into that model's chat; the reply comes back in comment format and
whichever member has file access transcribes it **verbatim**, attributed to the
speaker. See `references/onboarding.md` for the full loop.

## Rules worth understanding rather than obeying

Read `references/protocol.md` for the complete set. These are the ones that
carry the most weight, with the reasoning that makes them stick:

**Never edit a directory you do not own.** If you need something from another
member's area, propose a contract change or open a thread. Reaching across is
tempting and always cheaper in the moment; it is also how you silently break
work you cannot see.

**Escalate only after the members agree, and only with a recommendation.** The
prefix encodes this: `AGENT-` threads are between members, `ASK-` threads go to
the owner. `ASK-` covers two things — **a decision only the owner can make**
(licensing, scope, naming, money) and **approval to act on their machine**
(installs, large downloads, system config). The second matters because deciding
and acting are separate: the members can settle *what* to install on purely
technical grounds and still not be entitled to run it. Either way, creating an
`ASK-` file is a claim that the members already did their part.

**Quote the owner, do not summarise them.** Members do not share the owner's
conversation. Whatever you transcribe is the only version of the owner's intent
the others will ever have, and a summary carries your interpretation baked in
with no way for anyone to detect it. Their words are evidence; your paraphrase
is testimony. Put the quote first and your reading of it directly below, so the
seam is visible.

**Never assume you are the only author.** The owner edits these files. So do
other members. Re-read before editing and preserve changes you did not make —
that is about not clobbering someone mid-write, which is a different hazard from
the one below.

**Every member can write the log, and no member rewrites another's.** Full
write access to `INDEX.md` and `threads/` is what membership means for a
direct-access member; one that cannot append is broken, and fixing that comes
before the work. Write means **append** — your own comments, your own rows.
Never remove, edit, reword or reorder another member's comment. A wrong comment
is answered, not deleted, and the record then carries both what was believed and
what corrected it. Your own earlier comments are not drafts either: append a
correction below one, rather than editing it. `references/protocol.md` section
13 has the whole rule, including what the CLI is allowed to rewrite.

**Promote decisions out of the log the same session.** A decision that exists
only in a thread does not exist. Copy it into the spec, the contract, or the
code. Otherwise the log quietly becomes the real specification — a file nobody
can read in full, where the actual answer is buried at entry 173.

**Keep the log about the project.** Conventions about how to keep the log belong
in the agents' instruction files, not in a thread. Otherwise members spend their
shared channel discussing the channel.

**Review before merge; owner before push.** A commit is local and reversible, so
any member may commit its own paths. A merge to `main` is still local, but it is
canonical: it changes what will publish when the owner pushes. The
reviewer-of-record must be a member who did not author the change, and their
approval or findings belong in an `AGENT-` thread. Pushing, opening a PR,
creating a repo and flipping one public all need the owner's go-ahead at the
moment of acting. `references/git.md` covers the rest, including the one that
bites most: never `git commit -a`, because it sweeps up whatever another member
is half-way through writing.

**Use ASCII punctuation in shared files.** Providers differ in what they emit
reliably; em-dashes and arrows get silently transliterated, and then the other
member converts them back. Real changes disappear into that churn.

## When a member disagrees

Say so plainly, in the thread, with the evidence. Two agents that agree
instantly are usually not both thinking. The protocol's value is that a
disagreement becomes visible and resolvable rather than resolving itself into
whoever wrote last. If evidence can settle it, get the evidence. If it cannot,
it is probably an owner question.

## Bundled files

- `references/protocol.md` — the provider-neutral protocol. Copied into the repo
  as `PROTOCOL.md` in the state directory; every member reads it. Read it
  before setting up a project.
- `references/onboarding.md` — adding a member mid-project, which instruction
  file each provider reads, and the full chat-only relay loop. Read when the
  roster changes.
- `references/task-fit.md` — what each provider is reliably good at, how each
  characteristically fails, and a routing table from work to member. Read before
  drawing ownership boundaries. Profiles are dated; re-check them when a member
  changes model generation.
- `references/git.md` — committing, branching, reviewing and merging when
  several members share a repository: why `git commit -a` breaks the boundary
  rule, how the log merges, how to name the reviewer-of-record, and why members
  commit but the owner pushes. Read before more than one member commits.
- `scripts/handoff.py` — the CLI above. `--help` on any subcommand.
- `scripts/test_handoff.py` — the regression suite, covering legacy Unicode
  headers, year-boundary sorting, an edit landing mid-write, who the index says
  owes a reply, impossible timestamps, a status field emptied by hand,
  shell-hostile comment bodies, what `init` installs and what it refuses to do
  from the copy installed in a repo, relay stamping, ignored handoff state,
  custom `--state-dir` names and their rejection cases, roster-participant
  drift, stale Conversation history, `close`'s promotion checks, and index
  completeness. Run it after
  changing the script; these are the cases that have actually bitten.
- `assets/` — templates the script writes, including the `CONTRIBUTING.md`
  every project gets for its own working conventions. Edit these to change what
  `init` produces.
