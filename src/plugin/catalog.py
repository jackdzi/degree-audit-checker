"""The two degree catalogs, the grade rules, and the seeded transcripts, as plain data.

The verifier keeps its own copy of this file (verifier/catalog.py, the same but for its import
line): it may not import the plugin, and it rebuilds each transcript itself.
"""

from plugin.rng import Stream

TOTAL_CREDITS = 120
GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "P", "F", "W"]

COURSES = {
    "COMP 140": ("Computational Thinking", 4),
    "COMP 182": ("Algorithmic Thinking", 4),
    "COMP 215": ("Program Design", 4),
    "COMP 222": ("Computer Organization", 4),
    "COMP 321": ("Computer Systems", 4),
    "COMP 310": ("Software Engineering", 3),
    "COMP 330": ("Tools and Models for Data Science", 3),
    "COMP 340": ("Human-Computer Interaction", 3),
    "COMP 382": ("Reasoning about Algorithms", 3),
    "COMP 409": ("Logic in Computer Science", 3),
    "COMP 481": ("Automata and Formal Languages", 3),
    "COMP 410": ("Operating Systems", 4),
    "COMP 412": ("Compiler Construction", 4),
    "COMP 421": ("Distributed Systems", 3),
    "COMP 440": ("Artificial Intelligence", 3),
    "COMP 441": ("Large-Scale Machine Learning", 3),
    "COMP 447": ("Cryptography", 3),
    "COMP 448": ("Computer Graphics", 3),
    "COMP 487": ("Computer Vision", 3),
    "MATH 101": ("Calculus I", 3),
    "MATH 102": ("Calculus II", 3),
    "MATH 354": ("Linear Algebra", 3),
    "MATH 355": ("Matrix Analysis", 3),
    "STAT 310": ("Probability and Statistics", 3),
    "STAT 315": ("Statistics for Data Science", 4),
    "STAT 405": ("Statistical Computing", 3),
    "STAT 413": ("Statistical Learning", 3),
    "STAT 421": ("Time Series Analysis", 3),
    "DSCI 301": ("Data Science Tools", 3),
    "DSCI 435": ("Data Science Capstone", 4),
    "ELEC 303": ("Random Signals", 3),
    "PHYS 101": ("Mechanics", 4),
    "PHYS 102": ("Electricity and Magnetism", 4),
    "CHEM 121": ("General Chemistry I", 4),
    "CHEM 122": ("General Chemistry II", 4),
    "BIOS 201": ("Cell Biology", 3),
    "ESCI 101": ("Earth Systems", 3),
    "ECON 100": ("Principles of Economics", 3),
    "ECON 309": ("Econometrics", 3),
    "BIOS 325": ("Genomics", 3),
    "POLI 209": ("Political Methods", 3),
    "HIST 101": ("World History", 3),
    "HIST 102": ("Modern History", 3),
    "ENGL 103": ("Academic Writing", 3),
    "ENGL 210": ("American Literature", 3),
    "ARTS 150": ("Drawing", 3),
    "ARTS 160": ("Photography", 3),
    "PHIL 101": ("Introduction to Philosophy", 3),
    "PHIL 205": ("Ethics", 3),
    "MUSI 110": ("Music Theory", 3),
    "MUSI 120": ("Music History", 3),
    "SPAN 101": ("Elementary Spanish", 3),
    "SPAN 102": ("Elementary Spanish II", 3),
    "FREN 101": ("Elementary French", 3),
    "PSYC 101": ("Introduction to Psychology", 3),
    "SOCI 101": ("Introduction to Sociology", 3),
    "ANTH 201": ("Cultural Anthropology", 3),
    "FILM 220": ("Film History", 3),
    "RELI 101": ("World Religions", 3),
    "LING 200": ("Introduction to Linguistics", 3),
    "CLAS 110": ("Greek Myth", 3),
    "ARCH 101": ("Architecture and Society", 3),
    "THEA 101": ("Acting", 3),
    "GEOG 101": ("World Geography", 3),
    "SOCI 230": ("Urban Sociology", 3),
    "ENGL 220": ("Creative Writing", 3),
    "HIST 230": ("History of Science", 3),
    "ASIA 101": ("Asian Civilizations", 3),
    "AFAM 101": ("African American Studies", 3),
    "WGSS 101": ("Gender Studies", 3),
    "PHIL 210": ("Philosophy of Mind", 3),
    "KINE 105": ("Fitness", 1),
}
GENERAL = ["HIST 101", "HIST 102", "ENGL 103", "ENGL 210", "ARTS 150", "ARTS 160", "PHIL 101", "PHIL 205", "MUSI 110", "MUSI 120", "SPAN 101", "SPAN 102", "FREN 101", "PSYC 101", "SOCI 101", "ANTH 201", "FILM 220", "RELI 101", "LING 200", "CLAS 110", "ARCH 101", "THEA 101", "GEOG 101", "SOCI 230", "ENGL 220", "HIST 230", "ASIA 101", "AFAM 101", "WGSS 101", "PHIL 210", "KINE 105"]


def requirement(id, title, kind, needed, min_grade, courses):
    return {"id": id, "title": title, "kind": kind, "needed": needed, "min_grade": min_grade, "courses": courses}


ELECTIVES_CS = ["COMP 310", "COMP 330", "COMP 340", "COMP 382", "COMP 409", "COMP 410", "COMP 412", "COMP 421",
                "COMP 440", "COMP 441", "COMP 447", "COMP 448", "COMP 481", "COMP 487"]
PROGRAMS = {
    "cs-bs": {
        "name": "B.S. in Computer Science",
        "requirements": [
            requirement("core", "Computer Science Core", "all", 5, "C-", ["COMP 140", "COMP 182", "COMP 215", "COMP 222", "COMP 321"]),
            requirement("math", "Mathematics", "all", 3, "C-", ["MATH 101", "MATH 102", "MATH 354"]),
            requirement("statistics", "Statistics", "choose", 1, "C-", ["STAT 310", "STAT 315", "ELEC 303"]),
            requirement("theory", "Theory", "choose", 1, "C-", ["COMP 382", "COMP 409", "COMP 481"]),
            requirement("systems", "Systems", "choose", 1, "C-", ["COMP 410", "COMP 412", "COMP 421"]),
            requirement("electives", "Upper-Level Electives", "credits", 12, "C-", ELECTIVES_CS),
            requirement("science", "Natural Science", "credits", 8, "D-", ["PHYS 101", "PHYS 102", "CHEM 121", "CHEM 122", "BIOS 201", "ESCI 101"]),
        ],
    },
    "data-science-ba": {
        "name": "B.A. in Data Science",
        "requirements": [
            requirement("core", "Data Science Core", "all", 4, "C-", ["COMP 140", "STAT 310", "DSCI 301", "MATH 355"]),
            requirement("programming", "Programming", "choose", 1, "C-", ["COMP 182", "COMP 215"]),
            requirement("modeling", "Statistical Modeling", "choose", 2, "C-", ["STAT 405", "STAT 413", "STAT 421", "STAT 315"]),
            requirement("learning", "Machine Learning", "choose", 1, "C-", ["COMP 440", "COMP 441", "STAT 413"]),
            requirement("electives", "Data Electives", "credits", 9, "C-",
                        ["COMP 330", "COMP 441", "COMP 487", "STAT 421", "STAT 405", "DSCI 435", "COMP 382", "ECON 309"]),
            requirement("domain", "Domain Area", "credits", 6, "D-", ["ECON 100", "ECON 309", "BIOS 201", "BIOS 325", "POLI 209", "PSYC 101"]),
            requirement("capstone", "Capstone", "all", 1, "C-", ["DSCI 435"]),
        ],
    },
}
TERMS = [f"{season} {year}" for year in range(2022, 2027) for season in ("Spring", "Fall")][1:]


def program_courses(program):
    seen = []
    for req in PROGRAMS[program]["requirements"]:
        for course in req["courses"]:
            if course not in seen:
                seen.append(course)
    return seen


def draw_grade(stream, general):
    """A grade: mostly A to B-, some on the C-/D+ line, a few F, W and P (pass), P mostly in general courses."""
    roll = stream.below(100)
    if roll < 10 if general else roll < 3:
        return "P"
    if roll < 72:
        return stream.choice(["A", "A-", "B+", "B", "B-"])
    if roll < 86:
        return stream.choice(["C+", "C", "C-", "C-"])
    if roll < 92:
        return stream.choice(["D+", "D", "D-"])
    if roll < 96:
        return "F"
    return "W"


def transcript(seed, program):
    """The student's attempts as [term, course, grade], oldest term first.

    How far along the student is (from the seed) sets how much of each requirement they took; some
    take extra courses that fit two requirements, so placing them matters; failed, withdrawn and
    low grades are sometimes retaken a later term; general courses fill the credits, and about a
    fifth of seeds aim the passed credits at exactly 120.
    """
    stream = Stream("degree", f"{seed}|{program}")
    progress = stream.choice([60, 80, 90, 100, 100, 100])
    taken = []
    for req in PROGRAMS[program]["requirements"]:
        options = stream.shuffled(req["courses"])
        if req["kind"] == "all":
            count = sum(1 for _ in options if stream.chance(progress, 100))
        elif req["kind"] == "choose":
            count = min(len(options), req["needed"] + stream.between(-1, 1) if progress < 100 else req["needed"] + stream.between(0, 1))
        else:
            count, credits = 0, 0
            target = req["needed"] * progress // 100 + (stream.between(-3, 4) if progress < 100 else stream.between(0, 4))
            while count < len(options) and credits < target:
                credits += COURSES[options[count]][1]
                count += 1
        taken += [c for c in options[:count] if c not in taken]
    attempts = []
    for course in stream.shuffled(taken):
        grade = draw_grade(stream, general=False)
        attempts.append([course, grade])
        if grade in ("F", "W", "P", "D+", "D", "D-") and (progress == 100 or stream.chance(2, 3)):
            attempts.append([course, draw_grade(stream, general=False)])
    target = stream.choice([TOTAL_CREDITS, TOTAL_CREDITS, TOTAL_CREDITS - 3, 110, 124, 130])
    general = [c for c in stream.shuffled(GENERAL) if c not in taken]
    passed = {}
    for course, grade in attempts:
        if grade not in ("F", "W"):
            passed[course] = COURSES[course][1]
    for course in general:
        credits = sum(passed.values())
        if credits >= target:
            break
        grade = draw_grade(stream, general=True)
        if credits + COURSES[course][1] > target and target == TOTAL_CREDITS and grade not in ("F", "W"):
            continue
        attempts.append([course, grade])
        if grade not in ("F", "W"):
            passed[course] = COURSES[course][1]
    # Terms: each attempt in a term from the first on, a retake always in a later term than the first try.
    term_of, dated = {}, []
    for course, grade in attempts:
        if course in term_of:
            earliest = term_of[course] + 1
            term = earliest + stream.below(len(TERMS) - earliest)
        else:
            term = stream.below(len(TERMS) - 1)
        term_of[course] = term
        dated.append([term, course, grade])
    dated = sorted(dated, key=lambda row: (row[0], row[1], GRADES.index(row[2])))
    return [[TERMS[term], course, grade] for term, course, grade in dated]
