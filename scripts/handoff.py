#!/usr/bin/env python3
"""
agent-handoff - file-based collaboration protocol for multi-provider agent teams.

Every command reads the real system clock, so timestamps cannot be invented.
Writes are atomic and check for concurrent modification, because the whole point
of this protocol is that several agents touch these files.

Stdlib only. Works on Windows, macOS, Linux.

  init    scaffold the protocol into a repo
  new     open a thread (AGENT- between members, ASK- to the owner)
  reply   append an attributed comment to a thread
  close   close a thread after promoted files pass existence and recency checks
  sync    regenerate the handoff CHATLOG.md index blocks from chat_logs/
  summary print what is waiting right now, for a member arriving cold
  brief   emit a paste-ready briefing for a member with no file access
  doctor  check the log for integrity problems
  test    run the built-in regression suite

Comment bodies come from --body, --body-file or --body-stdin. Prefer a file or
stdin for anything long or quoted: shells disagree about quoting, and a mangled
comment is a lie in the record.
"""
import argparse
import datetime
import fnmatch
import hashlib
import os
import pathlib
import re
import sys

THREAD_FILE = re.compile(r"^(AGENT|ASK)-(\d{3})-(.+)\.md$")
STAMP = re.compile(r"\*\*\[([^,\]]+), (\d{4}), (\d{4})\]\*\*")
# Anything that opens a line like a comment header. A header that does not also
# match STAMP is invisible to every other command, so doctor must say so rather
# than silently counting the comment as absent.
HEADERISH = re.compile(r"^\*\*\[(.+?)\]\*\*\s*$", re.M)
# Key is anything between the bold markers. Never enumerate allowed characters:
# real repos carry "From -> To" and "From <arrow> To" and we must read both.
HDR_ROW = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$", re.M)
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
HISTORY_TIME = re.compile(r"^\|\s*(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\s*\|")

STATUSES = {"open", "answered", "closed", "withdrawn", "superseded", "blocked"}
LIVE = {"open", "answered", "blocked"}
TYPES = {"STATUS", "QUESTION", "REQUEST", "ANSWER", "DECISION", "BLOCKER", "ACK"}
REQUIRED_HEADERS = {"From -> To", "Type", "Status", "Time"}
DEFAULT_STATE_DIR = ".agents"
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")

BLOCKS = {
    "awaiting": ("<!-- handoff:awaiting:start -->", "<!-- handoff:awaiting:end -->"),
    "open": ("<!-- handoff:open:start -->", "<!-- handoff:open:end -->"),
    "threads": ("<!-- handoff:threads:start -->", "<!-- handoff:threads:end -->"),
}

# Characters that differ across providers. Normalise before parsing so a repo
# written by one agent stays readable to another.
FOLD = {"→": "->", "←": "<-", "—": "-", "–": "-",
        "·": "-", "‘": "'", "’": "'", "“": '"', "”": '"'}


def fold(s):
    for k, v in FOLD.items():
        s = s.replace(k, v)
    return s


def now():
    return datetime.datetime.now()


def now_stamp():
    d = now()
    return d.strftime("%d%m"), d.strftime("%H%M")


def pretty(ddmm, hhmm):
    return f"{ddmm[:2]}-{ddmm[2:]} {hhmm[:2]}:{hhmm[2:]}"


def atomic_write(path, text):
    """Write via temp + os.replace so a crash or a racing reader never sees half a file."""
    tmp = path.with_name(path.name + ".handoff-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_copy(src, dst):
    """
    Copy byte for byte, not through text mode.

    write_text() rewrites newlines to the platform's, so a copied script would
    never match its source on Windows - the staleness check below would fire on
    every run, and nobody could tell a stale copy from a re-encoded one.
    """
    tmp = dst.with_name(dst.name + ".handoff-tmp")
    tmp.write_bytes(src.read_bytes())
    os.replace(tmp, dst)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def state_name(root, requested=None):
    if requested:
        parts = re.split(r"[\\/]+", requested)
        posix = pathlib.PurePosixPath(requested)
        win = pathlib.PureWindowsPath(requested)
        if posix.is_absolute() or win.is_absolute() or win.drive or ".." in parts:
            sys.exit(f"unsafe state dir '{requested}' - use a safe relative path")
        clean = "/".join(part for part in parts if part and part != ".")
        if not clean:
            sys.exit(f"unsafe state dir '{requested}' - use a safe relative path")
        if clean == ".claude/handoff":
            return clean
        return ".claude/handoff" if clean == ".claude" else clean
    installed = [".agents", ".claude/handoff"]
    for name in installed:
        p = root / name
        if (p / "CHATLOG.md").exists() or (p / "PROTOCOL.md").exists():
            return name
    agents_exists = (root / ".agents").is_dir()
    claude_exists = (root / ".claude").is_dir()
    if claude_exists and not agents_exists:
        return ".claude/handoff"
    return DEFAULT_STATE_DIR


def state_dir(root, requested=None):
    return root / state_name(root, requested)


def threads_dir(root, requested=None):
    return state_dir(root, requested) / "chat_logs"


def log_path(root, requested=None):
    return state_dir(root, requested) / "CHATLOG.md"


def project_file(root, name, requested=None):
    return state_dir(root, requested) / name


def state_rel(root, requested=None):
    return state_name(root, requested)


def render_state_text(text, state):
    """Templates are written for .agents; .claude is an explicit alternate."""
    return text.replace(".agents", state)


def resolve_years(stamps, base):
    """
    Comment stamps are DDMM/HHMM with no year - that is the human-readable format
    the protocol settled on. Recover the year from the thread's creation date so
    sorting does not break at a year boundary: stamps run forward from creation,
    so a (month, day) earlier than the previous one has rolled into a new year.

    A stamp that is not a real date and time resolves to None rather than raising.
    datetime does the validating, so day 32, month 00 and minute 60 are rejected
    by the calendar itself instead of by hand-written bounds that miss cases. An
    unresolvable stamp must not move `year` or `prev` either: one impossible
    entry should not shift every later timestamp in the thread.
    """
    out, year, prev = [], base.year, (base.month, base.day)
    for who, ddmm, hhmm in stamps:
        try:
            day, month = int(ddmm[:2]), int(ddmm[2:])
            rolled = year + 1 if (month, day) < prev else year
            dt = datetime.datetime(rolled, month, day, int(hhmm[:2]), int(hhmm[2:]))
        except ValueError:
            out.append((who, None))
            continue
        year, prev = rolled, (month, day)
        out.append((who, dt))
    return out


def status_token(t):
    """
    The first word of Status, lowercased, or "" when the field is blank.

    A member who clears a status value instead of replacing it leaves
    `| **Status** |  |`, which parses to an empty string. Taking [0] of that
    raised - and it raised inside doctor, the one command whose job is to report
    exactly this kind of damage.
    """
    return (t["status"].split() or [""])[0].lower()


def is_live(t):
    """
    open, answered and blocked are all still in flight; the rest are done.

    A status nobody can read counts as live. The alternative is that a blank or
    misspelt status quietly drops the thread out of the index's open sections,
    and a thread that vanishes from the index is a worse failure than one listed
    with a bad status: doctor reports both, but only one of them stays visible
    to the members while somebody fixes it.
    """
    st = status_token(t)
    return st in LIVE or st not in STATUSES


def body_from(a, default=None):
    """
    Resolve the comment body from --body, --body-file or --body-stdin.

    Long comments passed as a shell argument are the most common way a write to
    this log fails: PowerShell and POSIX shells disagree about quoting, and a
    comment containing a quoted command or a newline gets mangled or rejected.
    A file or stdin removes the shell from the path entirely.
    """
    given = [k for k, v in (("--body", a.body),
                            ("--body-file", getattr(a, "body_file", None)),
                            ("--body-stdin", getattr(a, "body_stdin", False))) if v]
    if len(given) > 1:
        sys.exit(f"give only one of {', '.join(given)}")
    if a.body:
        return a.body
    if getattr(a, "body_file", None):
        p = pathlib.Path(a.body_file)
        if not p.is_file():
            sys.exit(f"no such body file: {p}")
        return p.read_text(encoding="utf-8").strip("\n")
    if getattr(a, "body_stdin", False):
        text = sys.stdin.read().strip("\n")
        if not text.strip():
            sys.exit("--body-stdin got nothing on stdin")
        return text
    return default


def add_body_args(parser):
    parser.add_argument("--body", help="comment text")
    parser.add_argument("--body-file", help="read the comment from a file "
                                            "(no shell quoting to get wrong)")
    parser.add_argument("--body-stdin", action="store_true",
                        help="read the comment from stdin")


def owes_reply(t):
    """
    Who the thread is waiting on: the participant who did not speak last.

    The 'From -> To' header records who opened the thread, not who owes the next
    turn, so reading the debt off it means the index still points at the last
    person who answered. Only the two named participants move the debt -
    a transcribed owner answer or a relayed third party does not.
    """
    parts = [p.strip() for p in t["to"].split("->")]
    if len(parts) != 2 or not all(parts):
        return t["to"]
    frm, to = parts
    other = {frm.lower(): to, to.lower(): frm}
    for who, _, _ in reversed(t["stamps"]):
        nxt = other.get(who.strip().lower())
        if nxt:
            return nxt
    return to


def read_threads(root, requested=None):
    d = threads_dir(root, requested)
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.md")):
        m = THREAD_FILE.match(f.name)
        if not m:
            continue
        # Read the bytes once and hash exactly what we read, so `reply` can tell
        # whether the file changed after this read. Hashing a re-read would leave
        # the very gap the check exists to close. The newline folding reproduces
        # what text mode would have done, so writing back is unchanged.
        data = f.read_bytes()
        raw = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        text = fold(raw)
        hdr = {k.strip(): v.strip() for k, v in HDR_ROW.findall(text)}
        stamps = STAMP.findall(text)
        iso = ISO.search(hdr.get("Time", ""))
        base = (datetime.datetime(*map(int, iso.groups()))
                if iso else datetime.datetime.fromtimestamp(f.stat().st_mtime))
        dated = resolve_years(stamps, base)
        title = fold(text.splitlines()[0]).lstrip("#").strip()
        title = re.sub(r"^`[^`]+`\s*[-:]?\s*", "", title).strip()
        out.append({
            "path": f, "raw": raw, "text": text, "hdr": hdr,
            "id": f"{m.group(1)}-{m.group(2)}", "kind": m.group(1),
            "num": int(m.group(2)), "title": title,
            "status": hdr.get("Status", "open"),
            "to": hdr.get("From -> To", "?"),
            "type": hdr.get("Type", "-"),
            "stamps": stamps, "dated": dated,
            "last_dt": next((d for _, d in reversed(dated) if d), None),
            "base": base, "digest": hashlib.sha256(data).hexdigest(),
        })
    return out


def next_id(root, kind, requested=None):
    ns = [t["num"] for t in read_threads(root, requested) if t["kind"] == kind]
    return f"{kind}-{max(ns) + 1:03d}" if ns else f"{kind}-001"


def set_header(text, key, value):
    """Insert or replace a header row, tolerating the folded and unfolded key."""
    pat = re.compile(r"^\|\s*\*\*" + re.escape(key) + r"\*\*\s*\|.*\|\s*$", re.M)
    row = f"| **{key}** | {value} |"
    if pat.search(text):
        return pat.sub(row, text, count=1)
    anchor = re.compile(r"^\|\s*\*\*Status\*\*\s*\|.*\|\s*$", re.M)
    return anchor.sub(lambda m: m.group(0) + "\n" + row, text, count=1)


def refresh_meta(t):
    """Keep Latest and Updated current so newest state is visible without scrolling."""
    if not t["dated"]:
        return t["raw"]
    who, dt = next(((w, d) for w, d in reversed(t["dated"]) if d), (None, None))
    if dt is None:
        return t["raw"]
    text = t["raw"]
    text = set_header(text, "Latest",
                      f"{who}, {dt.strftime('%d-%m %H:%M')} ({len(t['stamps'])} comments)")
    text = set_header(text, "Updated", dt.strftime("%Y-%m-%d %H:%M"))
    return text


# ---------------------------------------------------------------- commands
def agents_section(cli_path, state):
    return f"""
## Multi-agent protocol

Several agents work this repository at once. Before writing anything:

1. Read `{state}/PROTOCOL.md` - how the shared log works and what you may edit.
2. Read `{state}/ROSTER.md` - who owns which directories. Never edit a
   directory you do not own; open a thread or propose a contract change instead.
3. Write to the log with `{cli_path}`, not by hand:
   `python {cli_path} reply AGENT-004 --frm <you> --body-file msg.md`
   It stamps from the system clock. Never write a timestamp yourself.
4. Run `python {cli_path} summary <you>` to see what is waiting on
   you. Without a name it lists every live thread rather than yours.
"""


# Everything init copies out of the skill folder, named once so that the guard
# below and the copy loop cannot fall out of step with each other.
INIT_SOURCES = [("references/protocol.md", "PROTOCOL.md"),
                ("assets/CHATLOG.template.md", "CHATLOG.md"),
                ("assets/ROSTER.template.md", "ROSTER.md"),
                ("assets/CONTRIBUTING.template.md", "CONTRIBUTING.md")]
TEST_SUITE = "scripts/test_handoff.py"


def protocol_pointer():
    return """# Collaboration protocol - pointer

The protocol this project follows is `references/protocol.md`. **Read that.**

This file is a pointer, not a copy. `references/protocol.md` is the artefact
this repository ships to other repos, so a second copy of it here would be two
files with the same content and no rule about which one wins - the exact drift
`AGENTS.md` forbids. A pointer file is fine; a second file with real content in
it is not.
"""


def is_skill_checkout(root, here):
    """The skill checkout already has the authoritative CLI under scripts/."""
    cli = (here / "scripts" / "handoff.py").resolve()
    return root == here and cli == pathlib.Path(__file__).resolve()


def cmd_init(a):
    root = pathlib.Path(a.root).resolve()
    here = pathlib.Path(__file__).resolve().parent.parent
    skill_checkout = is_skill_checkout(root, here)
    state = state_rel(root, a.state_dir)
    # init is the one subcommand that needs the skill folder, because it copies
    # templates out of it. The copy installed at .agents/handoff.py sits two
    # levels under a target repo, where none of them exist - so without this
    # check it dies part-way through scaffolding with a bare FileNotFoundError,
    # leaving a half-built repo and a member with nothing to go on. Say which
    # copy they are running and where the working one is.
    missing = [s for s, _ in INIT_SOURCES if not (here / s).is_file()]
    if not (here / TEST_SUITE).is_file():
        missing.append(TEST_SUITE)
    if missing:
        sys.exit(f"""init cannot find the skill templates under {here}
  missing: {', '.join(missing)}
This looks like the copy installed in a repo, which ships no templates.
Run init from the skill checkout instead:
  uv run --no-project <skill>/scripts/handoff.py init --root <repo>
Every other subcommand works from this copy.""")
    threads_dir(root, state).mkdir(parents=True, exist_ok=True)
    for src, dst in INIT_SOURCES:
        target = state_dir(root, state) / dst
        if target.exists() and (not a.force or dst == "CONTRIBUTING.md"):
            print(f"  skip (exists)  {state}/{dst}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (protocol_pointer() if skill_checkout and dst.endswith("PROTOCOL.md")
                else (here / src).read_text(encoding="utf-8"))
        text = render_state_text(text, state)
        atomic_write(target, text)
        print(f"  wrote          {state}/{dst}")

    # The tool has to live in the repo, not only in one provider's skill folder.
    # .agents/PROTOCOL.md tells every member to stamp with it; a member who
    # cannot run it is pushed straight into the hand-editing the same document
    # forbids.
    tool = state_dir(root, state) / "handoff.py"
    if skill_checkout:
        print(f"  skip (skill)   {state}/handoff.py - use scripts/handoff.py here")
    elif tool.exists() and not a.force and digest(tool) == digest(pathlib.Path(__file__)):
        print(f"  skip (current) {state}/handoff.py")
    else:
        tool.parent.mkdir(parents=True, exist_ok=True)
        atomic_copy(pathlib.Path(__file__).resolve(), tool)
        atomic_copy(here / TEST_SUITE, tool.with_name("test_handoff.py"))
        print(f"  wrote          {state}/handoff.py (+ its test suite)")

    if not (a.no_agents_md or a.no_instructions):
        files = [root / name for name in INSTRUCTION_FILES if (root / name).exists()]
        section = agents_section("scripts/handoff.py" if skill_checkout else f"{state}/handoff.py",
                                 state)
        for instruction in files:
            existing = instruction.read_text(encoding="utf-8") if instruction.exists() else ""
            if "Multi-agent protocol" in existing:
                print(f"  skip (linked)  {instruction.name}")
                continue
            head = existing.rstrip() + "\n" if existing else "# Agent instructions\n"
            atomic_write(instruction, head + section)
            print(f"  {'appended to' if existing else 'wrote':<13}  {instruction.name}")
        if not files:
            print("  skip (none)    no AGENTS.md or CLAUDE.md to register")
    print(f"\nScaffolded into {root}")
    print(f"Next: fill in {state}/ROSTER.md (members, owned directories), then `handoff new`.")


def cmd_new(a):
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    kind = "ASK" if a.ask else "AGENT"
    ttype = a.type.upper()
    if ttype not in TYPES:
        sys.exit(f"unknown type '{a.type}' - use one of: {', '.join(sorted(TYPES))}")
    tid = next_id(root, kind, state)
    ddmm, hhmm = now_stamp()
    slug = re.sub(r"[^a-z0-9]+", "-", fold(a.title).lower()).strip("-")[:48]
    path = threads_dir(root, state) / f"{tid}-{slug}.md"
    if path.exists():
        sys.exit(f"refusing to overwrite {path}")
    body = body_from(a, "(write the opening comment here)")
    atomic_write(path, f"""# `{tid}` - {a.title}

| | |
|---|---|
| **From -> To** | {a.frm} -> {a.to} |
| **Type** | {ttype} |
| **Status** | open |
| **Latest** | {a.frm}, {pretty(ddmm, hhmm)} (1 comments) |
| **Updated** | {now().strftime('%Y-%m-%d %H:%M')} |
| **Time** | {now().strftime('%Y-%m-%d %H:%M')} |

---

**[{a.frm}, {ddmm}, {hhmm}]**

{body}
""")
    print(f"created {path.relative_to(root)}")
    if kind == "ASK":
        print("\nReminder: an ASK- thread claims the members already agreed a")
        print("recommendation, or that a decision you made needs the owner's")
        print("go-ahead to act. If neither is true yet, make it an AGENT- thread.")
    cmd_sync(a)


def cmd_reply(a):
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    match = [t for t in read_threads(root, state) if t["id"] == a.id.upper()]
    if not match:
        sys.exit(f"no thread {a.id}")
    t = match[0]
    before = t["digest"]
    body = body_from(a)
    if body is None:
        sys.exit("a reply needs a body: --body, --body-file or --body-stdin")

    ddmm, hhmm = now_stamp()
    src = f"\n*(said {a.source_time}; transcribed on arrival)*\n" if a.source_time else ""
    text = t["raw"].rstrip() + f"\n\n---\n\n**[{a.frm}, {ddmm}, {hhmm}]**\n{src}\n{body}\n"
    if a.status:
        if a.status not in STATUSES:
            sys.exit(f"unknown status '{a.status}' - use one of: {', '.join(sorted(STATUSES))}")
        text = set_header(text, "Status", a.status)

    if digest(t["path"]) != before:
        sys.exit(f"{t['path'].name} changed on disk while composing.\n"
                 "Another member or the owner edited it. Re-read it and retry - "
                 "never overwrite an edit you did not make.")
    atomic_write(t["path"], text)

    t2 = [x for x in read_threads(root, state) if x["id"] == t["id"]][0]
    atomic_write(t2["path"], refresh_meta(t2))
    print(f"appended to {t['path'].name}  [{a.frm}, {ddmm}, {hhmm}]")
    cmd_sync(a)


def promoted_path(root, value):
    parts = re.split(r"[\\/]+", value)
    posix = pathlib.PurePosixPath(value)
    win = pathlib.PureWindowsPath(value)
    if posix.is_absolute() or win.is_absolute() or win.drive or ".." in parts:
        sys.exit(f"unsafe promoted path '{value}' - use a path relative to --root")
    clean_parts = [p for p in parts if p and p != "."]
    if not clean_parts:
        sys.exit(f"unsafe promoted path '{value}' - use a path relative to --root")
    clean = pathlib.Path(*clean_parts)
    return root / clean


def cmd_close(a):
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    match = [t for t in read_threads(root, state) if t["id"] == a.id.upper()]
    if not match:
        sys.exit(f"no thread {a.id}")
    t = match[0]
    before = t["digest"]
    st = status_token(t)
    if st in {"closed", "withdrawn", "superseded"}:
        sys.exit(f"{t['id']} is already terminal ({st})")
    if not t["base"]:
        sys.exit(f"{t['id']} has no valid creation timestamp to verify against")

    promoted = []
    problems = []
    for raw in a.promoted_to:
        path = promoted_path(root, raw)
        if not path.exists():
            problems.append(f"{raw}: missing")
            continue
        mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
        if mtime < t["base"]:
            problems.append(f"{raw}: stale (modified {mtime.strftime('%Y-%m-%d %H:%M')}, "
                            f"thread created {t['base'].strftime('%Y-%m-%d %H:%M')})")
            continue
        promoted.append(raw)
    if problems:
        sys.exit("cannot close; promoted path check failed:\n  " + "\n  ".join(problems))

    extra = body_from(a, "")
    ddmm, hhmm = now_stamp()
    path_list = "\n".join(f"- `{p}`" for p in promoted)
    generated = (
        "Closing after promoted files passed the existence and recency checks:\n\n"
        f"{path_list}\n\n"
        "This is a recency check only, not proof of relevance or review quality."
    )
    body = f"{extra}\n\n{generated}" if extra else generated
    text = t["raw"].rstrip() + f"\n\n---\n\n**[{a.frm}, {ddmm}, {hhmm}]**\n\n{body}\n"
    text = set_header(text, "Status", "closed")

    if digest(t["path"]) != before:
        sys.exit(f"{t['path'].name} changed on disk while composing.\n"
                 "Another member or the owner edited it. Re-read it and retry - "
                 "never overwrite an edit you did not make.")
    atomic_write(t["path"], text)

    t2 = [x for x in read_threads(root, state) if x["id"] == t["id"]][0]
    atomic_write(t2["path"], refresh_meta(t2))
    print(f"closed {t['path'].name}  [{a.frm}, {ddmm}, {hhmm}]")
    cmd_sync(a)


def _row(t, cols):
    return "| " + " | ".join(cols) + " |"


def cmd_sync(a):
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    log = log_path(root, state)
    if not log.exists():
        sys.exit(f"no {state}/CHATLOG.md - run `handoff init` first")

    for t in read_threads(root, state):
        new = refresh_meta(t)
        if new != t["raw"]:
            atomic_write(t["path"], new)

    ts = read_threads(root, state)
    ts.sort(key=lambda t: t["last_dt"] or datetime.datetime.min, reverse=True)

    def link(t):
        return f"[`{t['id']}`](chat_logs/{t['path'].name})"

    def when(t):
        return t["last_dt"].strftime("%d-%m %H:%M") if t["last_dt"] else "-"

    blocks = {}
    blocks["threads"] = (["| ID | Subject | From -> To | Type | Status | Last |",
                          "|---|---|---|---|---|---|"] +
                         [_row(t, [link(t), t["title"], t["to"], t["type"],
                                   t["status"], when(t)]) for t in ts])

    live = [t for t in ts if is_live(t)]
    openagent = [t for t in live if t["kind"] == "AGENT"]
    blocks["open"] = ["| ID | Subject | Owes a reply | Since |", "|---|---|---|---|"]
    if openagent:
        blocks["open"] += [_row(t, [link(t), t["title"], owes_reply(t), when(t)])
                           for t in openagent]
    else:
        blocks["open"].append("| - | *none between members* | | |")

    openask = [t for t in live if t["kind"] == "ASK"]
    blocks["awaiting"] = ["| ID | Decision or approval | Since |", "|---|---|---|"]
    if openask:
        blocks["awaiting"] += [_row(t, [link(t), t["title"], when(t)]) for t in openask]
    else:
        blocks["awaiting"].append("| - | *nothing waiting on you* | |")

    text = log.read_text(encoding="utf-8")
    missing = []
    for name, (b, e) in BLOCKS.items():
        if b in text and e in text:
            text = text[:text.index(b) + len(b)] + "\n" + "\n".join(blocks[name]) + "\n" + text[text.index(e):]
        else:
            missing.append(name)
    atomic_write(log, text)
    print(f"synced {state}/CHATLOG.md - {len(ts)} threads, {len(openagent)} open between members, "
          f"{len(openask)} awaiting owner")
    if missing:
        print(f"  note: no marker block for {', '.join(missing)} - add the "
              f"<!-- handoff:{missing[0]}:start/end --> pair to {state}/CHATLOG.md")


def cmd_summary(a):
    """What a member needs to know on arrival, without reading the whole log."""
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    ts = sorted(read_threads(root, state),
                key=lambda t: t["last_dt"] or datetime.datetime.min, reverse=True)
    live = [t for t in ts if is_live(t)]
    asks = [t for t in live if t["kind"] == "ASK"]
    agents = [t for t in live if t["kind"] == "AGENT"]

    def line(t, who=None):
        when = t["last_dt"].strftime("%d-%m %H:%M") if t["last_dt"] else "-"
        tail = f"  waiting on {who}" if who else ""
        return f"  {t['id']}  {t['title'][:46]:<46} {t['status']:<9} {when}{tail}"

    print(f"{len(ts)} threads, {len(live)} live\n")
    print(f"AWAITING THE OWNER ({len(asks)})")
    print("\n".join(line(t) for t in asks) if asks else "  nothing waiting on them")
    print(f"\nBETWEEN MEMBERS ({len(agents)})")
    print("\n".join(line(t, owes_reply(t)) for t in agents)
          if agents else "  nothing in flight")
    if a.member:
        mine = [t for t in agents if owes_reply(t).lower() == a.member.lower()]
        print(f"\nYOURS ({a.member}): {len(mine)} thread(s) waiting on you")
        for t in mine:
            print(line(t))
    print(f"\nFull index: {state}/CHATLOG.md   Rules: {state}/PROTOCOL.md   Ownership: {state}/ROSTER.md")


def cmd_brief(a):
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    ts = [t for t in read_threads(root, state)
          if is_live(t)]
    if a.thread:
        want = {x.upper() for x in a.thread}
        ts = [t for t in ts if t["id"] in want]
    out = ["=" * 70, f"BRIEFING FOR: {a.member}",
           "You have no direct access to this repository. Read this, then reply in",
           "the format at the end. Another member transcribes your reply verbatim",
           "into the log under your name.", "=" * 70, ""]
    for name in ("ROSTER.md", "PROTOCOL.md"):
        p = project_file(root, name, state)
        if p.exists():
            out += [f"--- {name.replace('.md','')} ---",
                    p.read_text(encoding="utf-8").strip(), ""]
    out += ["--- OPEN THREADS ---", ""]
    for t in ts:
        out += [f"### {t['id']} - {t['title']}", t["text"].strip(), "", "-" * 70, ""]
    out += ["--- HOW TO REPLY ---",
            "One block per thread you are answering:", "",
            "    THREAD: AGENT-00X",
            "    <your comment>", "",
            "**Do not write a timestamp or a name header.** You cannot read this",
            "project's clock, and hours may pass before your reply is pasted back.",
            "A guessed time is worse than none: the log's value rests on times being",
            "real. Whoever transcribes you stamps the moment it actually lands, and",
            "can record when you said it separately if that matters.",
            "",
            "You are answering from this text alone, not from the code. Mark clearly",
            "which parts of your answer depend on something you have not seen, so the",
            "member with repo access can check those against the files.",
            "",
            "Say plainly when you disagree. Agreement you do not hold is worse than",
            "useless here - it removes the reason for asking you."]
    txt = "\n".join(out)
    if a.out:
        atomic_write(pathlib.Path(a.out), txt)
        print(f"briefing written to {a.out}  ({len(txt)} chars, {len(ts)} threads)")
    else:
        print(txt)


def history_notes(body, ts, state, cap=5):
    """
    Nudge, never fail, when Conversation history has fallen behind the threads.

    The tool regenerates every other table, so this is the one section that can
    silently stop being written - and it is the section that says what a turn
    actually meant. A hard error would be wrong (only a participant can write
    it, and not always in the same session), but silence lets it rot.
    """
    m = re.search(r"##\s*Conversation history(.*?)(?=\n##\s|\Z)", body, re.S)
    if not m:
        return [f"{state}/CHATLOG.md: no 'Conversation history' section"]
    section = m.group(1)
    rows = [l for l in section.splitlines()
            if l.startswith("|") and set(l) - set("|-: ")
            and "Speaker" not in l]
    active = [t for t in ts if t["stamps"]]
    if not active:
        return []
    if not rows:
        return [f"{state}/CHATLOG.md: Conversation history is empty though "
                f"{len(active)} thread(s) have comments - write your turn"]
    missing = [t["id"] for t in active if t["id"] not in section]
    if not missing:
        latest_threads = [t for t in active if t["last_dt"]]
        if not latest_threads:
            return []
        latest = max(latest_threads, key=lambda t: t["last_dt"])
        history_dates = resolve_history_years(rows, latest["last_dt"])
        if not history_dates:
            return []
        latest_history = max(history_dates)
        if latest["last_dt"] <= latest_history:
            return []
        return [f"{state}/CHATLOG.md: Conversation history latest row "
                f"({latest_history.strftime('%Y-%m-%d %H:%M')}) is older than "
                f"latest thread activity ({latest['id']} at "
                f"{latest['last_dt'].strftime('%Y-%m-%d %H:%M')}) - "
                f"add your turn at the top, newest first"]
    shown = ", ".join(missing[:cap]) + (" ..." if len(missing) > cap else "")
    return [f"{state}/CHATLOG.md: no Conversation history row mentions {shown} - "
            f"add your turn at the top, newest first"]


def resolve_history_years(rows, anchor):
    """
    Recover years for Conversation history rows.

    Those rows are newest-first DD-MM HH:MM, while thread comments are
    chronological DDMM/HHMM. This is the same rollover rule as resolve_years(),
    applied in reverse and anchored to the latest real thread activity: as rows
    move down the table, a later month/day means the history crossed into the
    previous year. Invalid or undated rows do not move the recovered year.
    """
    out, year, prev = [], anchor.year, (anchor.month, anchor.day)
    for row in rows:
        m = HISTORY_TIME.match(row)
        if not m:
            continue
        day, month, hour, minute = map(int, m.groups())
        rolled = year - 1 if (month, day) > prev else year
        try:
            dt = datetime.datetime(rolled, month, day, hour, minute)
        except ValueError:
            continue
        year, prev = rolled, (month, day)
        out.append(dt)
    return out


def roster_names(root, state):
    """
    Read exact display names from ROSTER.md's Members table.

    Matching is intentionally simple: the name in a thread must equal a name in
    the roster after surrounding whitespace is trimmed. Aliases belong in a
    future roster contract, not in a guess inside doctor.
    """
    path = project_file(root, "ROSTER.md", state)
    if not path.exists():
        return None
    body = fold(path.read_text(encoding="utf-8"))
    m = re.search(r"##\s*Members(.*?)(?=\n##\s|\Z)", body, re.S)
    if not m:
        return set()
    names = set()
    for line in m.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        name = cells[0]
        if (not name or name == "Name" or set(name) <= {"-", ":"}
                or (name.startswith("<") and name.endswith(">"))):
            continue
        names.add(name)
    return names


def roster_notes(root, state, ts):
    names = roster_names(root, state)
    if names is None:
        return [f"{state}/ROSTER.md missing - cannot validate thread participants"]
    if not names:
        return []
    notes = []
    for t in ts:
        seen = []
        if "->" in t["to"]:
            seen += [p.strip() for p in t["to"].split("->") if p.strip()]
        for who, _, _ in t["stamps"]:
            who = who.strip()
            if who:
                seen.append(who)
        unknown = sorted({x for x in seen if x not in names})
        for who in unknown:
            notes.append(f"{t['id']}: participant '{who}' is not listed in ROSTER.md")
    return notes


def gitignore_matches(pattern, rel):
    """Small gitignore subset for catching ignored handoff state."""
    pattern = pattern.replace("\\", "/").lstrip("/")
    rel = rel.replace("\\", "/")
    if pattern.endswith("/"):
        prefix = pattern.rstrip("/") + "/"
        return rel.startswith(prefix)
    if "/" in pattern:
        return fnmatch.fnmatchcase(rel, pattern)
    return any(fnmatch.fnmatchcase(part, pattern) for part in rel.split("/"))


def gitignore_decision(root, rel):
    path = root / ".gitignore"
    if not path.exists():
        return False, None
    ignored = False
    match = None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:] if negated else line
        if gitignore_matches(pattern, rel):
            ignored = not negated
            match = f"{path.name}:{n}:{line}"
    return ignored, match


def gitignore_notes(root, state):
    checks = [f"{state}/CHATLOG.md", f"{state}/ROSTER.md",
              f"{state}/PROTOCOL.md", f"{state}/chat_logs/AGENT-001-example.md"]
    hits = []
    for rel in checks:
        ignored, match = gitignore_decision(root, rel)
        if ignored:
            hits.append(match)
    if not hits:
        return []
    shown = ", ".join(dict.fromkeys(hits))
    return [f".gitignore appears to ignore handoff state ({shown}) - "
            "a log excluded from version control will vanish on a fresh clone"]


def cmd_doctor(a):
    root = pathlib.Path(a.root).resolve()
    state = state_rel(root, a.state_dir)
    ts = read_threads(root, state)
    p, notes = [], []
    notes += gitignore_notes(root, state)
    notes += roster_notes(root, state, ts)
    seen = {}
    for t in ts:
        for h in REQUIRED_HEADERS - set(t["hdr"]):
            p.append(f"{t['id']}: missing required header '{h}'")
        st = status_token(t)
        if not st:
            p.append(f"{t['id']}: Status header is empty - set one of {sorted(STATUSES)}")
        elif st not in STATUSES:
            p.append(f"{t['id']}: status '{t['status']}' not one of {sorted(STATUSES)}")
        if t["id"] in seen:
            p.append(f"{t['id']}: duplicate id, also {seen[t['id']]}")
        seen[t["id"]] = t["path"].name
        if not t["stamps"]:
            p.append(f"{t['id']}: no attributed comments")
        if "->" not in t["to"] and t["to"] != "?":
            p.append(f"{t['id']}: recipient '{t['to']}' is not parseable as 'A -> B'")
        if t["to"] == "?":
            p.append(f"{t['id']}: recipient unreadable - check the 'From -> To' header")
        for (who, dt), (_, ddmm, hhmm) in zip(t["dated"], t["stamps"]):
            if dt is None:
                p.append(f"{t['id']}: impossible stamp [{who}, {ddmm}, {hhmm}] - "
                         f"no such date and time")
        for hdr_line in HEADERISH.findall(t["text"]):
            if not STAMP.match(f"**[{hdr_line}]**"):
                p.append(f"{t['id']}: comment header '[{hdr_line}]' is not "
                         f"[Name, DDMM, HHMM] - it will not be read as a comment")
        if t["dated"] and t["raw"] != refresh_meta(t):
            p.append(f"{t['id']}: Latest/Updated stale - run `handoff sync`")

    log = log_path(root, state)
    if not log.exists():
        p.append(f"{state}/CHATLOG.md missing")
    else:
        body = log.read_text(encoding="utf-8")
        for name, (b, e) in BLOCKS.items():
            if b not in body or e not in body:
                p.append(f"{state}/CHATLOG.md: missing '{name}' marker block - "
                         f"sync cannot maintain that section")
        for lk in sorted(set(re.findall(r"\(chat_logs/([^)]+)\)", body))):
            if not (threads_dir(root, state) / lk).exists():
                p.append(f"{state}/CHATLOG.md: dead link -> chat_logs/{lk}")
        ids = {t["id"] for t in ts}
        for tid in sorted(set(re.findall(r"`((?:AGENT|ASK)-\d{3})`", body))):
            if tid not in ids:
                p.append(f"{state}/CHATLOG.md: references {tid}, no such thread")
        for t in ts:
            if t["id"] not in body:
                p.append(f"{state}/CHATLOG.md: {t['id']} exists but is not in the index - run sync")
        notes += history_notes(body, ts, state)

    for t in ts:
        if t["type"] not in TYPES and t["type"] != "-":
            notes.append(f"{t['id']}: type '{t['type']}' is not one of {sorted(TYPES)}")

    print(f"{len(ts)} threads checked")
    if notes:
        print("\nNOTES (not failures):")
        for x in notes:
            print(f"  - {x}")
    if p:
        print("\nPROBLEMS:")
        for x in p:
            print(f"  - {x}")
        sys.exit(1)
    print("\nno problems found" if notes else "no problems found")


def cmd_test(a):
    import test_handoff
    sys.exit(0 if test_handoff.run_all() else 1)


def main():
    # SUPPRESS, not None: with parents=[common] on both the main parser and each
    # subparser, a plain default makes the subparser overwrite the value the main
    # parser already parsed - so `handoff --root X init` would silently write to
    # the current directory instead of X. SUPPRESS leaves the attribute unset
    # unless the flag is actually given, so either position works.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS,
                        help="repo root (default: cwd), accepted before or after the subcommand")
    common.add_argument("--state-dir", default=argparse.SUPPRESS,
                        help="handoff state folder, .agents by default; .claude means "
                             ".claude/handoff; custom values must be relative")
    p = argparse.ArgumentParser(prog="handoff", description=__doc__, parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", parents=[common], help="scaffold into a repo")
    s.add_argument("--force", action="store_true")
    s.add_argument("--no-agents-md", action="store_true",
                   help="deprecated alias for --no-instructions")
    s.add_argument("--no-instructions", action="store_true",
                   help="do not create or append AGENTS.md or CLAUDE.md registration")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("new", parents=[common], help="open a thread")
    s.add_argument("title")
    s.add_argument("--frm", required=True)
    s.add_argument("--to", required=True)
    s.add_argument("--type", default="QUESTION", help="|".join(sorted(TYPES)))
    add_body_args(s)
    s.add_argument("--ask", action="store_true",
                   help="ASK- thread: owner decision, or approval to act")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("reply", parents=[common], help="append an attributed comment")
    s.add_argument("id")
    s.add_argument("--frm", required=True)
    add_body_args(s)
    s.add_argument("--status", help="|".join(sorted(STATUSES)))
    s.add_argument("--source-time",
                   help="when the speaker actually said it, if not now "
                        "(relayed replies); recorded alongside the receipt stamp")
    s.set_defaults(func=cmd_reply)

    s = sub.add_parser("close", parents=[common],
                       help="close after promoted files exist and postdate thread creation "
                            "(recency check only, not relevance proof)")
    s.add_argument("id")
    s.add_argument("--frm", required=True)
    s.add_argument("--promoted-to", required=True, nargs="+",
                   help="repo-relative file(s) updated after the thread was created")
    add_body_args(s)
    s.set_defaults(func=cmd_close)

    s = sub.add_parser("sync", parents=[common], help="regenerate .agents/CHATLOG.md blocks")
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("summary", parents=[common],
                       help="what is waiting right now, without reading the log")
    s.add_argument("member", nargs="?", help="also show what is waiting on this member")
    s.set_defaults(func=cmd_summary)

    s = sub.add_parser("waiting", parents=[common],
                       help="alias for 'summary <member>' - what is waiting on you")
    s.add_argument("member")
    s.set_defaults(func=cmd_summary)

    s = sub.add_parser("brief", parents=[common], help="briefing for a relay member")
    s.add_argument("member")
    s.add_argument("--out")
    s.add_argument("--thread", nargs="*", help="limit to these thread ids")
    s.set_defaults(func=cmd_brief)

    s = sub.add_parser("doctor", parents=[common], help="check log integrity")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("test", parents=[common], help="run the regression suite")
    s.set_defaults(func=cmd_test)

    a = p.parse_args()
    if not getattr(a, "root", None):
        a.root = "."
    if not hasattr(a, "state_dir"):
        a.state_dir = None
    a.func(a)


if __name__ == "__main__":
    main()
