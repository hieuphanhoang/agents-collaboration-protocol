# Onboarding a member

Read this when the roster changes: a new agent joins, one leaves, or a member
switches provider.

---

## 1 - Decide what they own

A member without owned directories has nothing to do and will drift into
everyone else's work. Before anything else, settle with the owner:

- **Which directories become theirs?** Carve them out of the shared area or from
  a member who has too much, and say so in that member's thread so they are not
  surprised.
- **What do they meet the others at?** Usually the existing contract. If the new
  member needs a field nobody exposes, that is a contract change and needs
  review from everyone affected - not a quiet addition.
- **Does the split still make sense?** Three members carving one codebase into
  thirds is often worse than two members with a clean seam. If the honest answer
  is that there is no natural third territory, say so to the owner rather than
  inventing one. Adding a member has a cost, and it is paid in coordination.
- **Does the territory suit them?** Providers differ in what they are reliably
  good at and in how they characteristically fail, and a boundary drawn across a
  member's weak spot produces work the others have to redo. `task-fit.md` has
  the current profiles and a routing table. Read it before you carve, not after
  the first collision.

Record it in `.handoff/ROSTER.md`, then open an `AGENT-` thread introducing them
so the existing members learn the new boundary from the log rather than from a
collision.

---

## 2 - Brief them

What a new member needs, in this order:

1. `.handoff/ROSTER.md` - who exists, who owns what
2. `.handoff/PROTOCOL.md` - how the log works
3. The specification or contract - what is being built
4. Open threads - what is live right now

Members with repo access read those directly. Point their instruction file at
`.handoff/PROTOCOL.md` - agents follow the file their harness loads, and a
protocol nobody is told to read is ignored.

| Provider | Instruction file it reads |
|---|---|
| Codex / ChatGPT CLI | `AGENTS.md` |
| opencode | `AGENTS.md` |
| Claude Code | `CLAUDE.md` normally - its own convention, and what it looks for first - and `AGENTS.md` as well |
| Cursor | `.cursor/rules/` (`.cursorrules` is the older form) |
| Grok, browser models | no instruction file - see section 3 |
| Others | check the docs; most read a root markdown file |

**Register, do not colonise.** `init` appends a short pointer to whichever of
`AGENTS.md` and `CLAUDE.md` the project already has - both, when both exist -
and creates neither when the project has neither. A repository without an
instruction file may have decided that on purpose, and adding one uninvited is
the same overreach as editing a directory you do not own.

That is why registering with two files is not the duplication this document
warns about elsewhere. What lands in them is a **pointer**: read
`<state>/PROTOCOL.md`, the log lives here, handoff mode is active. The content
lives in one place, under the state directory, and both entry points name it.
Two pointers to one file cannot disagree; two copies of the rules can.

**Then leave them alone.** Registration happens once. Everything the protocol
produces afterwards - roster, protocol, log, threads - belongs under the state
directory, never in the project's instruction files. Those are entry points, not
workspace. If a harness turns out to read something else again (Cursor's
`.cursor/rules/`), add a one-line pointer there too; never a second copy of the
content. Real content in two files is how members end up following different
rules and blaming each other for it.

A short section is enough - who they are, what they own, and "read
`PROTOCOL.md` in the state directory before writing to the log." The state
directory is `.handoff/` unless the project chose something else with
`--state-dir`; the registration `init` wrote names which one, so a new
member never has to guess.

---

## 3 - Members with no file access

Some useful models are only a browser tab - Grok and the chat-only frontends are
the common case. They can still contribute real work; they simply cannot read
the repo.

**Check the harness, not the model, before deciding this.** File access is a
property of what the model is running inside. Qwen in a browser is a relay
member; the same Qwen running under opencode is a full member that reads, writes
and owns directories. Getting this wrong in either direction is expensive: you
either build a relay loop nobody needed, or you hand directories to a member
that cannot see them.

```bash
uv run --no-project <skill>/scripts/handoff.py brief Grok --out briefing.txt
```

That bundles roster, protocol, every open thread, and a reply format that
deliberately carries no timestamp - the briefing tells them not to write one,
because they cannot read this project's clock. Whoever transcribes the answer
stamps it when it actually lands.

### The relay loop

1. **Generate** the briefing.
2. **Owner pastes** it into that model's chat.
3. **Model replies** in the comment format.
4. **Owner pastes the reply back** to a member with file access.
5. **That member transcribes it verbatim**, attributed to the speaker:
   `handoff.py reply AGENT-004 --frm Grok --body "..."`

### What matters in step 5

**Transcribe, do not summarise.** The same rule as for the owner's words, and
for the same reason: nobody else can see the original. If Grok's answer is
three paragraphs of reasoning and you record "Grok agrees", you have deleted the
part that was worth having.

**Attribute to them, not to yourself.** The comment is `[Grok, ...]`, not
`[Opus, ...]` describing Grok. If you want to add your own reaction, that is a
second comment below.

**Stamp on arrival, and never let them stamp themselves.** A relay member cannot
read the project's clock, and hours can pass between generating a briefing and
pasting the answer back. A guessed time is worse than none: the log's whole value
rests on times being real, and one invented stamp makes every stamp suspect. The
briefing tells them not to write times; you stamp when the reply actually lands.

**Say when the relay is lossy.** A chat-only member cannot see the codebase, so
its answer may rest on assumptions the files would have corrected. Note that in
your own comment when it matters — "Grok has not seen the adapter; the
constraint it assumes here does not hold." That is your job as the one with
eyes on the repo.

**Ask them to flag their own blind spots.** The briefing requests that they mark
which parts of an answer depend on code they have not seen. That turns an
unverifiable opinion into a checkable list, and it is cheap for them to produce.

**Keep the briefing small.** Do not paste closed threads. A model given sixty
pages of settled history answers the wrong question. Past the first
briefing, add `--compact` to drop the ROSTER.md/PROTOCOL.md dump - a relay
member who has already seen it once does not need it repeated in every
paste, only the open threads and the reply format.

---

## 4 - Removing a member

Do not delete their threads. They are the record of why things are the way they
are, and deleting them turns settled decisions back into mysteries.

Instead:

- Mark their open threads `superseded` or `closed`, with a comment saying where
  the work went.
- Reassign their directories in `.handoff/ROSTER.md`.
- Note the handover in an `AGENT-` thread so the remaining members know what
  they have inherited and what state it is in.

---

## 5 - When the roster is wrong

Signs the split needs revisiting, worth raising rather than working around:

- Two members keep needing changes in the same files → the boundary is in the
  wrong place.
- One member's threads are all "can you add X for me" → they do not own enough
  to work independently.
- A member has not posted in weeks → either they have nothing to do, or work is
  happening off-log. Both are worth surfacing.
- Every decision becomes an owner escalation → the members are not actually
  empowered, or the split put judgement calls on the wrong side of the line.

Raise it as an `AGENT-` thread with the other members first. If the fix needs
the owner's intent — scope, budget, who they want involved — take them one
recommendation, not the diagnosis.
