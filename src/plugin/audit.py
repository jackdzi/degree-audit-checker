"""The grade rules, the answer-key solver, and the three tools."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

from slimconfig import plain_output

from contract import (
    Attempt,
    AuditInput,
    AuditOutput,
    CatalogOutput,
    Course,
    Kind,
    PinOutput,
    PlaceInput,
    PlaceOutput,
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


def eligible_homes(program: str, rows: list[list[str]]) -> dict[str, list[str]]:
    """{course: the requirements its best grade lets it count toward}, for courses with at least one."""
    reqs = PROGRAMS[program]["requirements"]
    best = best_grades(rows)
    homes = {c: [r["id"] for r in reqs if c in r["courses"] and meets(g, r["min_grade"])] for c, g in best.items()}
    return {c: ids for c, ids in homes.items() if ids}


def build_audit(program: str, rows: list[list[str]], placed: dict[str, list[str]]) -> tuple[int, AuditOutput]:
    """The audit of a placement {requirement id: courses}, and how many requirements it satisfies."""
    reqs = PROGRAMS[program]["requirements"]
    results = [
        RequirementResult(requirement=r["id"], satisfied=missing(r, placed[r["id"]]) == 0, courses=placed[r["id"]], missing=missing(r, placed[r["id"]]))
        for r in reqs
    ]
    satisfied = sum(result.satisfied for result in results)
    credits = total_credits(rows)
    return satisfied, AuditOutput(requirements=results, total_credits=credits, graduation_ready=satisfied == len(reqs) and credits >= TOTAL_CREDITS)


def audit_path(task: AuditInput) -> str:
    return f"audit/{task.program.value}-{task.seed}.json"


def place_courses(given: PlaceInput, workspace: Path) -> PlaceOutput:
    """Apply each course to a requirement: shared courses where the placements say, the rest to their one requirement."""
    check_seed(given.task)
    program = given.task.program.value
    rows = transcript(given.task.seed, program)
    homes = eligible_homes(program, rows)
    chosen: dict[str, str] = {}
    for placement in given.placements:
        if placement.course not in homes:
            raise ValueError(f"{placement.course} counts toward no requirement on this transcript")
        if placement.course in chosen:
            raise ValueError(f"{placement.course} is placed twice")
        if placement.requirement not in homes[placement.course]:
            raise ValueError(f"{placement.course} may count toward {', '.join(homes[placement.course])}, not {placement.requirement}")
        chosen[placement.course] = placement.requirement
    unplaced = sorted(c for c, ids in homes.items() if len(ids) > 1 and c not in chosen)
    if unplaced:
        raise ValueError(f"place every course with two or more requirements; not placed: {', '.join(unplaced)}")
    placed = {r["id"]: [] for r in PROGRAMS[program]["requirements"]}
    for course in sorted(homes):
        placed[chosen.get(course, homes[course][0])].append(course)
    satisfied, audit = build_audit(program, rows, placed)
    path = workspace / audit_path(given.task)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"task": plain_output(given.task), "placements": [plain_output(p) for p in given.placements], "audit": plain_output(audit)}, indent=1), encoding="utf-8")
    return PlaceOutput(file=audit_path(given.task), satisfied=satisfied, audit=audit)


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
    reqs = PROGRAMS[task.program.value]["requirements"]
    best = best_grades(rows)
    courses = []
    for course in sorted(best):
        homes = [r["id"] for r in reqs if course in r["courses"] and meets(best[course], r["min_grade"])]
        if homes:
            courses.append(Course(course=course, credits=COURSES[course][1], best_grade=best[course], counts_toward=homes))
    return TranscriptOutput(
        attempts=[Attempt(term=term, course=course, title=COURSES[course][0], credits=COURSES[course][1], grade=grade) for term, course, grade in rows],
        courses=courses,
        passed_credits=total_credits(rows),
    )


def pin_audit(task: AuditInput, workspace: Path) -> PinOutput:
    check_seed(task)
    program = task.program.value
    rows = transcript(task.seed, program)
    top, placed = solve(program, rows)
    _, audit = build_audit(program, rows, placed)
    return PinOutput(data_sha256=canonical_sha256({"program": PROGRAMS[program], "transcript": rows}), best_satisfied=top, audit=audit)
