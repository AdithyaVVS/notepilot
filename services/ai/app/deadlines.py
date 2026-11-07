import calendar
import re
from datetime import date, timedelta

WEEKDAYS = {name.lower(): i for i, name in enumerate(calendar.day_name)}
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})


def _next_weekday(today: date, weekday: int) -> date:
    """The next given weekday strictly after today."""
    return today + timedelta(days=(weekday - today.weekday() - 1) % 7 + 1)


def _calendar_date(today: date, month_name: str, day: str, year: str | None):
    month = MONTHS.get(month_name)
    if month is None:
        return None
    try:
        if year:
            return date(int(year), month, int(day))
        result = date(today.year, month, int(day))
        if result < today:
            result = date(today.year + 1, month, int(day))
        return result
    except ValueError:
        return None


def resolve_deadline(text: str, today: date) -> date | None:
    """Turn wording like 'by Friday' into a date, or None if we can't be sure."""
    t = re.sub(r"\s+", " ", text.strip().lower()).rstrip(".")
    t = re.sub(r"^(by|before|on|until|due)\s+", "", t)
    t = re.sub(r"^this\s+", "", t)

    if t in {"today", "tonight", "eod", "end of day", "end of the day"}:
        return today
    if t == "tomorrow":
        return today + timedelta(days=1)
    if t in {"end of week", "end of the week", "eow"}:
        return today + timedelta(days=(4 - today.weekday()) % 7)
    if t in {"end of month", "end of the month", "eom"}:
        return today.replace(day=calendar.monthrange(today.year, today.month)[1])
    if t == "next week":
        return _next_weekday(today, 0)

    match = re.fullmatch(r"next (\w+)", t)
    if match and match.group(1) in WEEKDAYS:
        return _next_weekday(today, 0) + timedelta(days=WEEKDAYS[match.group(1)])
    if t in WEEKDAYS:
        return _next_weekday(today, WEEKDAYS[t])

    match = re.fullmatch(r"in (\d{1,3}) (day|days|week|weeks)", t)
    if match:
        unit = 7 if match.group(2).startswith("week") else 1
        return today + timedelta(days=int(match.group(1)) * unit)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        try:
            return date.fromisoformat(t)
        except ValueError:
            return None

    match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)? ([a-z]+)(?:,? (\d{4}))?", t)
    if match:
        return _calendar_date(today, match.group(2), match.group(1), match.group(3))
    match = re.fullmatch(r"([a-z]+) (\d{1,2})(?:st|nd|rd|th)?(?:,? (\d{4}))?", t)
    if match:
        return _calendar_date(today, match.group(1), match.group(2), match.group(3))
    return None
