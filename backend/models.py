"""Pydantic data objects shared by the tools, the agent, and the API.

The raw rows in ``data/yale_som_classes.json`` use spaced, title-cased keys
("Course Title", "Faculty 1", ...). ``Course`` mirrors those rows with tidy
snake_case attributes so ``tools.py`` and ``agent.py`` can work with real
objects instead of loose dicts.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# "Daytimes" packs the days into a prefix like "T  Th 1:00 PM-2:20 PM".
_DAYTIME_TOKENS = {
    "M": "mo",
    "T": "tu",
    "W": "we",
    "Th": "th",
    "F": "fr",
    "Sa": "sa",
    "Su": "su",
}


class Course(BaseModel):
    """One row of ``yale_som_classes.json``."""

    model_config = ConfigDict(populate_by_name=True)

    course_id: str = Field(default="", alias="Course ID")
    number: str = Field(default="", alias="Course Number")
    title: str = Field(default="", alias="Course Title")
    section: str = Field(default="", alias="Section")
    category: str = Field(default="", alias="Course Category")
    course_type: str = Field(default="", alias="Course Type")
    units: str = Field(default="", alias="Units")

    description: str = Field(default="", alias="Course Description")

    faculty: str = Field(default="", alias="Faculty 1")
    faculty_email: str = Field(default="", alias="Faculty 1 Email")
    faculty_bio: str = Field(default="", alias="faculty_bio")

    daytimes: str = Field(default="", alias="Daytimes")
    days: str = Field(default="", alias="Timings Day")
    start_time: str = Field(default="", alias="Timings StartTime")
    end_time: str = Field(default="", alias="Timings EndTime")
    room: str = Field(default="", alias="Room")

    session: str = Field(default="", alias="Course Session")
    session_start: str = Field(default="", alias="Course Session Start date")
    session_end: str = Field(default="", alias="Course Session End Date")
    term_code: str = Field(default="", alias="TermCode")

    bid_or_permission: str = Field(default="", alias="Bid Or Permission")
    syllabus: str = Field(default="", alias="Syllabus")
    old_syllabus: str = Field(default="", alias="Old Syllabus")

    def day_codes(self) -> set[str]:
        """Weekdays this course meets, as lowercase two-letter codes.

        Only 25 of the 234 rows fill in "Timings Day"; the rest keep their days
        inside the "Daytimes" string, so fall back to parsing that.
        """
        codes = {c.strip().lower() for c in self.days.split(",") if c.strip()}
        if codes:
            return codes

        daytimes = self.daytimes.strip()
        if not daytimes:
            return set()
        head = re.split(r"\d", daytimes, maxsplit=1)[0]
        return {
            _DAYTIME_TOKENS[token]
            for token in head.split()
            if token in _DAYTIME_TOKENS
        }

    def haystack(self) -> str:
        """Lowercased blob of the searchable fields."""
        parts = (
            self.number,
            self.title,
            self.category,
            self.course_type,
            self.faculty,
            self.faculty_email,
            self.daytimes,
            self.days,
            self.session,
            self.room,
            self.description,
            self.faculty_bio,
        )
        return " ".join(parts).lower()

    def summary(self) -> str:
        """Compact one-liner used when reporting a tool result in the audit."""
        return f"{self.number} {self.title} ({self.faculty or 'TBD'})".strip()


class CourseMatch(BaseModel):
    """A course the search tool decided to return, plus why it matched."""

    course: Course
    matched_on: list[str] = Field(default_factory=list)


class CourseSearchResult(BaseModel):
    """What ``search_courses`` hands back to the model."""

    query: str
    total_matches: int
    returned: int
    truncated: bool = False
    matches: list[CourseMatch] = Field(default_factory=list)
    note: str = ""
    """Set when a filter could not be applied, so a zero result is never
    mistaken for "no such course"."""


class AgentResult(BaseModel):
    """The shape ``main.py`` expects from ``run_agent``."""

    reply: str
    tools_used: list[str] = Field(default_factory=list)


class AuditToolCall(BaseModel):
    """One tool invocation inside an agent loop."""

    tool: str
    args: dict[str, Any] | str = Field(default_factory=dict)
    result: str = ""


class AuditEntry(BaseModel):
    """One appended row of ``output/audit_trail.json``."""

    time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    user_message: str
    thoughts: list[str] = Field(default_factory=list)
    tool_calls: list[AuditToolCall] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    reply: str = ""
    stop_reason: str = ""
