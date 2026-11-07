"""A scripted stand-in for the agent: it follows the task's instructions with no model, so a whole
run can be replayed offline. It reads only what get_catalog and get_transcript return, and decides
where each shared course goes by trying every placement."""

from __future__ import annotations

from itertools import product


def placements_from(catalog: dict, transcript: dict) -> list[dict]:
    reqs = catalog["requirements"]
    courses = {c["course"]: c for c in transcript["courses"]}
    shared = sorted(c for c, info in courses.items() if len(info["counts_toward"]) > 1)

    def satisfied(choice: dict[str, str]) -> int:
        placed = {r["id"]: [] for r in reqs}
        for course, info in courses.items():
            placed[choice.get(course, info["counts_toward"][0])].append(course)
        count = 0
        for r in reqs:
            have = sum(courses[c]["credits"] for c in placed[r["id"]]) if r["kind"] == "credits" else len(placed[r["id"]])
            count += have >= r["needed"]
        return count

    best = max(
        (dict(zip(shared, homes)) for homes in product(*(courses[c]["counts_toward"] for c in shared))),
        key=satisfied,
        default={},
    )
    return [{"course": course, "requirement": requirement} for course, requirement in best.items()]
