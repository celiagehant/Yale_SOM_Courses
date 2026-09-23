"""The two tools the course agent is allowed to use.

1. ``search_courses`` — a local function tool over ``data/yale_som_classes.json``
2. ``WEB_SEARCH_TOOL`` — OpenAI's native web search, run provider-side

Only these two. ``agent.py`` wires both onto the agent.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_ai import WebSearchTool

from models import Course, CourseMatch, CourseSearchResult

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "yale_som_classes.json"

MAX_RESULTS = 15

# Normalizes whatever the user typed for a weekday into the JSON's "Mo,Tu,We,Th,Fr" codes.
DAY_CODES: dict[str, str] = {
    "monday": "mo",
    "mon": "mo",
    "mo": "mo",
    "m": "mo",
    "tuesday": "tu",
    "tues": "tu",
    "tue": "tu",
    "tu": "tu",
    "t": "tu",
    "wednesday": "we",
    "wed": "we",
    "we": "we",
    "w": "we",
    "thursday": "th",
    "thurs": "th",
    "thur": "th",
    "thu": "th",
    "th": "th",
    "friday": "fr",
    "fri": "fr",
    "fr": "fr",
    "f": "fr",
    "saturday": "sa",
    "sat": "sa",
    "sa": "sa",
    "sunday": "su",
    "sun": "su",
    "su": "su",
}


@lru_cache(maxsize=1)
def load_courses() -> tuple[Course, ...]:
    """Read and validate every row once, then reuse it."""
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return tuple(Course.model_validate(row) for row in rows)


def _fields_matching(course: Course, term: str) -> list[str]:
    """Which named fields contain ``term`` — used to explain a match."""
    checks = {
        "number": course.number,
        "title": course.title,
        "faculty": course.faculty,
        "category": course.category,
        "type": course.course_type,
        "session": course.session,
        "daytimes": course.daytimes,
        "description": course.description,
        "faculty_bio": course.faculty_bio,
    }
    return [name for name, value in checks.items() if term in value.lower()]


def search_courses(
    query: str,
    day: str | None = None,
    category: str | None = None,
    faculty: str | None = None,
    limit: int = MAX_RESULTS,
) -> CourseSearchResult:
    """Search the Yale SOM course catalog.

    Use this for anything answerable from the catalog: course titles, course
    numbers, who teaches what, meeting days and times, sessions, units,
    bidding/permission, course descriptions, and faculty bios.

    Args:
        query: Free text to look for, e.g. "negotiation", "MGT 401",
            "DiBenigno", "sustainability". Every word must appear somewhere in
            the course row. Pass an empty string to browse with filters only.
        day: Optional weekday filter, e.g. "Monday", "Tue", "Th".
        category: Optional filter on subject area or course type. Subject areas
            include Finance, Marketing, Operations, Strategy, Accounting,
            Economics, Organizational Behavior, Artificial Intelligence,
            Healthcare Management, Real Estate, and more. Course types include
            "core", "elective", "EMBA", "PhD", "MAM", and the MMS programs.
            Matches against either field.
        faculty: Optional instructor name filter, e.g. "Simonsohn".
        limit: Maximum courses to return (capped at 15).

    Returns:
        Matching courses with the fields each one matched on.
    """
    courses = load_courses()
    terms = [t for t in query.lower().split() if t]

    day_code: str | None = None
    if day and day.strip():
        day_code = DAY_CODES.get(day.strip().lower())
        if day_code is None:
            # Never silently drop a filter — that would return every course and
            # read like a real answer.
            return CourseSearchResult(
                query=query,
                total_matches=0,
                returned=0,
                note=(
                    f"Could not read {day!r} as a weekday. Use a name or "
                    "abbreviation like 'Monday', 'Tue', or 'Th'."
                ),
            )

    category_term = category.strip().lower() if category else None
    faculty_term = faculty.strip().lower() if faculty else None

    matches: list[CourseMatch] = []
    for course in courses:
        haystack = course.haystack()

        if any(term not in haystack for term in terms):
            continue
        if day_code and day_code not in course.day_codes():
            continue
        # "Core"/"Elective" live in Course Type; subject areas live in Course
        # Category — so one filter checks both fields.
        if category_term and not (
            category_term in course.category.lower()
            or category_term in course.course_type.lower()
        ):
            continue
        if faculty_term and faculty_term not in course.faculty.lower():
            continue

        matched_on: list[str] = []
        for term in terms:
            for field in _fields_matching(course, term):
                if field not in matched_on:
                    matched_on.append(field)
        matches.append(CourseMatch(course=course, matched_on=matched_on))

    capped = max(1, min(limit, MAX_RESULTS))
    return CourseSearchResult(
        query=query,
        total_matches=len(matches),
        returned=min(len(matches), capped),
        truncated=len(matches) > capped,
        matches=matches[:capped],
    )


# OpenAI's native web search, executed by the provider rather than by us.
# For faculty news, syllabus context, or anything the catalog JSON can't answer.
WEB_SEARCH_TOOL = WebSearchTool(search_context_size="medium")
