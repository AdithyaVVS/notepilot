from datetime import date

import pytest

from app.deadlines import resolve_deadline

TODAY = date(2026, 11, 4)  # a Wednesday


@pytest.mark.parametrize(
    "text, expected",
    [
        ("today", date(2026, 11, 4)),
        ("tomorrow", date(2026, 11, 5)),
        ("by Friday", date(2026, 11, 6)),
        ("Wednesday", date(2026, 11, 11)),  # today is Wednesday, so next week's
        ("next Friday", date(2026, 11, 13)),
        ("next week", date(2026, 11, 9)),
        ("end of week", date(2026, 11, 6)),
        ("end of month", date(2026, 11, 30)),
        ("in 3 days", date(2026, 11, 7)),
        ("in 2 weeks", date(2026, 11, 18)),
        ("2026-11-20", date(2026, 11, 20)),
        ("20 Nov", date(2026, 11, 20)),
        ("Nov 20th", date(2026, 11, 20)),
        ("2 Nov", date(2027, 11, 2)),  # already passed this year, so next year
        ("31 Feb", None),
        ("whenever", None),
    ],
)
def test_resolve_deadline(text, expected):
    assert resolve_deadline(text, TODAY) == expected
