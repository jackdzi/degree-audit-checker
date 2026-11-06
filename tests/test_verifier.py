"""The verifier on correct, wrong, missing, malformed and boundary audits."""

from __future__ import annotations

import copy

import pytest
from helpers import gold, task, verdict

import verifier
from plugin.audit import best_grades, meets
from plugin.catalog import PROGRAMS, transcript

PROGRAMS_IDS = ["cs-bs", "data-science-ba"]


def find_seed(program: str, wanted) -> int:
    """The first seed whose transcript (rows, best grades) has a wanted feature."""
    for seed in range(2000):
        rows = transcript(seed, program)
        if wanted(rows, best_grades(rows)):
            return seed
    raise AssertionError("no seed has the feature")


def requirement(audit: dict, req_id: str) -> dict:
    return next(r for r in audit["requirements"] if r["requirement"] == req_id)


@pytest.mark.parametrize("program", PROGRAMS_IDS)
@pytest.mark.parametrize("seed", range(25))
def test_accepts_a_best_audit(program: str, seed: int) -> None:
    given = task(seed, program)
    audit, reference = gold(given)
    result = verdict(given, audit, reference)
    assert result["valid"] is True and result["score"] == 1.0, result["message"]


def test_accepts_a_different_best_placement() -> None:
    # Moving a surplus course to another requirement it also fits keeps the audit a best one.
    from plugin.audit import missing

    for program in PROGRAMS_IDS:
        reqs = {q["id"]: q for q in PROGRAMS[program]["requirements"]}
        for seed in range(300):
            given = task(seed, program)
            audit, reference = gold(given)
            best = best_grades(transcript(seed, program))
            for source in audit["requirements"]:
                for course in source["courses"]:
                    rest = [c for c in source["courses"] if c != course]
                    if missing(reqs[source["requirement"]], rest):
                        continue
                    for target in audit["requirements"]:
                        spec = reqs[target["requirement"]]
                        if target is source or course not in spec["courses"] or not meets(best[course], spec["min_grade"]):
                            continue
                        moved = copy.deepcopy(audit)
                        requirement(moved, source["requirement"])["courses"] = rest
                        goal = requirement(moved, target["requirement"])
                        goal["courses"] = goal["courses"] + [course]
                        goal["missing"] = missing(spec, goal["courses"])
                        goal["satisfied"] = goal["missing"] == 0
                        result = verdict(given, moved, reference)
                        assert result["valid"] is True, result["message"]
                        return
    raise AssertionError("no seed has a movable surplus course")


def test_rejects_a_worse_placement() -> None:
    # Put every shared course in the first requirement it fits: on many seeds that satisfies fewer.
    for seed in range(200):
        given = task(seed, "data-science-ba")
        audit, reference = gold(given)
        naive = copy.deepcopy(audit)
        shared = {}
        for r in naive["requirements"]:
            for c in r["courses"]:
                shared[c] = r["requirement"]
        catalog = PROGRAMS["data-science-ba"]["requirements"]
        best = best_grades(transcript(seed, "data-science-ba"))
        for r in naive["requirements"]:
            r["courses"] = []
        for course, grade in best.items():
            home = next((q["id"] for q in catalog if course in q["courses"] and meets(grade, q["min_grade"])), None)
            if home:
                requirement(naive, home)["courses"].append(course)
        from plugin.audit import missing

        for q in catalog:
            r = requirement(naive, q["id"])
            r["missing"] = missing(q, r["courses"])
            r["satisfied"] = r["missing"] == 0
        if sum(r["satisfied"] for r in naive["requirements"]) < reference.best_satisfied:
            naive["graduation_ready"] = False
            result = verdict(given, naive, reference)
            assert result["valid"] is False and "best_placement" in result["details"]["failed_checks"]
            return
    raise AssertionError("no seed where the naive placement is worse")


def test_rejects_a_course_used_twice() -> None:
    given = task(4)
    audit, reference = gold(given)
    core = requirement(audit, "core")
    requirement(audit, "electives")["courses"].append(core["courses"][0])
    assert verdict(given, audit, reference)["valid"] is False


def test_rejects_a_course_that_does_not_belong_to_the_requirement() -> None:
    given = task(4)
    audit, reference = gold(given)
    requirement(audit, "theory")["courses"].append("HIST 101")
    result = verdict(given, audit, reference)
    assert result["valid"] is False and "does not count toward theory" in result["message"]


def test_rejects_a_course_never_taken() -> None:
    seed = find_seed("cs-bs", lambda rows, best: "COMP 448" not in best)
    given = task(seed)
    audit, reference = gold(given)
    requirement(audit, "electives")["courses"].append("COMP 448")
    result = verdict(given, audit, reference)
    assert result["valid"] is False and "not on the transcript" in result["message"]


def test_rejects_a_pass_grade_on_a_c_minus_requirement() -> None:
    def pass_on_major(rows, best):
        return any(g == "P" and c.startswith("COMP") for c, g in best.items())

    seed = find_seed("cs-bs", pass_on_major)
    given = task(seed)
    audit, reference = gold(given)
    course = next(c for c, g in best_grades(transcript(seed, "cs-bs")).items() if g == "P" and c.startswith("COMP"))
    home = next(q["id"] for q in PROGRAMS["cs-bs"]["requirements"] if course in q["courses"])
    requirement(audit, home)["courses"].append(course)
    result = verdict(given, audit, reference)
    assert result["valid"] is False and "does not meet" in result["message"]


def test_rejects_a_d_plus_on_a_c_minus_requirement() -> None:
    seed = find_seed("cs-bs", lambda rows, best: any(g == "D+" and c.startswith("COMP 1") for c, g in best.items()))
    given = task(seed)
    audit, reference = gold(given)
    course = next(c for c, g in best_grades(transcript(seed, "cs-bs")).items() if g == "D+" and c.startswith("COMP 1"))
    requirement(audit, "core")["courses"].append(course)
    assert verdict(given, audit, reference)["valid"] is False


def test_accepts_a_c_minus_exactly_on_a_c_minus_requirement() -> None:
    seed = find_seed("cs-bs", lambda rows, best: any(g == "C-" and c in PROGRAMS["cs-bs"]["requirements"][0]["courses"] for c, g in best.items()))
    given = task(seed)
    audit, reference = gold(given)
    course = next(c for c, g in best_grades(transcript(seed, "cs-bs")).items() if g == "C-" and c.startswith("COMP"))
    assert any(course in r["courses"] for r in audit["requirements"])
    assert verdict(given, audit, reference)["valid"] is True


def test_a_retake_counts_with_its_best_grade() -> None:
    def improved_retake(rows, best):
        firsts = {}
        for _, c, g in rows:
            if c in firsts and firsts[c] in ("F", "W") and g in ("A", "A-", "B+", "B") and c.startswith("COMP 1"):
                return True
            firsts.setdefault(c, g)
        return False

    seed = find_seed("cs-bs", improved_retake)
    given = task(seed)
    audit, reference = gold(given)
    assert verdict(given, audit, reference)["valid"] is True


def test_rejects_wrong_missing_and_satisfied_flags() -> None:
    seed = find_seed("cs-bs", lambda rows, best: True)
    given = task(seed)
    audit, reference = gold(given)
    wrong = copy.deepcopy(audit)
    wrong["requirements"][0]["missing"] += 1
    assert verdict(given, wrong, reference)["valid"] is False
    flipped = copy.deepcopy(audit)
    flipped["requirements"][1]["satisfied"] = not flipped["requirements"][1]["satisfied"]
    assert verdict(given, flipped, reference)["valid"] is False


def test_rejects_a_short_requirement_with_an_unused_qualifying_course() -> None:
    for seed in range(300):
        given = task(seed)
        audit, reference = gold(given)
        for r in audit["requirements"]:
            if r["satisfied"] and r["courses"]:
                dropped = copy.deepcopy(audit)
                q = requirement(dropped, r["requirement"])
                q["courses"] = q["courses"][:-1]
                spec = next(x for x in PROGRAMS["cs-bs"]["requirements"] if x["id"] == r["requirement"])
                from plugin.audit import missing

                q["missing"] = missing(spec, q["courses"])
                q["satisfied"] = q["missing"] == 0
                if not q["satisfied"]:
                    dropped["graduation_ready"] = False
                    result = verdict(given, dropped, reference)
                    assert result["valid"] is False and "unused" in result["message"]
                    return
    raise AssertionError("no audit to drop a course from")


def test_rejects_missing_misordered_and_unknown_requirements() -> None:
    given = task(4)
    audit, reference = gold(given)
    dropped = copy.deepcopy(audit)
    dropped["requirements"] = dropped["requirements"][1:]
    swapped = copy.deepcopy(audit)
    swapped["requirements"][0], swapped["requirements"][1] = swapped["requirements"][1], swapped["requirements"][0]
    renamed = copy.deepcopy(audit)
    renamed["requirements"][0]["requirement"] = "language"
    for bad in (dropped, swapped, renamed):
        assert verdict(given, bad, reference)["valid"] is False


def test_rejects_an_empty_audit() -> None:
    given = task(4)
    _, reference = gold(given)
    result = verdict(given, {"requirements": [], "total_credits": 0, "graduation_ready": False}, reference)
    assert result["valid"] is False and result["score"] < 0.5


@pytest.mark.parametrize("program", PROGRAMS_IDS)
def test_total_credits_exactly_at_the_line(program: str) -> None:
    from plugin.audit import total_credits

    seed = next(s for s in range(500) if total_credits(transcript(s, program)) == 120)
    given = task(seed, program)
    audit, reference = gold(given)
    assert verdict(given, audit, reference)["valid"] is True
    off = copy.deepcopy(audit)
    off["total_credits"] = 119
    assert verdict(given, off, reference)["valid"] is False


def test_rejects_a_wrong_graduation_answer() -> None:
    given = task(4)
    audit, reference = gold(given)
    audit["graduation_ready"] = not audit["graduation_ready"]
    assert verdict(given, audit, reference)["valid"] is False


def test_both_graduation_outcomes_occur() -> None:
    outcomes = {gold(task(seed, program))[0]["graduation_ready"] for program in PROGRAMS_IDS for seed in range(60)}
    assert outcomes == {True, False}


def test_rejects_a_tampered_answer_key() -> None:
    given = task(4)
    audit, reference = gold(given)
    reference.best_satisfied -= 1
    assert verdict(given, audit, reference)["valid"] is False
    assert verifier.verify_task("audit-degree", given, gold(given)[1].audit, None, ".")["valid"] is False


def test_input_and_tool_output_checks() -> None:
    from helpers import as_sandbox

    from contract import TranscriptOutput
    from plugin import get_transcript

    assert verifier.verify_input("get_catalog", task(-1))["valid"] is False
    given = task(4)
    made = as_sandbox(get_transcript(given, "."), TranscriptOutput)
    assert verifier.verify_output("get_transcript", given, made, ".")["valid"] is True
    made.attempts[0].grade = "A" if made.attempts[0].grade != "A" else "B"
    assert verifier.verify_output("get_transcript", given, made, ".")["valid"] is False
