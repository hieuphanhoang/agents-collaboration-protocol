# How we work here - <PROJECT>

Working conventions for the members of this project. Not the log: decisions
about the *work* go in `chat_logs/`, and this file holds the standing rules
about *how* we work, which would otherwise clog the log with process talk.

Read `PROTOCOL.md` first - that is how the log itself works, and it is the same
in every project. This file is what is specific to this one. Keep it short. A
convention nobody can remember is not a convention.

---

## Before you hand work to another member

The point of this list is that the next member should never be the one to
discover your change was broken. Fill in what applies here and delete the rest.

- Build or typecheck command:
- Test command:
- Linter or formatter, if one is enforced:
- Anything slow or manual that still has to happen:

## Conventions that have bitten us

One line each, with the reason. A rule whose reason is not written down gets
dropped by the first member who finds it inconvenient, and they will not be
wrong to.

| Convention | Why |
|---|---|
| | |

## Definition of done

What has to be true before a thread can move to `closed`. `PROTOCOL.md`
section 7 requires the decision to be written into the spec, the contract or the
code; add anything else this project needs - a migration applied, a doc updated,
a flag removed.

---

## Keeping this file honest

Add to it when a member gets something wrong that a written rule would have
prevented, and delete from it when a rule stops being true. It is not a style
guide and it is not a place to record decisions - those belong in the code and
the contract, per `PROTOCOL.md` section 7.

If a convention here is about the *log* rather than the *project* - naming,
ordering, when to open a thread - it belongs in `PROTOCOL.md` instead, and
changing that is the owner's call.
