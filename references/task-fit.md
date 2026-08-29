# Assigning work to the right member

Read this when building the roster, and again when the work changes shape and
the split stops fitting. The profiles below reflect public reporting as of
**August 2026**. Model generations turn over every few months and the rankings
move with them, so treat this as a starting point rather than a settled fact:
check current numbers before a large re-allocation, and prefer what you have
observed in this repo over anything written here.

---

## 1 - The protocol allocates territory, not tasks

`.handoff/ROSTER.md` gives each member directories, not job descriptions. A
strength only becomes an assignment when it maps onto a place in the tree.
"Codex is good at tests" is not an assignment; "Codex owns `tests/` and `ci/`"
is.

Two things follow:

- **A strength with no directory is advice, not ownership.** If a member is good
  at review but owns nothing, say so explicitly in the roster - `advisory - no
  directories` - and route work to them through threads. Do not leave it vague
  and hope.
- **A member's failure mode matters as much as its strength**, because the
  boundary rule is what contains it. An agent that tends to edit adjacent files
  it was not asked to touch is exactly what section 2 of `.handoff/PROTOCOL.md`
  exists for. Give that member a territory with few cross-cutting dependencies
  and its failure mode becomes a rejected diff instead of a silent regression.

---

## 2 - Profiles

### Claude Code (Opus)

*Last reviewed 2026-08-27 - in use.*

- **Strong at:** deep reasoning over a large codebase, long multi-step sessions
  that hold their thread, cross-cutting refactors, designing the shared
  contract, frontend and UI work. Reporting through 2026 consistently puts it at
  or near the top for code quality in head-to-head trials and for holding a
  whole-repo picture at once.
- **Weak at / watch for:** usage limits are the number one complaint, and they
  bite hardest exactly when a session is going well. It runs on one provider's
  models, so there is no routing away from a bad day.
- **Therefore:** spend it where reasoning depth is the scarce input - the
  contract, the architecture, the refactor that touches everything, the review
  that has to be right. Do not put it on the high-volume mechanical path; that
  is how the limit arrives mid-refactor.

### Codex CLI (GPT)

*Last reviewed 2026-08-27 - in use.*

- **Strong at:** terminal and shell work, infrastructure, CI, test generation,
  one-shot review of a finished diff. Cloud sandbox execution means it can be
  handed something risky without it touching the working tree, and several runs
  can go in parallel.
- **Weak at / watch for:** focus discipline. The recurring report is sprawling
  diffs - files edited beyond the intended scope - plus weaker frontend output
  and more erratic behaviour in very long sessions.
- **Therefore:** ideal for a bounded, well-specified territory with clear edges:
  `ci/`, `scripts/`, `tests/`, infrastructure. Keep its sessions short and its
  boundary explicit. This is the member for which a strict ownership line and
  `handoff.py doctor` earn their keep.

### opencode + Qwen3.8

*Last reviewed 2026-08-27 - in use.*

- **Strong at:** agentic terminal work close to frontier level (Terminal-Bench
  2.1 in the high 80s, within a few points of the best proprietary agents), and
  notably reliable tool calling - testers report multi-hour sessions with no
  failed tool calls. Open weights, so cost per iteration is low or zero and the
  work can run offline. opencode routes across many providers, so this member
  can change models without changing seats.
- **Weak at / watch for:** the hardest reasoning sits a tier below the frontier
  (SWE-Bench Pro around 67-68, against roughly 69 for Opus 4.8 and 80 for Fable
  5), and generated code carries small logic slips - a toggle that resets
  instead of pausing, an unreliable control - that pass a smoke test and fail a
  real one. Small local variants are a different animal: an 8B at a 32k context
  cannot hold a multi-file task, whatever the family name suggests.
- **Therefore:** the volume member. Mechanical implementation inside a module
  whose interface is already settled, test fixtures, data and format plumbing,
  scripted migrations, anything you would run many times. Pair it with tests
  that would actually catch a small logic slip, and have another member review
  the diff rather than trusting the smoke test.

### Grok (planned)

*Last reviewed 2026-08-27 - not yet on the team.*

- **Strong at:** speed and price. Good for bulk reading, boilerplate, quick
  debugging hypotheses, and high-volume iteration where being roughly right
  immediately beats being exactly right in a minute.
- **Weak at / watch for:** large multi-file codebases, missed edge cases and
  error handling, and specific blind spots in frontend styling. Fewer harness
  integrations than the others.
- **Therefore:** a second opinion and a cheap first pass, not the owner of
  anything load-bearing. If it joins as a browser tab it is a `relay only`
  member - see `onboarding.md` section 3.

### Cursor (planned)

*Last reviewed 2026-08-27 - not yet on the team.*

- **Strong at:** the human in the loop. Inline edits, visual diffs, per-request
  routing across providers, and parallel agents on git worktrees. The fastest
  tool here for moment-to-moment editing.
- **Weak at / watch for:** it is not really a peer member. It is the owner's
  hands.
- **Therefore:** list it in `.handoff/ROSTER.md` as how the owner edits, not as a
  member with its own territory. This matters to the protocol: section 6 of
  `.handoff/PROTOCOL.md` says never assume the log contains only your own
  writing, and Cursor is the most likely reason that is true. Re-read before
  writing, and expect `handoff.py reply` to refuse when a file changed
  underneath you.

---

## 3 - The routing table

| Work | Member | Why it lands there |
|---|---|---|
| Architecture, the shared contract, cross-cutting refactor | Claude Code | Reasoning depth and whole-repo context are the scarce inputs |
| Frontend and UI | Claude Code | The others are all measurably weaker here |
| CI, infra, shell, ops scripts | Codex CLI | Best terminal work, sandboxed so a bad run costs nothing |
| Test suites and fixtures | Codex CLI or opencode | Both are strong and cheap; keep it away from whoever wrote the code |
| Bulk implementation behind a settled interface | opencode + Qwen3.8 | Reliable tool calls, low cost per iteration, runs offline |
| Scripted migrations, data plumbing, repetitive edits | opencode + Qwen3.8 | Volume work should never sit on the rate-limited member |
| Review of a finished diff | Any member except its author | See below |
| Cheap second opinion, boilerplate, first-pass reading | Grok (relay) | Fast and cheap; do not give it multi-file coherence to hold |
| Hand editing, visual diffs, worktree parallelism | Owner via Cursor | This is the owner acting, not a member working |

---

## 4 - Three rules that outlive the profiles

**The reviewer is not the author.** Whoever wrote a change is the worst
available judge of it - they re-run the same reasoning and reach the same
conclusion. Cross-review is the cheapest quality mechanism this protocol has,
and it is nearly free: open an `AGENT-` thread and hand the diff to a member who
did not write it.

**Cost and rate limits are a scheduling constraint, not a footnote.** A member
that is rate limited or expensive must not sit on the high-volume path, however
capable it is. Put the cheap member where the loop is tight and the strong
member where a wrong answer is expensive, and the team keeps working when one
provider throttles.

**Assign against the failure mode, not just the strength.** Every profile above
has a characteristic way of being wrong. The split is good when each member's
usual failure lands inside its own territory, where its own tests catch it, and
bad when one member's sprawl routinely lands in another's directory. If you are
repeatedly cleaning up after the same seam, the boundary is in the wrong place,
not the member. Raise it as an `AGENT-` thread; `onboarding.md` section 5 lists
the other signs.

---

## 5 - Keeping this honest

Each profile carries a **last reviewed** date. When you revise one, move the
date and say what changed it - a release, or something you watched happen in
this repo.

**Where a profile and the roster disagree, the roster wins.** These profiles are
assembled from public reporting; `.handoff/ROSTER.md`'s "usual failure to watch
for" column is assembled from what this team has actually seen. Observed beats
reported, every time - the same rule the log applies to the owner's words.

---

## 6 - When to revisit

- A member you rely on ships a new generation, or the one you rejected does.
- The work changes shape - a backend project grows a UI, and the member best at
  UI owns nothing there.
- One member's threads are all "can you change X for me". They do not own enough
  to work independently.
- You are routinely reviewing and fixing the same member's output in the same
  way. Either move that work, or write the missing test that would have caught
  it.
