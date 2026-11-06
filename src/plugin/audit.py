"""The grade rules, the answer-key solver, and the three tools."""

from __future__ import annotations

from itertools import product
from pathlib import Path

from contract import (
    Attempt,
    AuditInput,
    AuditOutput,
    CatalogOutput,
    Kind,
    PinOutput,
    Requirement,
    RequirementResult,
    TranscriptOutput,
)
from plugin.catalog import COURSES, GRADES, PROGRAMS, TOTAL_CREDITS, transcript
from plugin.rng import canonical_sha256

MAX_SEED = 1_000_000_000


def check_seed(task: AuditInput) -> None:
    if not 0 <= task.seed <= MAX_SEED:
        raise ValueError(f"seed must be from 0 to {MAX_SEED}")


def passing(grade: str) -> bool:
    return grade not in ("F", "W")


def meets(grade: str, minimum: str) -> bool:
    """Whether a grade counts where ``minimum`` is the lowest grade allowed; P meets only D-."""
    if not passing(grade):
        return False
    if grade == "P":
        return minimum == "D-"
    return GRADES.index(grade) <= GRADES.index(minimum)


def best_grades(rows: list[list[str]]) -> dict[str, str]:
    """Each course's best grade over its attempts (the grade order runs A, ..., D-, P, F, W)."""
    best: dict[str, str] = {}
    for _, course, grade in rows:
        if course not in best or GRADES.index(grade) < GRADES.index(best[course]):
            best[course] = grade
    return best


def missing(req: dict, applied: list[str]) -> int:
    if req["kind"] == "credits":
        return max(0, req["needed"] - sum(COURSES[c][1] for c in applied))
    return max(0, req["needed"] - len(applied))


def solve(program: str, rows: list[list[str]]) -> tuple[int, dict[str, list[str]]]:
    """The most requirements a placement can satisfy, and one placement that does.

    A course that qualifies for one requirement goes there; each course that qualifies for two or
    more is tried in each of them, every combination."""
    reqs = PROGRAMS[program]["requirements"]
    best = best_grades(rows)
    eligible = {
        course: [r["id"] for r in reqs if course in r["courses"] and meets(grade, r["min_grade"])]
        for course, grade in best.items()
    }
    fixed = {r["id"]: [c for c in r["courses"] if eligible.get(c) == [r["id"]]] for r in reqs}
    shared = sorted(c for c, ids in eligible.items() if len(ids) > 1)
    top, chosen = -1, {}
    for homes in product(*(eligible[c] for c in shared)):
        placed = {r["id"]: list(fixed[r["id"]]) for r in reqs}
        for course, home in zip(shared, homes):
            placed[home].append(course)
        satisfied = sum(1 for r in reqs if missing(r, placed[r["id"]]) == 0)
        if satisfied > top:
            top, chosen = satisfied, placed
    return top, chosen


def total_credits(rows: list[list[str]]) -> int:
    return sum(COURSES[course][1] for course, grade in best_grades(rows).items() if passing(grade))


def get_catalog(task: AuditInput, workspace: Path) -> CatalogOutput:
    check_seed(task)
    program = PROGRAMS[task.program.value]
    return CatalogOutput(
        program=task.program,
        name=program["name"],
        total_credits=TOTAL_CREDITS,
        grade_order=list(GRADES),
        requirements=[
            Requirement(id=r["id"], title=r["title"], kind=Kind(r["kind"]), needed=r["needed"], min_grade=r["min_grade"], courses=list(r["courses"]))
            for r in program["requirements"]
        ],
    )


def get_transcript(task: AuditInput, workspace: Path) -> TranscriptOutput:
    check_seed(task)
    rows = transcript(task.seed, task.program.value)
    return TranscriptOutput(
        attempts=[Attempt(term=term, course=course, title=COURSES[course][0], credits=COURSES[course][1], grade=grade) for term, course, grade in rows]
    )


def pin_audit(task: AuditInput, workspace: Path) -> PinOutput:
    check_seed(task)
    program = task.program.value
    rows = transcript(task.seed, program)
    top, placed = solve(program, rows)
    reqs = PROGRAMS[program]["requirements"]
    results = [
        RequirementResult(requirement=r["id"], satisfied=missing(r, placed[r["id"]]) == 0, courses=placed[r["id"]], missing=missing(r, placed[r["id"]]))
        for r in reqs
    ]
    credits = total_credits(rows)
    audit = AuditOutput(requirements=results, total_credits=credits, graduation_ready=top == len(reqs) and credits >= TOTAL_CREDITS)
    return PinOutput(data_sha256=canonical_sha256({"program": PROGRAMS[program], "transcript": rows}), best_satisfied=top, audit=audit)
