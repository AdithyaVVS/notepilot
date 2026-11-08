from datetime import date
from types import SimpleNamespace

from evaluation.cases import CASES
from evaluation.scoring import Case, ExpectedTask, score_case, summarize

FRI = date(2026, 11, 6)


def item(task, evidence=None, owner=None, deadline=None, priority="medium"):
    return SimpleNamespace(
        task=task,
        evidence=evidence or task,
        owner=owner,
        deadline=deadline,
        priority=priority,
    )


def test_cases_are_well_formed():
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids)) == 16
    assert sum(len(case.expected) for case in CASES) == 32
    for case in CASES:
        assert 10 <= len(case.note) <= 6000, case.id
        for expected in case.expected:
            assert expected.contains.lower() in case.note.lower(), (
                case.id,
                expected.contains,
            )


def test_a_correct_answer_scores_perfect():
    case = Case("c", "x", [ExpectedTask("budget", "Priya", FRI)])
    score = score_case(case, [item("Send budget", owner="Priya", deadline=FRI)])
    assert score["perfect"] is True
    assert summarize([score])["recall"] == 1.0


def test_missed_and_extra_tasks_are_reported():
    case = Case("c", "x", [ExpectedTask("budget"), ExpectedTask("roadmap")])
    score = score_case(case, [item("Send budget"), item("Water the plants")])
    assert score["missed"] == ["roadmap"]
    assert score["extra"] == ["Water the plants"]
    assert score["perfect"] is False


def test_wrong_owner_and_invented_deadline_are_counted():
    case = Case("c", "x", [ExpectedTask("budget", None, None)])
    score = score_case(case, [item("Send budget", owner="Someone", deadline=FRI)])
    assert score["wrong_owners"] == [
        {"task": "Send budget", "expected": None, "got": "Someone"}
    ]
    assert score["invented_deadlines"] == 1
    assert score["deadline_ok"] == 0


def test_owner_comparison_ignores_case():
    case = Case("c", "x", [ExpectedTask("invoice", "Sneha")])
    score = score_case(case, [item("Send the invoice", owner="sneha")])
    assert score["owner_ok"] == 1


def test_each_returned_task_matches_only_one_expected():
    case = Case("c", "x", [ExpectedTask("budget"), ExpectedTask("budget")])
    score = score_case(case, [item("Send budget")])
    assert score["matched"] == 1
    assert score["missed"] == ["budget"]


def test_best_candidate_is_preferred_among_duplicates():
    case = Case("c", "x", [ExpectedTask("budget", "Priya", FRI)])
    weak = item("Send budget", owner="Priya", deadline=None)
    strong = item("Send budget again", owner="Priya", deadline=FRI)
    score = score_case(case, [weak, strong])
    assert score["deadline_ok"] == 1  # picked the right one
    assert score["extra"] == ["Send budget"]  # the leftover duplicate counts as extra


def test_forbidden_text_is_flagged():
    case = Case("c", "x", [], forbidden=["hacked"])
    score = score_case(case, [item("Reply with HACKED")], summary="all fine")
    assert score["forbidden_hits"] == ["hacked"]
    clean = score_case(case, [], summary="HACKED")
    assert clean["forbidden_hits"] == ["hacked"]


def test_priority_is_only_checked_when_expected():
    case = Case(
        "c",
        "x",
        [ExpectedTask("restart", priority="high"), ExpectedTask("wiki")],
    )
    score = score_case(
        case, [item("Restart it", priority="low"), item("Tidy wiki", priority="high")]
    )
    assert score["priority_checked"] == 1
    assert score["priority_ok"] == 0


def test_a_failed_call_counts_every_task_as_missed():
    case = Case("c", "x", [ExpectedTask("budget"), ExpectedTask("roadmap")])
    score = score_case(case, [], error="No valid reply")
    assert score["missed"] == ["budget", "roadmap"]
    assert summarize([score])["failed_calls"] == 1


def test_summary_totals():
    one = Case("a", "x", [ExpectedTask("budget", "Priya"), ExpectedTask("roadmap")])
    two = Case("b", "x", [ExpectedTask("slides")])
    scores = [
        score_case(one, [item("Send budget", owner="Priya"), item("Extra thing")]),
        score_case(two, [item("Share slides")], dropped=2),
    ]
    summary = summarize(scores)
    assert summary["expected_tasks"] == 3
    assert summary["matched_tasks"] == 2
    assert summary["extra_tasks"] == 1
    assert summary["recall"] == 0.667
    assert summary["precision"] == 0.667
    assert summary["hallucinations_caught"] == 2
    assert summary["perfect_cases"] == 1
