# Working the same repository under git

Read this before several members commit to one repository. `PROTOCOL.md`
section 2 hands out directories, which stops two members writing the same file.
It says nothing about history, and history is a second shared surface with its
own collisions.

The distinction is worth holding onto: **ownership prevents conflicts in the
working tree; nothing prevents them in the graph.** Two members who never touch
the same file can still hand you a merge conflict, a lost commit, or a branch
nobody can land.

Paths below are written `<state>/`. That is your project's handoff state
directory - `.handoff/` unless the project chose something else with
`--state-dir`. The registration `init` wrote into `AGENTS.md` or `CLAUDE.md`
names which one, and `handoff.py summary` prints it. Substitute it mentally
wherever `<state>` appears.

---

## 1 - One branch, because ownership already did the hard part

Default to **all members committing to one working branch.** If the ownership
split is real their diffs do not overlap, and a branch per member buys
divergence and a merge you have to think about in exchange for nothing.

Reach for a branch per member only when one of these is true:

- A member is doing something long-running and disruptive - a refactor that will
  break the build for an hour - and the others need a stable tree meanwhile.
- A member is a **deferred writer**: it runs sandboxed and returns diffs a human
  applies later, so its work arrives in a lump and out of order with everyone
  else's.
- The owner wants one member's work reviewable as a unit before it lands.

When you do branch, name it for the work and not for the member -
`digest-guard`, not `codex-branch`. A branch named after a member becomes a
permanent parallel universe; a branch named after a task ends when the task
does.

**Worktrees** are for one member that needs two branches checked out at once.
They do not help members share a branch, because two worktrees cannot check out
the same branch - so they solve a problem most teams here do not have. If you
use them anyway, note that each worktree has its own working copy of `<state>/`:
the log can disagree with itself across worktrees, and only one of them is the
one you are reading. Sync in one place.

---

## 2 - Commit your own paths, never `git commit -a`

This is the git-level restatement of the boundary rule, and it is the single
most valuable line in this file.

```
git add scripts/ && git commit -m "..."     # yes
git commit -am "..."                        # no
```

`-a` stages every modified tracked file, including whatever another member is
part-way through writing in its own directory. The result is a commit that
claims work you did not do, mixed with work that was not finished, attributed to
whoever ran the command. That is the exact failure the ownership rule exists to
prevent, arriving through a door the ownership rule does not cover.

Two habits follow:

- **Stage by path, and read what you staged.** `git status` before every commit.
  If a file you do not own is staged, you have already made the mistake and can
  still take it back.
- **Never `git checkout .` or `git restore .` to tidy up.** It discards another
  member's uncommitted work with no undo and no record that it existed.

---

## 3 - The log in a merge

`<state>/` holds two kinds of file and they merge in opposite ways.

### `INDEX.md` is generated - never resolve it by hand

The tables between the `<!-- handoff:... -->` markers are rebuilt from the
thread files by `sync`. Two members who both ran `sync` will conflict on nearly
every row, and every one of those conflicts is noise: the file is a build
artifact of `threads/`.

**Resolution: take either side whole, then re-run `sync`.**

```
git checkout --ours <state>/INDEX.md   # or --theirs; it does not matter
<cli> sync
git add <state>/INDEX.md
```

The one part that is not generated is **Conversation history**, which is
hand-written prose. If both sides added rows there, keep both and order them
newest first. Losing a row there is a real loss; losing a generated row is not,
because the next `sync` puts it back.

### Thread files are append-only - keep both sides

Two members appending comments to the same thread on different branches will
conflict at the end of the file. Almost always the correct resolution is **keep
both comments, ordered by their stamps**, because that is what actually
happened: two members spoke, and a merge is not the place to decide that one of
them did not.

This is the payoff for the timestamp discipline. Every comment carries
`[Name, DDMM, HHMM]` read from a real clock, so the merge order is not a
judgement call - it is written on the comments themselves. Order them, then run
`doctor`, which will say if the result came out of sequence.

**Never resolve a thread conflict by dropping a comment.** If two comments truly
say incompatible things, that is a disagreement to settle in a new comment, not
by editing history so that one of them was never said.

### After any merge that touched `<state>/`

```
<cli> sync
<cli> doctor
```

`sync` rebuilds the index from whatever survived the merge; `doctor` reports
what did not. A merge is exactly the moment the index and the threads can
quietly stop agreeing, and checking is two commands.

---

## 4 - Review before merge, owner before push

`PROTOCOL.md` section 9 separates deciding from acting: members can settle a
question completely on technical grounds and still not be entitled to run the
command. Pushing is the clearest case of that in the whole protocol.

- **A commit is local and reversible.** Any member may commit its own paths.
- **A merge to `main` is local but canonical.** It changes what the repository
  will publish when the owner pushes.
- **A push is outward-facing and effectively permanent.** It puts the work on
  someone else's server, where it can be cloned, cached, indexed and forked
  before anyone notices a mistake. Deleting it afterwards does not reliably
  unpublish it.

So there are three roles:

| Role | Who | What they do |
|---|---|---|
| **Author** | The member who made the change | Commits only their own paths, runs the relevant checks, and opens or updates the review thread. |
| **Reviewer-of-record** | A member who did not author that change | Reviews the diff, records approval or findings in the thread, and says whether it may merge. |
| **Owner** | The human | Approves outward-facing GitHub actions: creating the repo, pushing, opening a PR, changing visibility, or publishing `main`. |

**A branch is releasable only once every member has committed its own paths.**
This is the corollary of "commit your own paths" and it is easy to miss, because
each member's own work looks finished from where it is standing. A branch where
one member has committed and another has not is not half-ready - it can be
actively wrong, in a way neither member sees. It happened here on the first
release: one member's committed documentation described a layout that the other
member's committed code did not yet produce, and each half was correct on its
own. The reviewer-of-record checks the branch, not the diff they were handed.

**The reviewer is not the author.** This is not ceremony; it is the cheapest
bug finder in the protocol. The author will usually re-run the same reasoning
that produced the change, while the other member is more likely to notice that
the branch now violates an invariant, contradicts the docs, or exposes
something that should stay local.

The review record lives in an `AGENT-` thread unless it needs an owner decision
or machine approval. A normal release thread should name:

- the commits under review,
- who authored them,
- who is reviewer-of-record,
- which checks passed,
- whether the branch may merge.

When a GitHub PR exists, link it from the thread and keep the same reviewer. If
there is no remote yet, the thread is the pull-request record: review the branch
locally, merge to `main` only after approval is written there, then ask the
owner before pushing `main` or creating the public repository.

So: **members commit freely, and a push needs the owner's go-ahead at the moment
of pushing** - an `ASK-` thread of type `REQUEST`, not a permission banked weeks
earlier. The same applies to opening a pull request, creating a repository, and
flipping a repository between private and public.

Three things belong in that request, for the reason section 9 gives - make it
answerable without research:

- **Which remote and which account.** A machine with two configured identities
  will happily push to the wrong one, and the mistake is public by the time it
  is visible.
- **What becomes visible, and to whom.** "Public repo" and "private repo" are
  different decisions with different consequences. Say which you are asking for.
- **Whether anything in the diff should not leave the machine.** The member
  proposing the push has read the diff and is the cheapest place to catch a key,
  a token, an internal hostname or a customer name. Say that you looked, and say
  what you looked for.

---

## 5 - Commit messages do not need agent attribution

You already have an attributed record. Every decision, every disagreement and
every author is in `threads/`, stamped and quoted. Repeating that in commit
trailers duplicates the log somewhere nobody reads it back from, and the copy
goes stale the moment the thread continues past the commit.

Write the message for the change: what moved and why, in plain words. If the
reasoning is long it belongs in a thread, and then the thread id is the useful
thing to put in the message - one token that leads to the whole argument.

---

## 6 - When it goes wrong

- **A member committed into another member's directory.** Say so in a thread
  before fixing it, so the owner of that directory learns it from the log rather
  than from a surprising diff. Then revert those paths, not the whole commit;
  the rest of it was legitimate.
- **A thread file lost a comment in a merge.** It is recoverable - `git log -p`
  on the thread file has every version. Restore the comment with its original
  stamp, and add a new comment saying it was restored and why. Do not re-stamp
  it to now: that would make the log lie about when it was said, and the log's
  whole value is that it does not.
- **`INDEX.md` is full of conflict markers.** Do not repair it by hand. Check
  out either side whole and run `sync`.
- **Two members keep conflicting in the same file.** That is the boundary being
  in the wrong place, not a git problem. See `onboarding.md` section 5.
