# Degree Audit Checker

A `nanoagent.plugin/v0001` plugin. Its task, `audit-degree`, gives an agent a
degree program's catalog and a student's transcript and asks for a degree
audit: which requirements are satisfied, by which courses, what is still
missing, the student's total credits, and whether they can graduate. Some
courses fit two requirements, and each course counts toward only one, so the
agent must place them to satisfy as many requirements as possible. The
transcript comes from a seed, and a deterministic verifier rebuilds it,
finds the best possible audit its own way, and checks every requirement.

## Tools

| Tool | Does | Code |
|---|---|---|
| `get_catalog` | The program's requirements (kind, what each needs, minimum grade, the courses that count), the credits needed to graduate, and the grade order | `src/plugin/audit.py`, `src/plugin/catalog.py` |
| `get_transcript` | The student's course attempts, oldest term first, each with its term, title, credits and grade; and its summary: every course that may count toward a requirement, with its best grade, credits and the requirements it qualifies for (`counts_toward`), and the passed credits | `src/plugin/audit.py`, `src/plugin/catalog.py` |
| `place_courses` | Applies every course to a requirement, each course with two or more requirements where the agent's placements say and the rest to their one requirement; saves the audit this gives to `audit/<program>-<seed>.json` and returns it with how many requirements it satisfies | `src/plugin/audit.py` |
| `pin_audit` | The answer key: the most requirements any legal placement satisfies and one audit that does, with the sha256 of the catalog and transcript | `src/plugin/audit.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `audit-degree` | Audits the transcript against the program, placing shared courses to satisfy as many requirements as possible | `agent`, with `get_catalog`, `get_transcript` and `place_courses`; reference `pin_audit` |

## The task

Input: `seed` (0 to 1,000,000,000) and `program`, `cs-bs` (B.S. in Computer
Science, 7 requirements) or `data-science-ba` (B.A. in Data Science, 7
requirements). Both catalogs are fictional and fixed in
`src/plugin/catalog.py`.

The rules:

- A retaken course counts once, with its best attempt. Grades run A, A-, ...,
  D-, P, F, W. F and W are never passed.
- A course counts toward a requirement when it is listed there and its best
  grade meets the requirement's minimum (C- or D-). P (pass) meets D- only.
- Requirements are `all` (every listed course), `choose` (n of the listed
  courses) or `credits` (listed courses worth n credits).
- Each course counts toward at most one requirement. A requirement left short
  must use every qualifying course not applied elsewhere.
- Total credits count every passed course once. The student can graduate when
  every requirement is satisfied and total credits reach 120.

The agent's decision is the placement: for each course that qualifies for two
requirements, which one it counts toward, so that as many requirements as
possible are satisfied. The grade rules (best attempt, F and W, P, minimum
grades) are applied by `get_transcript`, and `place_courses` works out what is
satisfied and missing from the placement. This split keeps each step within
RUSH Lab's default limits (replies of at most 2,048 tokens, reasoning
included): asked to apply the grade rules to 30 to 50 attempts itself,
DeepSeek V4 Flash spent the whole reply reasoning and never answered. The
agent calls `get_catalog` and `get_transcript`, then `place_courses`, then
`submit` with the audit it returned.

Transcripts vary in how far along the student is. They include failed,
withdrawn and pass-graded attempts, retakes in later terms, grades on the
C-/D+ line, and (in about one seed in ten) exactly 120 credits. In about 40%
of B.S. seeds and 90% of B.A. seeds, putting each shared course in the first
requirement it fits satisfies fewer requirements than the best placement.

## Ground truth and verification

`verify_task` (in `verifier/audit.py`):

1. Rebuilds the transcript from the seed with its own copy of the generator
   (`verifier/catalog.py`), and checks that the pinned answer key holds the
   same catalog and transcript (by sha256) and the same best count.
2. Ranks each course's attempts itself, and finds the most requirements that
   can be satisfied together by trying sets of requirements, largest first,
   and searching for a placement of the shared courses that satisfies the set.
   The tool instead tries every placement of every shared course.
3. Checks each submitted requirement: every course listed there, on the
   transcript, meeting the minimum grade and used nowhere else; `missing` and
   `satisfied` following from those courses; and, when short, no qualifying
   course left unused.
4. Checks that the audit satisfies the best possible number of requirements
   (any best placement is accepted), checks `total_credits` and
   `graduation_ready`, and checks that the audit saved in the workspace is
   the one submitted.

The verdict is valid only when every check holds; its score is the share of
checks that hold, one per requirement plus the requirement list, the best
placement, the total credits and the graduation answer.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (no network), tools, task
├── contract.py      # each tool's and task's typed input and output
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable names needed (none)
├── src/plugin/      # the MCP server (__main__.py), the generator (rng.py), the catalogs and
│                    #   transcripts (catalog.py), and the grade rules, solver and tools (audit.py)
├── tests/           # the verifier's tests, tool tests, a 2,000-transcript agreement test, an MCP
│                    #   smoke test, and a scripted no-model agent (scripted_agent.py)
├── ui/              # renderers.js and renderers.css: outputs drawn from their JSON Schema
├── product/         # the product page: product.yaml and icon.svg
└── verifier/        # the deterministic verifier: audit.py, its copies catalog.py and rng.py, checks.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

No network and no data files: every transcript comes from its seed. NanoAgent
passes the folder the plugin may write to as `NANOAGENT_WORKSPACE`.
