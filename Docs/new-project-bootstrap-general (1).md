# New Software Project — Bootstrap Prompt

Paste the block below verbatim to any AI assistant (Claude, Gemini, GPT, etc.) at the
start of a brand-new software project. The AI will interview you, then create the three
control files that make up the session framework.

After the initial setup, the "Open" and "Close" prompts embedded inside the generated
`AGENTS.md` are what you paste at the start and end of every future session.

---

## Paste this to bootstrap a new project

```
I am starting a new software project and I want you to help me set up a
session-control framework before we write any code. This framework uses three files
to prevent context rot across sessions and to work identically on any AI platform:

  AGENTS.md          — permanent project context; every AI reads this first
  .planning/STATE.md — cross-session working memory; decisions + active work
  .planning/next-session.md — handoff written at close, read first at open

Before creating those files, ask me the following questions one group at a time.
Wait for my answers before moving to the next group.

--- GROUP 1: Project basics ---
1. What is this project in one or two sentences? (What does it do, for whom?)
2. Is this a greenfield project or does an existing codebase already exist?
   If existing: where is the repo, and what state is it in?
3. What is the primary programming language?
4. What is the primary output or deliverable? (web app, CLI tool, library, API,
   desktop app, game, etc.)

--- GROUP 2: Tech stack ---
5. What framework(s), if any, will be used? (e.g. React, Django, Express, .NET)
6. What build tool / package manager? (e.g. npm, cargo, pip, gradle, make)
7. What test runner / testing approach? (e.g. pytest, jest, go test, manual for now)
8. What shell/OS are we running on? (Windows/PowerShell, macOS/zsh, Linux/bash)
9. Where will this be deployed or run? (local only, cloud, Docker, app store, etc.)

--- GROUP 3: Safety and credentials ---
10. Are there any external APIs or services that need credentials? (name them)
11. How should credentials be stored? (env file, gitignored flat file, vault, other)
12. Are there any files or directories that should NEVER be modified without
    explicit sign-off? (list them — generated code, config files, vendor dirs, etc.)
13. Are there any deploy or production-safety rules? (e.g. no force-push to main,
    no direct commits to production branch, must pass CI before merge)

--- GROUP 4: First task ---
14. What is the very first concrete task to work on once setup is done?
    (e.g. "scaffold the project with the framework CLI", "set up the build pipeline",
    "implement the core data model", "create the hello-world endpoint")

---

Once I answer all four groups, do the following:

1. Create the directory .planning/ if it does not exist.

2. Create AGENTS.md in the project root with this exact structure
   (populate each section from my answers; keep the section headers):

   # AGENTS.md
   Context file for any AI assistant working on this project.
   Read this before writing or modifying any code.

   ## What This Project Is
   [2-3 sentence description from answers]

   ## Off-Limits — Never Modify
   [Table: Path | Why — one row per file/dir the AI must not touch without explicit approval]
   If you need to modify anything listed here, discuss it first. Never alter production
   config or generated files without explicit instruction.

   ## Safety
   [Safety rules from answers — deploy protection, branch rules, backup/snapshot
   procedures if applicable. Note any scripts that protect state before mutations.]

   ## Credentials
   [How to load credentials into the shell environment, based on chosen method.
   Note which env vars are required for which scripts or features.]

   ## Running Things
   [Placeholder commands for build, test, lint, run, deploy — fill in as the
   project takes shape. Note any package dependencies and when they are required.]

   ## Architecture & Key Modules
   [Leave as "TBD — will be filled in as the project structure takes shape." for now]

   ## Key Commands / Endpoints
   [Leave as "TBD — will be filled in as commands, routes, or user-facing operations
   are implemented." for now]

   ## Shared Utilities & Patterns
   [Leave as "None yet. Add reusable code patterns, helper functions, and conventions
   here as they are developed." for now]

   ## Roadmap
   [Table: Milestone | What it adds — at minimum list v1 (initial working version)
   and any later milestones the user described.]

   ## Session Protocol
   [Embed the three prompts below verbatim, with project-specific file paths filled in]

   ### Open
   Read these files in full before doing anything:
     [absolute path to .planning/next-session.md]
     [absolute path to .planning/STATE.md]
     [absolute path to AGENTS.md]

   Then tell me: what is the specific next task, any constraints that affect it,
   and your proposed first action. Do not write any code until I confirm.

   ### During
   Whenever a decision is made mid-session, update .planning/STATE.md immediately.
   Do not wait until close — decisions not recorded are lost if the context resets.

   ### Close
   Session closing. Please do the following:
   1. Update [absolute path to .planning/STATE.md]
      — decisions made this session, current active work, open questions
   2. Overwrite [absolute path to .planning/next-session.md]
      with a fresh handoff: specific task, what was done, exact next steps,
      files modified, blockers
   3. Update [absolute path to AGENTS.md] if any project facts changed
      (new scripts, architecture changes, stack decisions confirmed)
   4. Finish with a one-sentence summary of what changed this session.

3. Create .planning/STATE.md with this structure:

   # STATE.md — Working Memory
   Cross-session context. Update this when decisions are made or work changes direction.
   Any AI assistant should read this before starting a session.

   ## Active Work
   [Describe the first task from answer 14. Mark it as "not started".]

   ## Decisions Made
   | Date | Decision | Rationale |
   | --- | --- | --- |
   [Leave empty — first row will be added during the first session]

   ## Open Questions
   [Leave empty for now]

4. Create .planning/next-session.md with this structure:

   # Next Session
   _Written by the AI at session close. Read this first, then STATE.md, then AGENTS.md._

   ## Specific Task
   [First task from answer 14]

   ## What Was Done This Session
   Project framework bootstrapped. AGENTS.md, STATE.md, and next-session.md created.

   ## Exact Next Steps
   1. [First concrete action needed to begin the task from answer 14]

   ## Design Decisions Locked In
   None yet.

   ## Files Created / Modified This Session
   - AGENTS.md (created)
   - .planning/STATE.md (created)
   - .planning/next-session.md (created)

   ## Blockers / Open Questions
   None yet.

5. After creating all three files, print a short confirmation:
   - Confirm the three files were created and where they live.
   - Print the "Open" prompt so I can copy it for my next session.
   - Tell me the first action you propose for the task in answer 14, and wait
     for my approval before doing anything else.

Do not write any application code until the framework files are created
and I have confirmed the first action.
```

---

## How the framework works (for reference)

### The three files and their roles

| File | Updated by | Read by | Purpose |
| --- | --- | --- | --- |
| `AGENTS.md` | AI (when facts change) | Every AI, every session | Permanent project context — architecture, conventions, off-limits, roadmap |
| `.planning/STATE.md` | AI (immediately when decisions are made) | Every AI, every session | Cross-session memory — active work, decisions log, open questions |
| `.planning/next-session.md` | AI (at session close) | Every AI (first thing at open) | Handoff — specific task, exact next step, blockers |

### Why three files instead of one

- `AGENTS.md` is slow-changing. It holds facts that stay true for months.
- `STATE.md` is medium-changing. Decisions accumulate; active work shifts.
- `next-session.md` is fast-changing. It is overwritten every session close.

Reading `next-session.md` first gives the AI a specific task and next step
without needing to reconstruct intent from the other two files.

### The decisions log (most important pattern)

Every significant decision goes into `STATE.md` under "Decisions Made" immediately —
not at close, immediately. The table format is:

| Date | Decision | Rationale |
| --- | --- | --- |
| YYYY-MM-DD | What was decided | Why — the constraint, tradeoff, or evidence that drove it |

This is the primary defense against context rot. If the rationale is not recorded,
the next session has no way to distinguish an intentional design choice from
an oversight, and will reverse it.

### Decision quality bar

A decision worth recording answers "why this and not the obvious alternative":
- Chosen SQLite over Postgres for local-first single-user app (no server process needed)
- Rate-limit API calls to 1 req/s (not 10 — caused throttling in testing)
- Monorepo with /client and /server (not separate repos — shared types, simpler CI)

Decisions that do NOT need recording: obvious implementation details, things
derivable from reading the code, temporary choices you will revisit in the same session.

### Handoff specificity

`next-session.md` must contain an **exact next step**, not a direction.
Bad: "Continue working on the authentication module."
Good: "Add JWT validation middleware to src/middleware/auth.ts, then write tests for the expired-token case."

The test: could a new AI with no prior context read this and know precisely what
command to run or what file to open first?

### Platform agnosticism

The session protocol uses plain-text paste prompts only. No slash commands,
no tool-specific syntax, no special modes. The open and close prompts work
identically pasted into:
- Claude Code (CLI or VS Code extension)
- Claude.ai web
- Gemini
- ChatGPT
- Any other assistant

### Safety patterns to establish early

1. **Protect production state** — before any operation that mutates deployed state
   (database migrations, config changes, infrastructure updates), create a snapshot
   or checkpoint you can roll back to. What this looks like depends on the project:
   - Database: snapshot before schema migrations
   - Config: git tag before deploy
   - Cloud infrastructure: backup current state file before modifying

2. **Idempotent operations** — any long-running or state-mutating process should be
   designed so it can be interrupted and restarted without side effects. Record
   progress (timestamps, status flags, checkpoint files) so re-running picks up
   where it left off rather than starting over or duplicating work.

3. **Credentials never committed** — store secrets in a gitignored file (e.g. `.env`,
   `codes`) and document how to load them in `AGENTS.md`. Never hardcode them.
   Add the credentials file to `.gitignore` immediately at project setup.

4. **Off-limits table** — list protected files and directories in `AGENTS.md`
   explicitly. An AI will not hesitate to modify files it does not know are
   sacred unless told otherwise. Common entries: generated code, vendor directories,
   production config, migration files that have already been run.
