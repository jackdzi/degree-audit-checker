"""The degree-audit verifier. It rebuilds the transcript from its seed, ranks each course's attempts
itself, and finds the most requirements that can be satisfied at once its own way: it tries sets of
requirements, largest first, and searches for a placement of the shared courses that satisfies the
whole set. The tools instead try every placement of every shared course; the two must agree."""

from itertools import combinations

from .catalog import COURSES, GRADES, PROGRAMS, TOTAL_CREDITS, transcript
from .checks import result
from .rng import canonical_sha256

MAX_SEED = 1_000_000_000
RANK = {grade: index for index, grade in enumerate(GRADES)}


def counts(grade, minimum):
    """Whether a best grade lets a course count where ``minimum`` is required."""
    if grade in ("F", "W"):
        return False
    if grade == "P":
        return minimum == "D-"
    return RANK[grade] <= RANK[minimum]


def rebuild(task):
    """(the program's requirements, the transcript rows, each course's best grade)."""
    program = task.program.value
    rows = transcript(task.seed, program)
    best = {}
    for _, course, grade in rows:
        best[course] = grade if course not in best else min(best[course], grade, key=RANK.get)
    return PROGRAMS[program]["requirements"], rows, best


def shortfall(req, courses):
    if req["kind"] == "credits":
        return max(0, req["needed"] - sum(COURSES[c][1] for c in courses))
    return max(0, req["needed"] - len(courses))


def qualifying(reqs, best):
    """{requirement id: [courses whose best grade counts there]}."""
    return {r["id"]: [c for c in r["courses"] if c in best and counts(best[c], r["min_grade"])] for r in reqs}


def most_satisfied(reqs, best):
    """The largest number of requirements that one placement satisfies together."""
    fits = qualifying(reqs, best)
    homes = {}
    for req_id, courses in fits.items():
        for c in courses:
            homes.setdefault(c, []).append(req_id)
    by_id = {r["id"]: r for r in reqs}

    def placeable(targets, used):
        if not targets:
            return True
        req = by_id[targets[0]]
        own = [c for c in fits[req["id"]] if len(homes[c]) == 1]
        free = [c for c in fits[req["id"]] if len(homes[c]) > 1 and c not in used]
        for size in range(len(free) + 1):
            for extra in combinations(free, size):
                if shortfall(req, own + list(extra)) == 0 and placeable(targets[1:], used | set(extra)):
                    return True
        return False

    ids = [r["id"] for r in reqs]
    for size in range(len(ids), 0, -1):
        if any(placeable(list(group), set()) for group in combinations(ids, size)):
            return size
    return 0


def passed_credits(best):
    return sum(COURSES[c][1] for c, grade in best.items() if grade not in ("F", "W"))


def judge(reqs, best, audit):
    """Every check of an audit: {name: problem or None}, plus how many requirements it satisfies."""
    fits = qualifying(reqs, best)
    checks = {}
    ids = [r["id"] for r in reqs]
    given = [r.requirement for r in audit.requirements]
    if given != ids:
        checks["requirement_list"] = f"the results name {given}, not the catalog's requirements {ids} in order"
    else:
        checks["requirement_list"] = None
    uses = {}
    for r in audit.requirements:
        for c in r.courses:
            uses[c] = uses.get(c, 0) + 1
    satisfied = 0
    placed = set(uses)
    for req in reqs:
        mine = [r for r in audit.requirements if r.requirement == req["id"]]
        if len(mine) != 1:
            checks[f"requirement {req['id']}"] = "not given exactly once"
            continue
        r = mine[0]
        problem = None
        for c in r.courses:
            if c not in req["courses"]:
                problem = f"{c} does not count toward {req['id']}"
            elif c not in best:
                problem = f"{c} is not on the transcript"
            elif c not in fits[req["id"]]:
                problem = f"{c}'s best grade, {best[c]}, does not meet {req['id']}'s minimum, {req['min_grade']}"
            elif uses[c] > 1:
                problem = f"{c} is used more than once"
            if problem:
                break
        need = shortfall(req, r.courses)
        if problem is None and r.missing != need:
            problem = f"missing is {r.missing}; with these courses it is {need}"
        if problem is None and r.satisfied != (need == 0):
            problem = f"satisfied is {str(r.satisfied).lower()}, but these courses leave {need} missing"
        if problem is None:
            satisfied += need == 0
            # A requirement left short may not leave a qualifying course unused.
            idle = [c for c in fits[req["id"]] if c not in placed]
            if need and idle:
                problem = f"{req['id']} is short but {idle[0]} qualifies and is unused"
        checks[f"requirement {req['id']}"] = problem
    return checks, satisfied


def seed_problem(task):
    if not 0 <= task.seed <= MAX_SEED:
        return f"seed must be from 0 to {MAX_SEED}"
    return None


def verify_audit_input(value):
    problem = seed_problem(value)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_catalog_output(task, output):
    program = PROGRAMS[task.program.value]
    given = [
        {"id": r.id, "title": r.title, "kind": r.kind.value, "needed": r.needed, "min_grade": r.min_grade, "courses": r.courses}
        for r in output.requirements
    ]
    if given != program["requirements"] or output.name != program["name"] or output.total_credits != TOTAL_CREDITS:
        return result(False, "the catalog is not the program's")
    if output.grade_order != GRADES:
        return result(False, "the grade order is wrong")
    return result(True, "the catalog is the program's")


def verify_transcript_output(task, output):
    rows = transcript(task.seed, task.program.value)
    given = [[a.term, a.course, a.grade] for a in output.attempts]
    if given != rows:
        return result(False, "the transcript is not the seed's")
    if any(a.credits != COURSES[a.course][1] or a.title != COURSES[a.course][0] for a in output.attempts):
        return result(False, "a course's title or credits is wrong")
    return result(True, "the transcript is the seed's", attempts=len(rows))


def verify_pin_output(task, output):
    reqs, rows, best = rebuild(task)
    if output.data_sha256 != canonical_sha256({"program": PROGRAMS[task.program.value], "transcript": rows}):
        return result(False, "the pinned data is not the seed's")
    top = most_satisfied(reqs, best)
    if output.best_satisfied != top:
        return result(False, f"the answer key satisfies {output.best_satisfied} requirements; the verifier finds {top}")
    checks, satisfied = judge(reqs, best, output.audit)
    failed = [f"{name}: {problem}" for name, problem in checks.items() if problem]
    if failed or satisfied != top:
        return result(False, "the pinned audit fails: " + "; ".join(failed or ["it is not the best placement"]))
    return result(True, "the answer key is a best audit", best_satisfied=top)


def verify_task(arguments, output, reference, workspace):
    if reference is None or verify_pin_output(arguments, reference)["valid"] is not True:
        return result(False, "the pinned answer key does not match the transcript the seed gives")
    reqs, _, best = rebuild(arguments)
    top = most_satisfied(reqs, best)
    credits = passed_credits(best)
    checks, satisfied = judge(reqs, best, output)
    legal = all(problem is None for problem in checks.values())
    checks["best_placement"] = (
        None if not legal or satisfied == top
        else f"the placement satisfies {satisfied} requirements; {top} can be satisfied together"
    )
    checks["total_credits"] = None if output.total_credits == credits else f"total_credits is {output.total_credits}, not {credits}"
    ready = top == len(reqs) and credits >= TOTAL_CREDITS
    checks["graduation_ready"] = (
        None if output.graduation_ready == ready else f"graduation_ready is {str(output.graduation_ready).lower()}, not {str(ready).lower()}"
    )
    failed = {name: problem for name, problem in checks.items() if problem}
    details = {
        "requirements": len(reqs),
        "best_satisfied": top,
        "submitted_satisfied": satisfied,
        "total_credits": credits,
        "graduation_ready": ready,
        "failed_checks": failed,
    }
    score = (len(checks) - len(failed)) / len(checks)
    if failed:
        return result(False, "; ".join(f"{name}: {problem}" for name, problem in failed.items()), score=score, **details)
    return result(True, f"a best audit: {top} of {len(reqs)} requirements satisfied, {credits} credits", **details)
