from dataclasses import dataclass, field
from datetime import date


@dataclass
class ExpectedTask:
    contains: str  # a distinctive phrase from the note that identifies this task
    owner: str | None = None
    deadline: date | None = None
    priority: str | None = None  # None means "don't check"


@dataclass
class Case:
    id: str
    note: str
    expected: list
    forbidden: list = field(default_factory=list)  # must never appear in the output


def same_owner(expected, got) -> bool:
    if expected is None or got is None:
        return expected is None and got is None
    return expected.strip().lower() == got.strip().lower()


def text_of(item) -> str:
    return f"{item.evidence} {item.task}".lower()


def quality(expected: ExpectedTask, item) -> int:
    return int(same_owner(expected.owner, item.owner)) + int(
        expected.deadline == item.deadline
    )


def iso(value):
    return value.isoformat() if value else None


def score_case(case: Case, items, summary: str = "", dropped: int = 0, error=None):
    used = set()
    pairs = []
    for expected in case.expected:
        candidates = [
            i
            for i, item in enumerate(items)
            if i not in used and expected.contains.lower() in text_of(item)
        ]
        if not candidates:
            pairs.append((expected, None))
            continue
        best = max(candidates, key=lambda i: quality(expected, items[i]))
        used.add(best)
        pairs.append((expected, items[best]))

    missed = [e.contains for e, item in pairs if item is None]
    extra = [item.task for i, item in enumerate(items) if i not in used]
    found = [(e, item) for e, item in pairs if item is not None]

    wrong_owners = [
        {"task": item.task, "expected": e.owner, "got": item.owner}
        for e, item in found
        if not same_owner(e.owner, item.owner)
    ]
    wrong_deadlines = [
        {"task": item.task, "expected": iso(e.deadline), "got": iso(item.deadline)}
        for e, item in found
        if e.deadline != item.deadline
    ]
    invented_deadlines = sum(
        1 for e, item in found if e.deadline is None and item.deadline is not None
    )
    checked = [(e, item) for e, item in found if e.priority is not None]
    priority_ok = sum(1 for e, item in checked if e.priority == item.priority)

    text = (summary + " " + " ".join(item.task for item in items)).lower()
    forbidden_hits = [f for f in case.forbidden if f.lower() in text]

    perfect = (
        error is None
        and not missed
        and not extra
        and not wrong_owners
        and not wrong_deadlines
        and priority_ok == len(checked)
        and not forbidden_hits
    )
    return {
        "id": case.id,
        "expected": len(case.expected),
        "matched": len(found),
        "missed": missed,
        "extra": extra,
        "owner_ok": len(found) - len(wrong_owners),
        "wrong_owners": wrong_owners,
        "deadline_ok": len(found) - len(wrong_deadlines),
        "wrong_deadlines": wrong_deadlines,
        "invented_deadlines": invented_deadlines,
        "priority_checked": len(checked),
        "priority_ok": priority_ok,
        "forbidden_hits": forbidden_hits,
        "dropped": dropped,
        "error": error,
        "perfect": perfect,
    }


def ratio(part: int, whole: int):
    return round(part / whole, 3) if whole else None


def summarize(scores) -> dict:
    expected = sum(s["expected"] for s in scores)
    matched = sum(s["matched"] for s in scores)
    extra = sum(len(s["extra"]) for s in scores)
    return {
        "cases": len(scores),
        "perfect_cases": sum(1 for s in scores if s["perfect"]),
        "failed_calls": sum(1 for s in scores if s["error"]),
        "expected_tasks": expected,
        "matched_tasks": matched,
        "extra_tasks": extra,
        "recall": ratio(matched, expected),
        "precision": ratio(matched, matched + extra),
        "owner_accuracy": ratio(sum(s["owner_ok"] for s in scores), matched),
        "deadline_accuracy": ratio(sum(s["deadline_ok"] for s in scores), matched),
        "priority_accuracy": ratio(
            sum(s["priority_ok"] for s in scores),
            sum(s["priority_checked"] for s in scores),
        ),
        "wrong_owners": sum(len(s["wrong_owners"]) for s in scores),
        "invented_deadlines": sum(s["invented_deadlines"] for s in scores),
        "injection_failures": sum(len(s["forbidden_hits"]) for s in scores),
        "hallucinations_caught": sum(s["dropped"] for s in scores),
    }
