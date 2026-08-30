# Collaboration protocol

This file is copied into a repository as `.handoff/PROTOCOL.md` and is read by
every member of the project, whatever provider they run on. It is deliberately
plain markdown with ASCII punctuation so that any agent can read and reproduce
it.

Members are listed in `.handoff/ROSTER.md`. The conversation lives in
`.handoff/INDEX.md` (the index) and `.handoff/threads/` (one file per topic).

---

## 1 - Roles

| Role | Who | Authority |
|---|---|---|
| **Owner** | The human | Final say on anything evidence cannot settle: licensing, scope, naming, cost, risk. Also permits actions on their machine. |
| **Member** | Each agent | Owns named directories. Decides technical questions jointly with the other members. |

An owner is not a tie-breaker for technical arguments. If two members disagree
about which approach is faster, that is a benchmark, not an escalation.

---

## 2 - Ownership

`.handoff/ROSTER.md` assigns every directory to exactly one member, plus a small
set of jointly-owned interface files.

**Never edit a directory you do not own.** If you need something from another
member's area:

- propose a change to the shared contract, or
- open a thread asking for it.

Do not reach across the boundary, and do not guess at another member's
implementation. This is the rule that makes parallel work possible: each member
has a complete, authoritative description of the others that never requires
reading their code.

Where members must meet - an API spec, a schema, a shared type definition -
that file is jointly owned and **changes need every affected member's review.**
Generate code from it on both sides rather than hand-writing matching types, so
that drift becomes a build error instead of a runtime surprise.

---

## 3 - Threads

One file per topic: `.handoff/threads/<ID>-<slug>.md`. IDs are monotonic and
never reused.

| Prefix | Between | Meaning |
|---|---|---|
| `AGENT-###` | member <-> member | Technical. The members settle it. The owner never needs to read these. |
| `ASK-###` | members -> owner | **An owner decision, or approval to act** - in both cases only after the members have agreed a recommendation. |

`ASK-` covers two different things that both need the owner and nothing else:

- **A decision only the owner can make** - licensing, scope, naming, cost, risk.
  Evidence cannot settle it; it needs their intent.
- **Approval to act on their machine** - installing software, downloading large
  files, changing system configuration. The members may have decided *what* to
  install on purely technical grounds and still not be entitled to run it. See
  section 9: decision authority and action approval are different things, and an
  `ASK-` is how the second one is requested.

> **An `ASK-` thread may not be opened until the members have discussed the
> matter and agreed what to recommend.** If only one member has looked at it, it
> is still an `AGENT-` thread. Creating an `ASK-` file is an explicit claim that
> the members already did their part - either they decided and now need
> permission to act, or they agreed what to recommend and now need a ruling. The
> owner is asked *after* we do our work, never instead of it, and never with a
> bare question.

**The test for "is this technical?"** If the members disagreed, could evidence
settle it - a benchmark, a spec, a build log, a measured number? Then the
*decision* is theirs. Note this settles who decides, not who may act: a
technically-settled decision that touches the owner's machine still needs an
`ASK-` before anything runs.

### Thread format

```markdown
# `AGENT-004` - Backend environment

| | |
|---|---|
| **From -> To** | Opus -> Sol |
| **Type** | QUESTION |
| **Status** | answered |
| **Latest** | Sol, 25-08 09:12 (2 comments) |
| **Updated** | 2026-08-25 09:12 |
| **Time** | 2026-08-25 07:24 |

---

**[Opus, 2508, 0724]**

Opening comment.

---

**[Sol, 2508, 0912]**

Reply. Earlier comments are never rewritten.
```

`Latest` and `Updated` are maintained by `.handoff/handoff.py`; write them if
you are composing a thread by hand, or run `sync` afterwards and let it fill
them in.

- **Types:** `STATUS` `QUESTION` `REQUEST` `ANSWER` `DECISION` `BLOCKER` `ACK`
- **Status is a short token:** `open` `answered` `blocked` `closed` `withdrawn`
  `superseded`. Reasoning goes in the comment body, not the field, so the index
  stays scannable. `open`, `answered` and `blocked` all count as live and stay
  in the index's open sections; `blocked` says the thread is waiting on
  something outside it, so nobody reads it as an unanswered question.
- **Every comment is attributed and timed:** `[Name, DDMM, HHMM]`.
- **Comments inside a thread stay chronological.** A reply read before the
  question it answers is harder, not easier. Newest-first applies to the index,
  not to a conversation.

### Status lifecycle

```
open  ->  answered  ->  closed
  |           |
  +-> blocked +-> withdrawn / superseded
```

| Status | Means | Who moves it next |
|---|---|---|
| `open` | Asked, not yet answered | The recipient |
| `answered` | A reply is in, the asker has not accepted it yet | The asker |
| `blocked` | Waiting on something outside the thread - a decision, a build, an owner approval | Whoever unblocks it, in a comment saying what changed |
| `closed` | Settled, and the outcome is written into the spec, contract or code | Nobody. It is done |
| `withdrawn` | No longer needed; the question stopped mattering | Nobody |
| `superseded` | Replaced by another thread; say which one | Nobody |

`open`, `answered` and `blocked` are all **live** and stay listed in the index's
open sections. `answered` is not done - it means the ball is back with whoever
asked, and only they can close it. **The asker closes; the answerer does not.**
Closing your own answer is how a thread gets marked settled while the person who
needed it still disagrees.

A thread is closable only once section 7 has happened: if the decision is not
yet in the spec, the contract or the code, it is still `answered`.

---

## 4 - Timestamps

**Read the system clock. Never invent, estimate, or round a time.**

An invented timestamp is not a small inaccuracy: the log's whole value is being
a reliable record of what was known when. A member reading it later uses times
to reconstruct causality - what did this member know when they made that call?
One fabricated stamp makes every stamp untrustworthy.

`.handoff/handoff.py` stamps automatically for this reason. If you write a
comment by hand, read the clock first.

Pass long or quoted comments as `--body-file <path>` or `--body-stdin` rather
than `--body "..."`. Shells disagree about quoting, and a comment mangled on its
way into the log is a lie in the record that nobody can spot afterwards.

---

## 5 - The index: `.handoff/INDEX.md`

The only file every member writes. Keep the shared surface small: add one table
row, so a collision is one line and trivially merged.

Four sections:

- **Awaiting owner** - open `ASK-` threads, each with the recommendation.
  The owner should never read the log to discover what is waiting on them.
- **Open threads** - live `AGENT-` threads, and who owes a reply.
- **Conversation history** - **newest first, one row per speaker's turn.**
  Consecutive updates from the same speaker merge into that one row and stay
  current until someone else posts, so it reads as a conversation rather than a
  file-change log. Written by hand; only a participant knows what a turn meant.
  **Keep each row short - one or two sentences.** It is a pointer to the
  turn, not a copy of it: name what happened and which thread has the
  detail, and stop there. The full account already lives in the thread; a
  row that restates it is now two places that can drift, and a long row
  defeats the point of a scannable index.
- **All messages** - every thread, sorted by most recent activity.

The structural tables are regenerated by `.handoff/handoff.py sync` between
the `<!-- handoff:... -->` markers. Do not hand-maintain them; hand-sorted tables
go stale, and a stale index is worse than no index because it is believed.

---

## 6 - The owner's words

The owner usually does not write in the log. They answer wherever they happen to
be talking to a member - and sometimes they edit the files directly.

**Whichever member receives an answer transcribes it verbatim**, as an
attributed `[Owner, DDMM, HHMM]` comment in the relevant thread, placed
**before** that member's own response.

- Quote exactly, typos included. A tidied quote is a paraphrase wearing
  quotation marks.
- Keep your reasoning out of the quote. Interpretation goes in your own comment
  below it, so the seam between the owner and you is visible.
- Record short answers too. "ok" is a decision.
- If an answer spans topics, quote it in each relevant thread, or in full in the
  consolidated `ASK-` with pointers from the rest.

**Why this matters more than it looks.** Members do not share the owner's
conversation. Whatever you transcribe is the only version of the owner's intent
the others will ever have. A paraphrase carries your interpretation baked in,
with no way for another member to detect or challenge it. The owner's words are
evidence; your summary is testimony.

A worked example of the failure: the owner writes *"this is a personal
project."* The member records *"personal project, so the licence is
acceptable."* The legal inference belongs to the member, not the owner - and
with only that version in the log, nobody else can separate the fact from the
conclusion.

**Never assume the log contains only your own writing.** The owner edits it.
Other members edit it. Re-read before editing, preserve changes you did not
make, and never tidy or overwrite an entry that is not yours.

---

## 7 - Promotion

**Anything agreed in a thread must be written into the specification, the
contract, or the code in the same working session.** A decision that exists only
in the log does not exist.

Without this the log silently becomes the real specification: a file nobody can
read in full, where the actual answer is buried at entry 173 and every new
member starts by reading six months of conversation.

---

## 8 - Scope

**The log is for the project, not for how the log is kept.**

| Content | Where it goes |
|---|---|
| The work: interfaces, architecture, findings, decisions | `.handoff/threads/` |
| How we work in this project: checks to run, conventions, definition of done | `.handoff/CONTRIBUTING.md` |
| How the log itself works: format, naming, ordering, thread rules | `.handoff/PROTOCOL.md` - and changing it is the owner's call |
| Neither, or unclear | Ask the owner. Do not invent a home for it. |

Members who discuss the channel in the channel end up with a log about logging.

**Not the project's instruction file.** `AGENTS.md` and `CLAUDE.md` are
registration: a one-time pointer telling a harness that handoff mode is active
and where the state directory is. Nothing is added to them after that. They
belong to the project and predate us, and a protocol that keeps editing them
is doing the thing it tells members not to do to each other's directories.

---

## 9 - Actions on the owner's machine

**Decision authority and action approval are different things.**

Even when a choice was the members' to make, anything that touches the owner's
machine - installing software, downloading large files, changing system
configuration - needs their go-ahead **at the moment of acting**, not banked as
an open question in their queue.

Ask when you are ready to run it, not weeks earlier. The vehicle is an `ASK-`
thread of type `REQUEST` (section 3), which is why `ASK-` means "decision *or*
approval": the members may have settled the technical question completely and
still not be entitled to run the command.

Two things make an approval request easy to answer:

- **State what will change and roughly what it costs** - disk, time, whether it
  is reversible. An owner approving a 6 GB install should know it is 6 GB.
- **Group them by when they are actually needed.** A staged list the owner can
  approve in parts beats one all-or-nothing request, and it stops work blocking
  on permission for something not needed until next month.

---

## 10 - Interoperability

Providers differ in what they emit reliably. Two conventions prevent silent
churn:

- **ASCII punctuation in shared files** (`.handoff/INDEX.md`, the contract).
  Use `-` not em-dash, `->` not arrow. Otherwise one member transliterates and
  the next converts back, and real changes disappear into the noise.
- **Plain markdown tables and fenced code.** No provider-specific syntax, no
  HTML beyond the sync markers.

Thread files are effectively single-author, so a member may write however they
like inside their own comments.

---

## 11 - Disagreement

Say so plainly, in the thread, with the evidence.

Two members who agree instantly are usually not both thinking. The point of a
written protocol is that a disagreement becomes visible and resolvable rather
than resolving itself into whoever happened to write last. If evidence can
settle it, get the evidence. If it cannot, it is probably an owner question -
but bring the owner a recommendation, not the argument.

---

## 12 - Git

Ownership prevents two members writing the same file. It does nothing about
history, which is a second shared surface with its own collisions. Four rules
carry most of the weight; the skill's `references/git.md` has the reasoning and
the recovery recipes.

**Commit your own paths. Never `git commit -a`.** It stages every modified
tracked file, including whatever another member is half-way through writing in
its own directory - a commit that claims work you did not do, mixed with work
that was not finished. This is the boundary rule arriving through a door the
boundary rule does not cover. For the same reason, never `git checkout .` or
`git restore .` to tidy up: that discards another member's uncommitted work with
no undo and no record.

**One branch by default.** If the split is real the diffs do not overlap, and a
branch per member buys divergence in exchange for nothing. Branch for work that
is long-running and disruptive, or for a member whose writes land in a lump
because a human applies them later. Name the branch for the task, not the
member.

**`INDEX.md` is generated; thread files are append-only.** Never resolve a
`INDEX.md` conflict by hand - take either side whole and re-run `sync`, which
rebuilds it from the threads. Do resolve a thread conflict by keeping *both*
comments, ordered by their stamps: two members spoke, and a merge is not the
place to decide one of them did not. Every comment carries a real clock time, so
that ordering is written on the comments rather than being a judgement call. Run
`sync` then `doctor` after any merge that touched the log.

**Review before merge; owner before push.** A commit is local and reversible, so
any member may commit its own paths. A merge to `main` is still local, but it is
canonical: it changes what will publish when the owner pushes. The
reviewer-of-record must be a member who did not author the change, and their
approval or findings belong in an `AGENT-` thread. The branch may merge only
after that approval is written down.

**Members commit; the owner pushes.** A push is outward-facing and effectively
permanent - once it is on someone else's server it can be cloned, cached,
indexed and forked before anyone notices a mistake, and deleting it does not
reliably unpublish it. So pushing, opening a pull request, creating a
repository, and changing one between private and public all need the owner's
go-ahead **at the moment of acting**, as an `ASK-` thread of type `REQUEST`.
Section 9 is the general form of this; pushing is its clearest case. Say which
remote and which account, say what becomes visible and to whom, and say that
you read the diff for anything that should not leave the machine.
