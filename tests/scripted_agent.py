"""A scripted stand-in for the agent: it follows the task's instructions with no model, so a whole
run can be replayed offline. It reads only what get_catalog and get_transcript return."""

from __future__ import annotations

from itertools import product


def audit_from(catalog: dict, transcript: dict) -> dict:
    order = catalog["grade_order"]
    best: dict[str, str] = {}
    credits: dict[str, int] = {}
    for attempt in transcript["attempts"]:
        course, grade = attempt["course"], attempt["grade"]
        credits[course] = attempt["credits"]
        if course not in best or order.index(grade) < order.index(best[course]):
            best[course] = grade

    def counts(grade: str, minimum: str) -> bool:
        if grade in ("F", "W"):
            return False
        return minimum == "D-" if grade == "P" else order.index(grade) <= order.index(minimum)

    reqs = catalog["requirements"]
    homes = {c: [r["id"] for r in reqs if c in r["courses"] and counts(g, r["min_grade"])] for c, g in best.items()}

    def short(req: dict, applied: list[str]) -> int:
        have = sum(credits[c] for c in applied) if req["kind"] == "credits" else len(applied)
        return max(0, req["needed"] - have)

    shared = [c for c, ids in homes.items() if len(ids) > 1]
    best_placement, best_count = None, -1
    for choice in product(*(homes[c] for c in shared)):
        placed = {r["id"]: [c for c in r["courses"] if homes.get(c) == [r["id"]]] for r in reqs}
        for course, home in zip(shared, choice):
            placed[home].append(course)
        count = sum(1 for r in reqs if short(r, placed[r["id"]]) == 0)
        if count > best_count:
            best_placement, best_count = placed, count
    results = [
        {"requirement": r["id"], "satisfied": short(r, best_placement[r["id"]]) == 0, "courses": best_placement[r["id"]],
         "missing": short(r, best_placement[r["id"]])}
        for r in reqs
    ]
    total = sum(credits[c] for c, g in best.items() if g not in ("F", "W"))
    return {
        "requirements": results,
        "total_credits": total,
        "graduation_ready": best_count == len(reqs) and total >= catalog["total_credits"],
    }
