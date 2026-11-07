"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    GET_CATALOG = "get_catalog"
    GET_TRANSCRIPT = "get_transcript"
    PLACE_COURSES = "place_courses"
    PIN_AUDIT = "pin_audit"


class Task(Enum):
    AUDIT_DEGREE = "audit-degree"


class Program(Enum):
    CS_BS = "cs-bs"
    DATA_SCIENCE_BA = "data-science-ba"


class Kind(Enum):
    ALL = "all"
    CHOOSE = "choose"
    CREDITS = "credits"


TASK = "The task input, copied exactly as given"
COURSE = "A course code exactly as the catalog writes it, e.g. COMP 382"
REQUIREMENT = "A requirement's id exactly as the catalog gives it, e.g. theory"


@dataclass
class AuditInput(Output):
    seed: Annotated[int, "Which student: any integer from 0 to 1000000000; the same seed always gives the same transcript"]
    program: Annotated[Program, "The degree program audited: cs-bs or data-science-ba"]


@dataclass
class Requirement(Output):
    id: Annotated[str, REQUIREMENT]
    title: Annotated[str, "The requirement's name"]
    kind: Annotated[
        Kind,
        "all: every listed course; choose: at least `needed` of the listed courses; credits: listed courses worth at "
        "least `needed` credits in total",
    ]
    needed: Annotated[int, "all: how many courses are listed; choose: how many courses; credits: how many credits"]
    min_grade: Annotated[str, "The lowest grade that lets a course count here: C- or D-"]
    courses: Annotated[list[Annotated[str, COURSE]], "Every course that may count toward this requirement"]


@dataclass
class CatalogOutput(Output):
    program: Annotated[Program, "The program"]
    name: Annotated[str, "The degree's name"]
    total_credits: Annotated[int, "The credits a student needs in all to graduate, counting every passed course once"]
    grade_order: Annotated[list[str], "Every grade from best to worst"]
    requirements: Annotated[list[Requirement], "Every requirement of the degree, in the catalog's order"]


@dataclass
class Attempt(Output):
    term: Annotated[str, "The term it was taken, e.g. Fall 2023"]
    course: Annotated[str, COURSE]
    title: Annotated[str, "The course's title"]
    credits: Annotated[int, "The course's credits"]
    grade: Annotated[str, "The grade earned: A to D-, P (pass), F (fail) or W (withdrew)"]


@dataclass
class Course(Output):
    course: Annotated[str, COURSE]
    credits: Annotated[int, "The course's credits"]
    best_grade: Annotated[str, "Its best grade over every attempt"]
    counts_toward: Annotated[
        list[Annotated[str, REQUIREMENT]],
        "Every requirement it may count toward: listed there, with a best grade that meets that requirement's minimum",
    ]


@dataclass
class TranscriptOutput(Output):
    attempts: Annotated[list[Attempt], "Every course attempt, oldest term first; a course retaken appears once per attempt"]
    courses: Annotated[
        list[Course],
        "Every course that may count toward at least one requirement, by course code; a course in two or more "
        "requirements' lists must be placed in only one",
    ]
    passed_credits: Annotated[int, "The credits of every course passed (best grade not F or W), each course once"]


@dataclass
class RequirementResult(Output):
    requirement: Annotated[str, REQUIREMENT]
    satisfied: Annotated[bool, "true when the courses applied here meet the requirement"]
    courses: Annotated[list[Annotated[str, COURSE]], "The courses applied to this requirement, each used by no other requirement"]
    missing: Annotated[
        int,
        "What is still needed with these courses: all and choose, how many more courses; credits, how many more "
        "credits; 0 when satisfied",
    ]


@dataclass
class AuditOutput(Output):
    requirements: Annotated[list[RequirementResult], "One result per requirement of the catalog, in the catalog's order"]
    total_credits: Annotated[int, "The credits of every course passed, each course counted once"]
    graduation_ready: Annotated[bool, "true when every requirement is satisfied and total_credits reaches the program's total"]


@dataclass
class Placement(Output):
    course: Annotated[str, COURSE]
    requirement: Annotated[str, "The requirement it is applied to: one of the course's counts_toward"]


@dataclass
class PlaceInput(Output):
    task: Annotated[AuditInput, TASK]
    placements: Annotated[
        list[Placement],
        "Where each course with two or more requirements in counts_toward goes, each such course once; courses with "
        "one requirement go to it on their own",
    ]


@dataclass
class PlaceOutput(Output):
    file: Annotated[str, "The saved audit, relative to the workspace"]
    satisfied: Annotated[int, "How many requirements this placement satisfies"]
    audit: Annotated[AuditOutput, "The audit this placement gives: submit it as it is"]


@dataclass
class PinOutput(Output):
    data_sha256: Annotated[str, "sha256 of the catalog and the transcript as canonical JSON"]
    best_satisfied: Annotated[int, "The most requirements any legal placement of the courses satisfies"]
    audit: Annotated[AuditOutput, "One audit that satisfies that many requirements"]


TOOLS = {
    Tool.GET_CATALOG: (AuditInput, CatalogOutput),
    Tool.GET_TRANSCRIPT: (AuditInput, TranscriptOutput),
    Tool.PLACE_COURSES: (PlaceInput, PlaceOutput),
    Tool.PIN_AUDIT: (AuditInput, PinOutput),
}
TASKS = {Task.AUDIT_DEGREE: (AuditInput, AuditOutput)}
