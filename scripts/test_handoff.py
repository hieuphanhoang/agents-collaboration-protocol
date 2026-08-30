#!/usr/bin/env python3
"""
Regression suite for handoff.py. Run with `handoff.py test` or directly.

Covers the cases that have actually bitten: legacy Unicode headers, year
boundaries, an edit landing between a read and its write, who the index says
owes a reply, impossible timestamps, a status field emptied by hand, init run
from the copy installed in a repo, instruction-file registration, relay
stamping, ignored handoff state, and index completeness.
Stdlib only, no pytest.
"""
import argparse
import datetime
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CLI = HERE / "handoff.py"
PASS, FAIL = [], []


def run(root, *args, expect_ok=True, stdin_text=None):
    r = subprocess.run([sys.executable, str(CLI), "--root", str(root), *args],
                       capture_output=True, text=True, input=stdin_text)
    if expect_ok and r.returncode != 0:
        raise AssertionError(f"{' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  <- {detail}" if not cond and detail else ""))


def fresh():
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-test-"))
    run(d, "init")
    return d


def meta(root, name, state=".handoff"):
    return root / state / name


def logs(root, state=".handoff"):
    return root / state / "threads"


def write_legacy_state(root, state=".handoff"):
    base = root / state
    old_threads = base / "chat_logs"
    old_threads.mkdir(parents=True)
    (base / "CHATLOG.md").write_text("""# CHATLOG

## Awaiting owner
<!-- handoff:awaiting:start -->
| ID | Decision or approval | Since |
|---|---|---|
| - | *nothing waiting on you* | |
<!-- handoff:awaiting:end -->

## Open threads
<!-- handoff:open:start -->
| ID | Subject | Owes a reply | Since |
|---|---|---|---|
| [`AGENT-001`](chat_logs/AGENT-001-legacy-layout.md) | Legacy layout | Codex | 01-01 12:00 |
<!-- handoff:open:end -->

## Conversation history

| Time | Speaker | Thread | Note |
|---|---|---|---|
| 01-01 12:00 | Opus | AGENT-001 | opened from the old chat_logs path |

## All messages
<!-- handoff:threads:start -->
| ID | Subject | From -> To | Type | Status | Last |
|---|---|---|---|---|---|
| [`AGENT-001`](chat_logs/AGENT-001-legacy-layout.md) | Legacy layout | Opus -> Codex | QUESTION | open | 01-01 12:00 |
<!-- handoff:threads:end -->
""", encoding="utf-8")
    (base / "ROSTER.md").write_text("""# ROSTER

## Members

| Name | Model / harness | File access | Owns | Reads instructions from |
|---|---|---|---|---|
| Owner | human | direct | final say | - |
| Opus | Claude | direct | docs | AGENTS.md |
| Codex | GPT | direct | scripts | AGENTS.md |
""", encoding="utf-8")
    (base / "PROTOCOL.md").write_text(
        "Members read .handoff/CHATLOG.md and write .handoff/chat_logs/.\n",
        encoding="utf-8")
    (base / "CONTRIBUTING.md").write_text(
        "Decisions about work go in chat_logs/ and CHATLOG.md indexes them.\n",
        encoding="utf-8")
    (old_threads / "AGENT-001-legacy-layout.md").write_text("""# `AGENT-001` - Legacy layout

| | |
|---|---|
| **From -> To** | Opus -> Codex |
| **Type** | QUESTION |
| **Status** | open |
| **Latest** | Opus, 01-01 12:00 (1 comments) |
| **Updated** | 2026-01-01 12:00 |
| **Time** | 2026-01-01 12:00 |

---

**[Opus, 0101, 1200]**

Written before the storage rename.
""", encoding="utf-8")


# ------------------------------------------------------------------ tests
def t_init():
    d = fresh()
    try:
        for f in ("PROTOCOL.md", "INDEX.md", "ROSTER.md", "CONTRIBUTING.md"):
            check(f"init writes .handoff/{f}", meta(d, f).exists())
        check("init creates .handoff/threads/", logs(d).is_dir())
        check("bare init leaves root instruction files alone",
              not (d / "AGENTS.md").exists() and not (d / "CLAUDE.md").exists())
        check("init leaves no root-level protocol files",
              not any((d / f).exists()
                      for f in ("PROTOCOL.md", "INDEX.md", "ROSTER.md",
                                "CONTRIBUTING.md", "threads")))
        body = meta(d, "INDEX.md").read_text(encoding="utf-8")
        for blk in ("awaiting", "open", "threads"):
            check(f"template has '{blk}' marker block",
                  f"<!-- handoff:{blk}:start -->" in body)
        check("template has an Open threads section", "## Open threads" in body)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_init_ships_the_tool():
    """A member without the skill folder must still be able to run the tool."""
    d = fresh()
    try:
        tool = d / ".handoff" / "handoff.py"
        check("init installs the CLI into the repo", tool.is_file())
        check("the installed copy is byte-identical",
              tool.read_bytes() == CLI.read_bytes())
        check("its test suite comes along",
              (d / ".handoff" / "test_handoff.py").is_file())
        r = subprocess.run([sys.executable, str(tool), "--root", str(d), "doctor"],
                           capture_output=True, text=True)
        check("the installed copy runs", r.returncode == 0, r.stdout + r.stderr)

        # Re-running must not duplicate the section or clobber what is there.
        (d / "AGENTS.md").write_text("# Mine\n\nkeep this\n", encoding="utf-8")
        run(d, "init")
        ag2 = (d / "AGENTS.md").read_text(encoding="utf-8")
        check("re-init preserves existing AGENTS.md content", "keep this" in ag2)
        check("init points AGENTS.md at the protocol", "PROTOCOL.md" in ag2)
        check("AGENTS.md points at .handoff/PROTOCOL.md", ".handoff/PROTOCOL.md" in ag2)
        check("AGENTS.md names the in-repo tool", ".handoff/handoff.py" in ag2)
        check("AGENTS.md tells members to pass their own name to summary",
              "summary <you>" in ag2)
        run(d, "init")
        ag3 = (d / "AGENTS.md").read_text(encoding="utf-8")
        check("re-init does not duplicate the pointer section",
              ag3.count("## Multi-agent protocol") == 1)

        e = pathlib.Path(tempfile.mkdtemp(prefix="handoff-noag-"))
        try:
            run(e, "init", "--no-agents-md")
            check("--no-agents-md leaves AGENTS.md alone", not (e / "AGENTS.md").exists())
        finally:
            shutil.rmtree(e, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_init_registers_existing_instruction_files_once():
    """
    Root instruction files are registration hooks, not ongoing handoff state.

    A project may already have AGENTS.md, CLAUDE.md, both, or neither. init
    should point existing harness files at the state folder once, then leave
    them alone; the mutable handoff work belongs under .handoff/.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-existing-instructions-"))
    try:
        (d / "AGENTS.md").write_text("# Agents\n\nkeep agents\n", encoding="utf-8")
        (d / "CLAUDE.md").write_text("# Claude\n\nkeep claude\n", encoding="utf-8")
        run(d, "init")

        ag = (d / "AGENTS.md").read_text(encoding="utf-8")
        cl = (d / "CLAUDE.md").read_text(encoding="utf-8")
        check("init registers an existing AGENTS.md", ".handoff/PROTOCOL.md" in ag)
        check("init registers an existing CLAUDE.md", ".handoff/PROTOCOL.md" in cl)
        check("registration preserves AGENTS.md content", "keep agents" in ag)
        check("registration preserves CLAUDE.md content", "keep claude" in cl)

        before = {name: (d / name).read_text(encoding="utf-8")
                  for name in ("AGENTS.md", "CLAUDE.md")}
        run(d, "init")
        run(d, "new", "After register", "--frm", "Opus", "--to", "Codex",
            "--body", "x")
        run(d, "reply", "AGENT-001", "--frm", "Codex", "--body", "y",
            "--status", "answered")
        run(d, "sync")
        after = {name: (d / name).read_text(encoding="utf-8")
                 for name in ("AGENTS.md", "CLAUDE.md")}
        check("handoff commands do not touch registered instruction files",
              before == after)

        e = pathlib.Path(tempfile.mkdtemp(prefix="handoff-no-instructions-"))
        try:
            run(e, "init", "--no-instructions")
            check("--no-instructions leaves root instruction files alone",
                  not (e / "AGENTS.md").exists() and not (e / "CLAUDE.md").exists())
        finally:
            shutil.rmtree(e, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_init_can_use_custom_state_dir():
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-custom-state-"))
    custom = ".team-handoff"
    try:
        (d / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        run(d, "init", "--state-dir", custom)
        check("init can write state under a custom directory",
              meta(d, "INDEX.md", custom).is_file())
        check("custom init does not also create .handoff", not (d / ".handoff").exists())
        ag = (d / "AGENTS.md").read_text(encoding="utf-8")
        check("registration points at custom PROTOCOL.md",
              f"{custom}/PROTOCOL.md" in ag)
        check("registration names custom handoff.py",
              f"{custom}/handoff.py" in ag)
        run(d, "new", "Custom state", "--frm", "Opus", "--to", "Codex",
            "--body", "x", "--state-dir", custom)
        run(d, "reply", "AGENT-001", "--frm", "Codex", "--body", "y",
            "--status", "answered", "--state-dir", custom)
        check("commands work against custom state when explicit",
              bool(list(logs(d, custom).glob("AGENT-001-*.md"))))
        out = run(d, "summary", "Opus", "--state-dir", custom).stdout
        check("summary works against custom state",
              "YOURS (Opus): 1 thread(s)" in out, out)
        run(d, "doctor", "--state-dir", custom)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_migrate_legacy_storage():
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-legacy-storage-"))
    try:
        write_legacy_state(d)

        r = run(d, "summary", expect_ok=False)
        check("commands refuse legacy storage before migration",
              r.returncode != 0 and "handoff migrate" in r.stderr,
              r.stdout + r.stderr)

        r = run(d, "doctor", expect_ok=False)
        check("doctor reports legacy storage",
              r.returncode != 0 and "legacy handoff storage" in r.stdout,
              r.stdout + r.stderr)

        run(d, "migrate")
        check("migrate renames CHATLOG.md to INDEX.md",
              meta(d, "INDEX.md").is_file() and not meta(d, "CHATLOG.md").exists())
        check("migrate renames chat_logs to threads",
              logs(d).is_dir() and not (d / ".handoff" / "chat_logs").exists())
        check("migrated thread file is preserved",
              (logs(d) / "AGENT-001-legacy-layout.md").is_file())

        body = meta(d, "INDEX.md").read_text(encoding="utf-8")
        check("migrate rewrites index links",
              "threads/AGENT-001-legacy-layout.md" in body and "chat_logs/" not in body,
              body)
        proto = meta(d, "PROTOCOL.md").read_text(encoding="utf-8")
        contrib = meta(d, "CONTRIBUTING.md").read_text(encoding="utf-8")
        check("migrate rewrites state docs",
              "INDEX.md" in proto and "threads/" in proto
              and "INDEX.md" in contrib and "threads/" in contrib,
              proto + contrib)

        r = run(d, "doctor")
        check("doctor accepts migrated storage", r.returncode == 0, r.stdout + r.stderr)
        out = run(d, "summary", "Codex").stdout
        check("summary reads migrated threads",
              "YOURS (Codex): 1 thread(s)" in out and "AGENT-001" in out,
              out)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_migrate_refuses_split_storage():
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-split-storage-"))
    try:
        write_legacy_state(d)
        meta(d, "INDEX.md").write_text("new index\n", encoding="utf-8")
        logs(d).mkdir()
        r = run(d, "migrate", expect_ok=False)
        check("migrate refuses to overwrite current storage",
              r.returncode != 0 and "cannot migrate" in r.stderr,
              r.stdout + r.stderr)
        check("migrate leaves legacy index untouched on conflict",
              meta(d, "CHATLOG.md").is_file())
        check("migrate leaves legacy threads untouched on conflict",
              (d / ".handoff" / "chat_logs" / "AGENT-001-legacy-layout.md").is_file())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_state_dir_rejects_unsafe_paths():
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-bad-state-"))
    try:
        for label, bad in [("parent segment", "../evil"),
                           ("absolute path", str(d / "outside"))]:
            r = run(d, "init", "--state-dir", bad, expect_ok=False)
            check(f"state dir rejects {label}", r.returncode != 0)
            check(f"state dir {label} failure is clean",
                  "safe relative path" in r.stderr and "Traceback" not in r.stderr,
                  r.stdout + r.stderr)
        check("unsafe state dirs do not create parent output",
              not (d.parent / "evil").exists())
        check("unsafe state dirs do not create absolute output",
              not (d / "outside").exists())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_init_ignores_vendor_directories():
    """
    .claude/ and .agents/ get no special treatment - not even avoidance logic.

    init always writes .handoff/ and never reads or writes anything under a
    vendor directory. This is a narrower claim than the old special-casing
    tests made (there is no more branching on these names to test), but the
    one thing worth a permanent regression guard is that init never touches
    another tool's own files sitting in a directory that happens to share a
    dot-prefix convention.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-vendor-dirs-"))
    try:
        (d / ".claude").mkdir()
        (d / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
        (d / ".claude" / "commands").mkdir()
        (d / ".agents").mkdir()
        (d / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
        run(d, "init")
        check("init uses .handoff regardless of .claude/.agents being present",
              (d / ".handoff" / "INDEX.md").is_file())
        check("nothing is written into .claude", not (d / ".claude" / "INDEX.md").exists())
        check("nothing is written into .agents", not (d / ".agents" / "INDEX.md").exists())
        check("an unrelated file already in .claude is untouched",
              (d / ".claude" / "settings.json").read_text(encoding="utf-8") == "{}")
        check("an unrelated directory already in .claude is untouched",
              (d / ".claude" / "commands").is_dir())
        cl = (d / "CLAUDE.md").read_text(encoding="utf-8")
        check("CLAUDE.md registration names .handoff", ".handoff/" in cl)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_init_needs_the_skill_folder():
    """
    The copy installed at .handoff/handoff.py ships no templates, so its init
    cannot work. It used to die part-way through scaffolding with a bare
    FileNotFoundError - the least useful thing to hand the one member who has no
    skill folder to compare against, and it left a half-built repo behind.
    """
    d = fresh()
    e = pathlib.Path(tempfile.mkdtemp(prefix="handoff-target-"))
    try:
        tool = d / ".handoff" / "handoff.py"
        r = subprocess.run([sys.executable, str(tool), "--root", str(e), "init"],
                           capture_output=True, text=True)
        check("init from the installed copy fails", r.returncode != 0)
        check("it explains rather than raising", "Traceback" not in r.stderr, r.stderr)
        check("it points at the skill checkout", "skill" in r.stderr.lower(), r.stderr)
        check("it scaffolds nothing before giving up",
              not (e / ".handoff" / "threads").exists()
              and not (e / ".handoff" / "PROTOCOL.md").exists())
        check("every other subcommand still runs from the installed copy",
              subprocess.run([sys.executable, str(tool), "--root", str(d), "doctor"],
                             capture_output=True, text=True).returncode == 0)
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(e, ignore_errors=True)


def t_init_inside_skill_skips_installed_copy():
    """
    The skill repo can dogfood the protocol without creating a second CLI copy.

    The authoritative tool is already scripts/handoff.py. Installing another
    copy under .handoff/ would give this repo two CLIs that can drift apart.
    """
    source = HERE.parent
    d = pathlib.Path(tempfile.mkdtemp(prefix="handoff-skill-"))
    try:
        skill = d / "multi-agent-collaboration-protocol"
        skill.mkdir()
        for name in ("SKILL.md", "README.md"):
            shutil.copy2(source / name, skill / name)
        for name in ("scripts", "assets", "references"):
            shutil.copytree(source / name, skill / name)
        tool = skill / "scripts" / "handoff.py"
        r = subprocess.run([sys.executable, str(tool), "--root", str(skill), "init"],
                           capture_output=True, text=True)
        check("self-init succeeds in the skill checkout", r.returncode == 0,
              r.stdout + r.stderr)
        check("self-init writes the log scaffold", meta(skill, "INDEX.md").is_file())
        proto = meta(skill, "PROTOCOL.md").read_text(encoding="utf-8")
        check("self-init writes a protocol pointer", "references/protocol.md" in proto)
        check("self-init avoids a duplicate protocol copy",
              proto != (skill / "references" / "protocol.md").read_text(encoding="utf-8"))
        check("self-init skips a duplicate installed CLI",
              not (skill / ".handoff" / "handoff.py").exists(), r.stdout)
        check("self-init tells members which CLI to use",
              "use scripts/handoff.py here" in r.stdout, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_body_input():
    """Long or quoted comments must not have to survive a shell."""
    d = fresh()
    try:
        awkward = 'He said "run `git log --oneline | head -3`" -- then $PATH broke.\n\nTwo paragraphs.'
        f = d / "msg.md"
        f.write_text(awkward, encoding="utf-8")
        run(d, "new", "Quoting", "--frm", "Opus", "--to", "Codex", "--body-file", str(f))
        th = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")
        check("--body-file lands verbatim", awkward in th, th[-300:])

        run(d, "reply", "AGENT-001", "--frm", "Codex", "--body-stdin",
            stdin_text="from stdin, with 'quotes' and | pipes")
        th = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")
        check("--body-stdin lands verbatim", "with 'quotes' and | pipes" in th)

        r = run(d, "reply", "AGENT-001", "--frm", "Codex", "--body", "a",
                "--body-file", str(f), expect_ok=False)
        check("two body sources are refused", r.returncode != 0)
        r = run(d, "reply", "AGENT-001", "--frm", "Codex", expect_ok=False)
        check("a reply with no body is refused", r.returncode != 0)
        r = run(d, "reply", "AGENT-001", "--frm", "Codex", "--body-file",
                str(d / "nope.md"), expect_ok=False)
        check("a missing body file is refused", r.returncode != 0)

        r = run(d, "new", "Bad type", "--frm", "Opus", "--to", "Codex",
                "--type", "MUSING", "--body", "x", expect_ok=False)
        check("an unknown thread type is refused", r.returncode != 0, r.stdout + r.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_summary():
    d = fresh()
    try:
        run(d, "new", "Retry budget", "--frm", "Opus", "--to", "Codex", "--body", "x")
        run(d, "new", "Buy a licence", "--frm", "Opus", "--to", "Owner",
            "--ask", "--type", "REQUEST", "--body", "y")
        out = run(d, "summary").stdout
        check("summary separates owner items", "AWAITING THE OWNER (1)" in out, out)
        check("summary lists member threads", "BETWEEN MEMBERS (1)" in out, out)
        check("summary says who each thread waits on", "waiting on Codex" in out, out)
        mine = run(d, "summary", "Codex").stdout
        check("summary can answer 'what is waiting on me'",
              "YOURS (Codex): 1 thread(s)" in mine, mine)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_waiting_alias():
    d = fresh()
    try:
        run(d, "new", "Retry budget", "--frm", "Opus", "--to", "Codex", "--body", "x")
        summary = run(d, "summary", "Codex").stdout
        waiting = run(d, "waiting", "Codex", expect_ok=False)
        check("waiting <member> succeeds", waiting.returncode == 0,
              waiting.stdout + waiting.stderr)
        check("waiting <member> matches summary <member>",
              waiting.stdout == summary, waiting.stdout)
        missing = run(d, "waiting", expect_ok=False)
        check("waiting requires a member argument",
              missing.returncode != 0
              and "the following arguments are required: member" in missing.stderr,
              missing.stdout + missing.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_missing_promotion_refuses_without_write():
    d = fresh()
    try:
        run(d, "new", "Cache contract", "--frm", "Opus", "--to", "Codex", "--body", "x")
        p = next(logs(d).glob("AGENT-001-*.md"))
        before = p.read_text(encoding="utf-8")

        r = run(d, "close", "AGENT-001", "--frm", "Codex",
                "--promoted-to", "missing.md", expect_ok=False)

        after = p.read_text(encoding="utf-8")
        check("close refuses a missing promoted path", r.returncode != 0, r.stdout + r.stderr)
        check("close names the missing promoted path", "missing.md" in r.stderr,
              r.stdout + r.stderr)
        check("close writes nothing when promoted path is missing", after == before)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_stale_promotion_refuses_without_write():
    d = fresh()
    try:
        run(d, "new", "Cache contract", "--frm", "Opus", "--to", "Codex", "--body", "x")
        promoted = d / "contract.md"
        promoted.write_text("old contract\n", encoding="utf-8")
        old = datetime.datetime(2000, 1, 1, 0, 0).timestamp()
        os.utime(promoted, (old, old))
        p = next(logs(d).glob("AGENT-001-*.md"))
        before = p.read_text(encoding="utf-8")

        r = run(d, "close", "AGENT-001", "--frm", "Codex",
                "--promoted-to", "contract.md", expect_ok=False)

        after = p.read_text(encoding="utf-8")
        check("close refuses a stale promoted path", r.returncode != 0,
              r.stdout + r.stderr)
        check("close names the stale promoted path", "contract.md" in r.stderr,
              r.stdout + r.stderr)
        check("close writes nothing when promoted path is stale", after == before)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_succeeds_with_fresh_promotion():
    d = fresh()
    try:
        run(d, "new", "Cache contract", "--frm", "Opus", "--to", "Codex", "--body", "x")
        promoted = d / "contract.md"
        promoted.write_text("new contract\n", encoding="utf-8")

        run(d, "close", "AGENT-001", "--frm", "Codex",
            "--promoted-to", "contract.md")

        thread = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")
        log = meta(d, "INDEX.md").read_text(encoding="utf-8")
        check("close sets status to closed", "| **Status** | closed |" in thread, thread)
        check("close appends a closing comment", "[Codex," in thread and "contract.md" in thread,
              thread)
        check("close comment says recency is not relevance proof",
              "recency check only" in thread, thread)
        check("close sync reflects closed status",
              "AGENT-001" in log and "| closed |" in log, log)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_allows_answered_and_blocked_threads():
    d = fresh()
    try:
        for status in ("answered", "blocked"):
            run(d, "new", f"Live {status}", "--frm", "Opus", "--to", "Codex",
                "--body", "x")
            tid = f"AGENT-{len(list(logs(d).glob('AGENT-*.md'))):03d}"
            run(d, "reply", tid, "--frm", "Codex", "--body", status,
                "--status", status)
            promoted = d / f"{status}.md"
            promoted.write_text(status, encoding="utf-8")

            run(d, "close", tid, "--frm", "Codex", "--promoted-to", promoted.name)

            thread = next(logs(d).glob(f"{tid}-*.md")).read_text(encoding="utf-8")
            check(f"close allows {status} thread",
                  "| **Status** | closed |" in thread and promoted.name in thread,
                  thread)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_accepts_file_changed_before_report_comment():
    d = fresh()
    try:
        run(d, "new", "Cache contract", "--frm", "Opus", "--to", "Codex", "--body", "x")
        p = next(logs(d).glob("AGENT-001-*.md"))
        text = p.read_text(encoding="utf-8")
        created = next(l for l in text.splitlines() if "**Time**" in l)
        base = datetime.datetime.strptime(created.split("|")[2].strip(),
                                          "%Y-%m-%d %H:%M")

        promoted = d / "contract.md"
        promoted.write_text("new contract\n", encoding="utf-8")
        promoted_at = (base + datetime.timedelta(minutes=1)).timestamp()
        os.utime(promoted, (promoted_at, promoted_at))

        # Normal workflow: the file changes during the thread, then the member's
        # final report comment lands after the file edit. close must compare
        # against thread creation, not the latest report comment.
        report_time = base + datetime.timedelta(minutes=2)
        p.write_text(text.rstrip() +
                     f"\n\n---\n\n**[Codex, {report_time.strftime('%d%m')}, "
                     f"{report_time.strftime('%H%M')}]**\n\nimplemented\n",
                     encoding="utf-8")

        run(d, "close", "AGENT-001", "--frm", "Codex",
            "--promoted-to", "contract.md")

        thread = p.read_text(encoding="utf-8")
        check("close accepts file changed before final report comment",
              "| **Status** | closed |" in thread and "contract.md" in thread,
              thread)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_requires_all_promoted_paths_fresh():
    d = fresh()
    try:
        run(d, "new", "Cache contract", "--frm", "Opus", "--to", "Codex", "--body", "x")
        fresh_path = d / "fresh.md"
        fresh_path.write_text("fresh\n", encoding="utf-8")
        stale_path = d / "stale.md"
        stale_path.write_text("stale\n", encoding="utf-8")
        old = datetime.datetime(2000, 1, 1, 0, 0).timestamp()
        os.utime(stale_path, (old, old))
        p = next(logs(d).glob("AGENT-001-*.md"))
        before = p.read_text(encoding="utf-8")

        r = run(d, "close", "AGENT-001", "--frm", "Codex",
                "--promoted-to", "fresh.md", "stale.md", expect_ok=False)

        after = p.read_text(encoding="utf-8")
        check("close refuses when any promoted path is stale", r.returncode != 0,
              r.stdout + r.stderr)
        check("close is all-or-nothing across promoted paths", after == before)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_rejects_unsafe_promoted_paths():
    d = fresh()
    try:
        run(d, "new", "Cache contract", "--frm", "Opus", "--to", "Codex", "--body", "x")
        p = next(logs(d).glob("AGENT-001-*.md"))
        before = p.read_text(encoding="utf-8")

        for bad in ("..", "../outside.md", ".", str(d / "contract.md")):
            r = run(d, "close", "AGENT-001", "--frm", "Codex",
                    "--promoted-to", bad, expect_ok=False)
            check(f"close rejects unsafe promoted path {bad!r}",
                  r.returncode != 0 and "unsafe promoted path" in r.stderr,
                  r.stdout + r.stderr)

        after = p.read_text(encoding="utf-8")
        check("close writes nothing for unsafe promoted paths", after == before)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_refuses_terminal_threads():
    d = fresh()
    try:
        for status in ("closed", "withdrawn", "superseded"):
            run(d, "new", f"Terminal {status}", "--frm", "Opus", "--to", "Codex",
                "--body", "x")
            tid = f"AGENT-{len(list(logs(d).glob('AGENT-*.md'))):03d}"
            run(d, "reply", tid, "--frm", "Codex", "--body", "terminal",
                "--status", status)
            promoted = d / f"{status}.md"
            promoted.write_text(status, encoding="utf-8")

            r = run(d, "close", tid, "--frm", "Codex",
                    "--promoted-to", promoted.name, expect_ok=False)

            check(f"close refuses already {status} thread",
                  r.returncode != 0 and "already terminal" in r.stderr,
                  r.stdout + r.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_close_does_not_replace_reply_closed():
    d = fresh()
    try:
        run(d, "new", "Manual close", "--frm", "Opus", "--to", "Codex", "--body", "x")
        run(d, "reply", "AGENT-001", "--frm", "Codex", "--body", "checked manually",
            "--status", "closed")
        thread = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")

        check("reply --status closed still works",
              "| **Status** | closed |" in thread and "checked manually" in thread,
              thread)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_history_nudge():
    """Conversation history is hand-written, so doctor nudges rather than fails."""
    d = fresh()
    try:
        run(d, "new", "Cache key", "--frm", "Opus", "--to", "Codex", "--body", "x")
        r = run(d, "doctor")
        check("an unwritten history row is only a note", r.returncode == 0, r.stdout)
        check("doctor names the section", "Conversation history" in r.stdout, r.stdout)
        th = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")
        updated = next(l for l in th.splitlines() if "**Updated**" in l)
        row_time = datetime.datetime.strptime(updated.split("|")[2].strip(),
                                              "%Y-%m-%d %H:%M").strftime("%d-%m %H:%M")
        log = meta(d, "INDEX.md")
        log.write_text(log.read_text(encoding="utf-8").replace(
            "| | | | |",
            f"| {row_time} | Opus | AGENT-001 | asked who owns the cache key |"),
            encoding="utf-8")
        r = run(d, "doctor")
        check("a written row clears the nudge",
              "Conversation history" not in r.stdout, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_history_stale_across_year_boundary():
    """A mentioned thread can still be newer than the hand-written history."""
    d = fresh()
    try:
        p = logs(d) / "AGENT-001-rollover.md"
        p.write_text("""# `AGENT-001` - Rollover

| | |
|---|---|
| **From -> To** | Opus -> Codex |
| **Type** | QUESTION |
| **Status** | open |
| **Time** | 2026-12-31 23:55 |

---

**[Opus, 3112, 2355]**

December.

---

**[Codex, 0101, 0005]**

January, the following year.
""", encoding="utf-8")
        run(d, "sync")
        log = meta(d, "INDEX.md")
        log.write_text(log.read_text(encoding="utf-8").replace(
            "| | | | |",
            "| 31-12 23:59 | Codex | AGENT-001 | mentioned but stale |"),
            encoding="utf-8")

        r = run(d, "doctor")
        check("a stale history row is only a note", r.returncode == 0, r.stdout)
        check("doctor notes stale Conversation history",
              "older than latest thread activity" in r.stdout, r.stdout)

        log.write_text(log.read_text(encoding="utf-8").replace(
            "| 31-12 23:59 | Codex | AGENT-001 | mentioned but stale |",
            "| 01-01 00:05 | Codex | AGENT-001 | current |"),
            encoding="utf-8")
        r = run(d, "doctor")
        check("a current history row clears the stale note",
              "older than latest thread activity" not in r.stdout, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_doctor_notes_ignored_log():
    """A log hidden by .gitignore will disappear from a fresh clone."""
    d = fresh()
    try:
        (d / ".gitignore").write_text(".handoff/\n", encoding="utf-8")
        r = run(d, "doctor")
        check("doctor notes when .gitignore hides handoff state",
              "ignore handoff state" in r.stdout, r.stdout)
        check("the ignored-log note is non-fatal", r.returncode == 0, r.stdout)

        (d / ".gitignore").write_text(".handoff/handoff.py\n"
                                      ".handoff/test_handoff.py\n",
                                      encoding="utf-8")
        r = run(d, "doctor")
        check("ignoring only installed CLI copies is accepted",
              "ignore handoff state" not in r.stdout, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_doctor_notes_unknown_roster_participants():
    """Thread participants should match ROSTER.md member names exactly."""
    d = fresh()
    try:
        meta(d, "ROSTER.md").write_text("""# ROSTER

## Members

| Name | Model / harness | File access | Owns | Reads instructions from |
|---|---|---|---|---|
| Owner | human | direct | final say | - |
| Opus | Claude | direct | docs | AGENTS.md |
| Codex | GPT | direct | scripts | AGENTS.md |

## Shared, jointly owned

| Path | Purpose | Change rule |
|---|---|---|
| INDEX.md | index | shared |
""", encoding="utf-8")
        run(d, "new", "Known", "--frm", "Opus", "--to", "Codex", "--body", "x")
        r = run(d, "doctor")
        check("known roster participants do not produce a roster note",
              "not listed in ROSTER.md" not in r.stdout, r.stdout)

        run(d, "new", "Unknown", "--frm", "Opus", "--to", "Codex CLI", "--body", "x")
        r = run(d, "doctor")
        check("unknown roster participant is only a note", r.returncode == 0, r.stdout)
        check("doctor notes unknown roster participant",
              "Codex CLI" in r.stdout and "not listed in ROSTER.md" in r.stdout,
              r.stdout)

        run(d, "reply", "AGENT-001", "--frm", "Sol", "--body", "relayed")
        r = run(d, "doctor")
        check("doctor also checks comment authors against roster",
              "Sol" in r.stdout and "not listed in ROSTER.md" in r.stdout,
              r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_doctor_skips_unfilled_roster_template():
    """A fresh init roster is placeholders only, so there is nothing to validate yet."""
    d = fresh()
    try:
        run(d, "new", "Fresh roster", "--frm", "Opus", "--to", "Codex", "--body", "x")
        r = run(d, "doctor")
        check("unfilled roster template does not produce roster notes",
              "not listed in ROSTER.md" not in r.stdout, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_roundtrip():
    d = fresh()
    try:
        run(d, "new", "Cache key", "--frm", "Opus", "--to", "Sol", "--body", "hash or query?")
        run(d, "reply", "AGENT-001", "--frm", "Sol", "--body", "query", "--status", "answered")
        log = meta(d, "INDEX.md").read_text(encoding="utf-8")
        check("thread appears in index", "AGENT-001" in log)
        check("recipient parsed, not '?'", "Opus -> Sol" in log, log)
        check("open-thread block lists who owes a reply", "Sol" in log)
        th = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")
        check("status updated in thread", "| **Status** | answered |" in th)
        check("Updated header maintained", "| **Updated** |" in th)
        check("both speakers stamped", "[Opus," in th and "[Sol," in th)
        run(d, "doctor")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_unicode_legacy():
    """A repo written by another agent using Unicode arrows and middle dots."""
    d = fresh()
    try:
        p = logs(d) / "AGENT-001-legacy.md"
        p.write_text("""# `AGENT-001` · Legacy thread

| | |
|---|---|
| **From → To** | Opus → Sol |
| **Type** | QUESTION |
| **Status** | open |
| **Time** | 2026-08-24 23:45 +0700 |

---

**[Opus, 2408, 2345]**

Written by a different agent, with Unicode punctuation.
""", encoding="utf-8")
        run(d, "sync")
        log = meta(d, "INDEX.md").read_text(encoding="utf-8")
        check("Unicode 'From -> To' header is read", "Opus -> Sol" in log, log)
        check("no '?' recipient from Unicode header", "| ? |" not in log)
        check("Unicode title parsed without the id prefix", "Legacy thread" in log)
        r = run(d, "doctor", expect_ok=False)
        check("doctor accepts a valid Unicode thread", r.returncode == 0, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_year_boundary():
    d = fresh()
    try:
        p = logs(d) / "AGENT-001-rollover.md"
        p.write_text("""# `AGENT-001` - Rollover

| | |
|---|---|
| **From -> To** | Opus -> Sol |
| **Type** | QUESTION |
| **Status** | open |
| **Time** | 2026-12-30 10:00 |

---

**[Opus, 3012, 1000]**

December.

---

**[Sol, 0201, 0900]**

January, the following year.
""", encoding="utf-8")
        run(d, "sync")
        th = p.read_text(encoding="utf-8")
        check("January stamp resolves to the next year",
              "| **Updated** | 2027-01-02 09:00 |" in th,
              [l for l in th.splitlines() if "Updated" in l])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_sort_across_years():
    d = fresh()
    try:
        for i, (tid, time, ddmm) in enumerate([
                ("AGENT-001", "2026-12-30 10:00", "3012"),
                ("AGENT-002", "2027-01-05 10:00", "0501")]):
            (logs(d) / f"{tid}-t{i}.md").write_text(
                f"""# `{tid}` - Thread {i}

| | |
|---|---|
| **From -> To** | Opus -> Sol |
| **Type** | QUESTION |
| **Status** | open |
| **Time** | {time} |

---

**[Opus, {ddmm}, 1000]**

body
""", encoding="utf-8")
        run(d, "sync")
        log = meta(d, "INDEX.md").read_text(encoding="utf-8")
        rows = [l for l in log.splitlines() if l.startswith("| [`AGENT-")]
        first = rows[0] if rows else ""
        check("2027 thread sorts above 2026 thread", "AGENT-002" in first, first)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_external_edit():
    """An edit already on disk when reply starts must survive it."""
    d = fresh()
    try:
        run(d, "new", "Race", "--frm", "Opus", "--to", "Sol", "--body", "x")
        p = next(logs(d).glob("AGENT-001-*.md"))
        p.write_text(p.read_text(encoding="utf-8") +
                     "\n\n---\n\n**[IKN, 0101, 0101]**\n\nowner edit\n", encoding="utf-8")
        run(d, "reply", "AGENT-001", "--frm", "Sol", "--body", "mine")
        after = p.read_text(encoding="utf-8")
        check("reply appends after an edit already on disk", "owner edit" in after)
        check("reply's own comment lands too", "mine" in after)
        check("atomic write leaves no .handoff-tmp files",
              not list(logs(d).glob("*.handoff-tmp")))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_concurrent():
    """
    reply must refuse to clobber an edit that lands *after* it read the file.

    This is the case the guard exists for and the only one that distinguishes a
    real check from a decorative one, so it has to be driven in-process: the edit
    is injected in the window between read_threads returning and the write.
    """
    d = fresh()
    try:
        run(d, "new", "Race", "--frm", "Opus", "--to", "Sol", "--body", "x")
        p = next(logs(d).glob("AGENT-001-*.md"))
        sys.path.insert(0, str(HERE))
        import handoff

        real, fired = handoff.read_threads, []

        def racing(root, requested=None):
            try:
                ts = real(root, requested)
            except TypeError:
                ts = real(root)
            if not fired:                      # only the first read races
                fired.append(True)
                p.write_text(p.read_text(encoding="utf-8") +
                             "\n\n---\n\n**[IKN, 0101, 0101]**\n\nowner edit\n",
                             encoding="utf-8")
            return ts

        handoff.read_threads = racing
        args = argparse.Namespace(root=str(d), id="AGENT-001", frm="Sol",
                                  body="stale reply", status=None, source_time=None,
                                  state_dir=None)
        try:
            handoff.cmd_reply(args)
            refused = False
        except SystemExit:
            refused = True
        finally:
            handoff.read_threads = real

        after = p.read_text(encoding="utf-8")
        check("reply refuses to write over an edit that landed after its read", refused)
        check("the racing edit survives", "owner edit" in after)
        check("the stale reply is not written", "stale reply" not in after)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_owes_reply():
    """The index must point at whoever owes the next turn, not at the opener."""
    d = fresh()
    try:
        run(d, "new", "Cache key", "--frm", "Opus", "--to", "Sol", "--body", "hash or query?")
        log = meta(d, "INDEX.md")

        def open_block():
            b = log.read_text(encoding="utf-8")
            return b[b.index("handoff:open:start"):b.index("handoff:open:end")]

        check("a fresh thread waits on the recipient", "| Sol |" in open_block(),
              open_block())
        run(d, "reply", "AGENT-001", "--frm", "Sol", "--body", "query",
            "--status", "answered")
        check("after the recipient answers, the opener owes the turn",
              "| Opus |" in open_block(), open_block())
        run(d, "reply", "AGENT-001", "--frm", "Opus", "--body", "why?")
        check("and it hands back again on the next comment",
              "| Sol |" in open_block(), open_block())
        run(d, "reply", "AGENT-001", "--frm", "Grok", "--body", "passing thought")
        check("a relayed third party does not take on the debt",
              "| Sol |" in open_block(), open_block())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_relay_stamping():
    d = fresh()
    try:
        run(d, "new", "Retry budget", "--frm", "Sol", "--to", "Opus", "--body", "burn")
        b = d / "brief.txt"
        run(d, "brief", "Grok", "--out", str(b))
        txt = b.read_text(encoding="utf-8")
        check("briefing tells the relay member not to stamp",
              "Do not write a timestamp" in txt)
        check("briefing contains no pre-filled stamp for the member",
              "[Grok," not in txt, txt[-400:])
        check("briefing asks them to flag unverifiable claims",
              "have not seen" in txt)
        run(d, "reply", "AGENT-001", "--frm", "Grok", "--body", "cap it",
            "--source-time", "yesterday 14:00")
        th = next(logs(d).glob("AGENT-001-*.md")).read_text(encoding="utf-8")
        check("relayed reply is attributed to the speaker", "[Grok," in th)
        check("source time recorded alongside receipt stamp",
              "yesterday 14:00" in th and "transcribed on arrival" in th)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_brief_compact_flag():
    d = fresh()
    try:
        run(d, "new", "Retry budget", "--frm", "Sol", "--to", "Opus", "--body", "burn")

        full = d / "full.txt"
        run(d, "brief", "Grok", "--out", str(full))
        full_txt = full.read_text(encoding="utf-8")
        check("default briefing includes the ROSTER dump", "--- ROSTER ---" in full_txt)
        check("default briefing includes the PROTOCOL dump", "--- PROTOCOL ---" in full_txt)

        compact = d / "compact.txt"
        run(d, "brief", "Grok", "--out", str(compact), "--compact")
        compact_txt = compact.read_text(encoding="utf-8")
        check("--compact drops the ROSTER dump", "--- ROSTER ---" not in compact_txt)
        check("--compact drops the PROTOCOL dump", "--- PROTOCOL ---" not in compact_txt)
        check("--compact still includes the open thread",
              "AGENT-001" in compact_txt and "Retry budget" in compact_txt)
        check("--compact still includes the reply-format block",
              "HOW TO REPLY" in compact_txt and "Do not write a timestamp" in compact_txt)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_ask_and_approval():
    d = fresh()
    try:
        run(d, "new", "Approve installing CUDA toolkit", "--frm", "Opus + Sol",
            "--to", "IKN", "--ask", "--type", "REQUEST", "--body", "3-5 GB")
        log = meta(d, "INDEX.md").read_text(encoding="utf-8")
        check("ASK- appears in the awaiting-owner block",
              "ASK-001" in log.split("handoff:awaiting:start")[1].split("handoff:awaiting:end")[0])
        check("awaiting block covers approvals, not just decisions",
              "approval" in log.lower())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_blank_status():
    """
    A Status field emptied by hand must not take the tooling down with it.

    `| **Status** |  |` parses to an empty string, and taking the first word of
    that raised - in every command that reads a thread, doctor included, which
    is the one whose job is to report this kind of damage. The thread must also
    stay listed while it is wrong: a thread that silently drops out of the open
    sections is the failure the index exists to prevent.
    """
    d = fresh()
    try:
        run(d, "new", "Blanked", "--frm", "Opus", "--to", "Sol", "--body", "x")
        f = next(logs(d).glob("AGENT-001-*.md"))
        f.write_text(f.read_text(encoding="utf-8").replace(
            "| **Status** | open |", "| **Status** |  |"), encoding="utf-8")

        for cmd in ("sync", "summary"):
            r = run(d, cmd, expect_ok=False)
            check(f"{cmd} survives a blank status", r.returncode == 0,
                  r.stdout + r.stderr)

        r = run(d, "doctor", expect_ok=False)
        check("doctor survives a blank status", "Traceback" not in r.stderr, r.stderr)
        check("doctor reports the blank status",
              "Status header is empty" in r.stdout, r.stdout)

        run(d, "sync")
        log = meta(d, "INDEX.md").read_text(encoding="utf-8")
        block = (log.split("<!-- handoff:open:start -->")[1]
                    .split("<!-- handoff:open:end -->")[0])
        check("a thread with an unreadable status stays in the open section",
              "AGENT-001" in block, block)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_doctor_catches():
    d = fresh()
    try:
        run(d, "new", "Good", "--frm", "Opus", "--to", "Sol", "--body", "x")
        bad = logs(d) / "AGENT-002-malformed.md"
        bad.write_text("""# `AGENT-002` - Malformed

| | |
|---|---|
| **Type** | QUESTION |
| **Status** | frobnicated |

---

**[Opus, 9999, 9999]**

no From->To header, bogus status, implausible stamp
""", encoding="utf-8")
        r = run(d, "doctor", expect_ok=False)
        o = r.stdout
        check("doctor flags missing required header", "missing required header" in o, o)
        check("doctor flags unknown status", "not one of" in o, o)
        check("doctor flags impossible stamp", "impossible stamp" in o, o)
        check("doctor exits non-zero on problems", r.returncode != 0)

        # The cases hand-written bounds missed: a day past the end of the month,
        # month zero, minute 60. Each is well-formed enough to reach the log and
        # wrong enough to make every other stamp in it untrustworthy.
        for label, stamp in [("day 32", "3212, 1200"), ("month 00", "0100, 1200"),
                             ("minute 60", "0101, 1260"), ("31 Feb", "3102, 1200")]:
            odd = logs(d) / "AGENT-003-odd.md"
            odd.write_text("# `AGENT-003` - Odd\n\n| | |\n|---|---|\n"
                           "| **From -> To** | Opus -> Sol |\n| **Type** | QUESTION |\n"
                           "| **Status** | open |\n| **Time** | 2026-01-01 12:00 |\n\n"
                           f"---\n\n**[Opus, {stamp}]**\n\nbad\n", encoding="utf-8")
            r = run(d, "doctor", expect_ok=False)
            check(f"doctor rejects {label}", "impossible stamp" in r.stdout, r.stdout)
        (logs(d) / "AGENT-003-odd.md").unlink()

        # A header in some other shape is not a comment to any command that reads
        # this file, so doctor has to say so rather than report zero comments.
        shape = logs(d) / "AGENT-004-shape.md"
        shape.write_text("# `AGENT-004` - Shape\n\n| | |\n|---|---|\n"
                         "| **From -> To** | Opus -> Sol |\n| **Type** | QUESTION |\n"
                         "| **Status** | open |\n| **Time** | 2026-01-01 12:00 |\n\n"
                         "---\n\n**[Opus, 1 Jan 2026, 12:00]**\n\nhi\n", encoding="utf-8")
        r = run(d, "doctor", expect_ok=False)
        check("doctor flags a comment header in the wrong shape",
              "not [Name, DDMM, HHMM]" in r.stdout, r.stdout)
        shape.unlink()

        run(d, "sync")
        log = meta(d, "INDEX.md")
        log.write_text(log.read_text(encoding="utf-8").replace(
            "<!-- handoff:open:start -->", "<!-- removed -->"), encoding="utf-8")
        r = run(d, "doctor", expect_ok=False)
        check("doctor flags a missing marker block", "marker block" in r.stdout, r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_all():
    print("multi-agent-collaboration-protocol regression suite\n")
    for fn in (t_init, t_init_ships_the_tool,
               t_init_registers_existing_instruction_files_once,
               t_init_can_use_custom_state_dir, t_migrate_legacy_storage,
               t_migrate_refuses_split_storage, t_state_dir_rejects_unsafe_paths,
               t_init_ignores_vendor_directories, t_init_needs_the_skill_folder,
               t_init_inside_skill_skips_installed_copy, t_body_input,
               t_summary, t_waiting_alias,
               t_close_missing_promotion_refuses_without_write,
               t_close_stale_promotion_refuses_without_write,
               t_close_succeeds_with_fresh_promotion,
               t_close_allows_answered_and_blocked_threads,
               t_close_accepts_file_changed_before_report_comment,
               t_close_requires_all_promoted_paths_fresh,
               t_close_rejects_unsafe_promoted_paths,
               t_close_refuses_terminal_threads,
               t_close_does_not_replace_reply_closed,
               t_history_nudge, t_history_stale_across_year_boundary,
               t_doctor_notes_ignored_log, t_doctor_notes_unknown_roster_participants,
               t_doctor_skips_unfilled_roster_template,
               t_roundtrip, t_unicode_legacy, t_year_boundary,
               t_sort_across_years, t_external_edit, t_concurrent,
               t_owes_reply, t_relay_stamping, t_brief_compact_flag, t_ask_and_approval,
               t_blank_status, t_doctor_catches):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as e:
            FAIL.append(fn.__name__)
            print(f"  ERROR {fn.__name__}: {e}")
        print()
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    return not FAIL


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
