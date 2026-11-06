"""The tools, the independent verifier search, and the MCP server."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import anyio
from helpers import task
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from plugin import get_catalog, get_transcript, pin_audit
from plugin.audit import best_grades, meets, solve, total_credits
from plugin.catalog import COURSES, PROGRAMS, TERMS, transcript
from verifier.audit import most_satisfied, rebuild

ROOT = Path(__file__).resolve().parents[1]


def test_a_transcript_is_the_same_for_the_same_seed() -> None:
    assert transcript(9, "cs-bs") == transcript(9, "cs-bs")
    assert transcript(9, "cs-bs") != transcript(10, "cs-bs")


def test_grade_rules() -> None:
    assert meets("C-", "C-") and not meets("D+", "C-")
    assert meets("P", "D-") and not meets("P", "C-")
    assert not meets("F", "D-") and not meets("W", "D-")
    assert best_grades([["Fall 2022", "COMP 140", "F"], ["Spring 2023", "COMP 140", "B"]]) == {"COMP 140": "B"}
    assert best_grades([["Fall 2022", "COMP 140", "D-"], ["Spring 2023", "COMP 140", "P"]]) == {"COMP 140": "D-"}


def test_a_hand_built_placement_puts_shared_courses_where_they_complete_a_requirement() -> None:
    # COMP 382 (theory or electives) and COMP 410 (systems or electives) are shared; four electives-only
    # courses already make 12 credits. The best placement satisfies theory, systems and electives.
    rows = [["Fall 2022", c, "A"] for c in ("COMP 382", "COMP 410", "COMP 440", "COMP 447", "COMP 448", "COMP 487")]
    top, placed = solve("cs-bs", rows)
    assert top == 3
    assert placed["theory"] == ["COMP 382"] and placed["systems"] == ["COMP 410"]
    assert sum(COURSES[c][1] for c in placed["electives"]) == 12


def test_the_tool_and_the_verifier_agree_on_2000_transcripts() -> None:
    for program in ("cs-bs", "data-science-ba"):
        for seed in range(1000):
            given = task(seed, program)
            reqs, rows, best = rebuild(given)
            assert rows == transcript(seed, program)
            assert solve(program, rows)[0] == most_satisfied(reqs, best), (program, seed)


def test_transcripts_are_well_formed() -> None:
    for program in ("cs-bs", "data-science-ba"):
        for seed in range(300):
            rows = transcript(seed, program)
            seen: dict[str, int] = {}
            for term, course, _ in rows:
                assert course in COURSES and term in TERMS
                assert seen.get(course, -1) < TERMS.index(term), "a retake comes in a later term"
                seen[course] = TERMS.index(term)
            assert sum(1 for _, c, _ in rows if c == rows[0][1]) <= 2


def test_the_seeds_cover_the_interesting_cases() -> None:
    totals = [total_credits(transcript(seed, "cs-bs")) for seed in range(300)]
    assert 120 in totals and min(totals) < 120 < max(totals)
    tops = {solve("cs-bs", transcript(seed, "cs-bs"))[0] for seed in range(300)}
    assert len(PROGRAMS["cs-bs"]["requirements"]) in tops and min(tops) < 6


def test_the_tools_serve_the_catalog_and_transcript() -> None:
    catalog = get_catalog(task(), Path("."))
    assert [r.id for r in catalog.requirements] == [r["id"] for r in PROGRAMS["cs-bs"]["requirements"]]
    attempts = get_transcript(task(), Path(".")).attempts
    assert [[a.term, a.course, a.grade] for a in attempts] == transcript(4, "cs-bs")
    pinned = pin_audit(task(), Path("."))
    assert pinned.best_satisfied == sum(r.satisfied for r in pinned.audit.requirements)


def test_the_mcp_server_lists_and_runs_every_tool(tmp_path: Path) -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "plugin"], cwd=str(ROOT), env={**os.environ, "NANOAGENT_WORKSPACE": str(tmp_path)}
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert names == {"get_catalog", "get_transcript", "pin_audit"}
            given = {"seed": 1, "program": "data-science-ba"}
            for name in names:
                answer = await session.call_tool(name, given)
                assert not answer.isError, name
            bad = await session.call_tool("get_transcript", {"seed": 1, "program": "history-ba"})
            assert bad.isError

    anyio.run(run)
