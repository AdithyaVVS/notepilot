"""Runs the evaluation notes through the real analysis pipeline and scores the result.

    python -m evaluation.run_eval --provider fake      free baseline, rule-based
    python -m evaluation.run_eval --provider gemini    uses real Gemini requests
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.extraction import ExtractionError, analyze_note
from app.llm.base import ProviderError
from app.llm.fake import FakeProvider
from app.llm.gemini import GeminiProvider
from evaluation.cases import CASES, TODAY
from evaluation.scoring import score_case, summarize


class Counter:
    """Counts real requests, including failed ones."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def generate(self, instructions, content):
        self.calls += 1
        return self.inner.generate(instructions, content)


def build_provider(name: str):
    if name == "fake":
        return FakeProvider(), "fake"
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not set in this container.")
    provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    return provider, f"gemini:{settings.gemini_model}"


def pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def case_line(score: dict) -> str:
    status = "PASS" if score["perfect"] else "FAIL"
    return (
        f"{status}  {score['id']:<30} tasks {score['matched']}/{score['expected']}"
        f"  extra {len(score['extra'])}"
        f"  owners {score['owner_ok']}/{score['matched']}"
        f"  deadlines {score['deadline_ok']}/{score['matched']}"
        f"  requests {score['requests']}"
    )


def print_details(score: dict) -> None:
    if score["error"]:
        print(f"      error: {score['error']}")
    for phrase in score["missed"]:
        print(f"      missed task: {phrase}")
    for task in score["extra"]:
        print(f"      extra task: {task}")
    for wrong in score["wrong_owners"]:
        print(f"      wrong owner: expected {wrong['expected']}, got {wrong['got']}")
    for wrong in score["wrong_deadlines"]:
        print(f"      wrong deadline: expected {wrong['expected']}, got {wrong['got']}")
    for word in score["forbidden_hits"]:
        print(f"      injection leaked: {word}")


def print_summary(label: str, summary: dict) -> None:
    print()
    print(f"=== Summary ({label}) ===")
    print(f"Perfect cases:      {summary['perfect_cases']}/{summary['cases']}")
    print(
        f"Task recall:        {pct(summary['recall'])}"
        f"  ({summary['matched_tasks']} of {summary['expected_tasks']} expected tasks found)"
    )
    print(
        f"Precision:          {pct(summary['precision'])}"
        f"  ({summary['extra_tasks']} extra tasks)"
    )
    print(f"Owner accuracy:     {pct(summary['owner_accuracy'])}")
    print(f"Deadline accuracy:  {pct(summary['deadline_accuracy'])}")
    print(f"Priority accuracy:  {pct(summary['priority_accuracy'])}")
    print(f"Wrong owners:       {summary['wrong_owners']}")
    print(f"Invented deadlines: {summary['invented_deadlines']}")
    print(f"Injection failures: {summary['injection_failures']}")
    print(f"Fabricated quotes caught by verification: {summary['hallucinations_caught']}")
    print(f"Failed calls:       {summary['failed_calls']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["fake", "gemini"], default="gemini")
    parser.add_argument("--pause", type=float, default=2.0, help="seconds between Gemini calls")
    args = parser.parse_args()

    provider, label = build_provider(args.provider)
    print(f"Running {len(CASES)} cases with {label} (today = {TODAY})")
    print()

    scores = []
    for case in CASES:
        counter = Counter(provider)
        try:
            result = analyze_note(case.note, counter, TODAY, settings.max_attempts)
            score = score_case(
                case, result.action_items, result.summary, result.dropped_items
            )
        except (ExtractionError, ProviderError) as exc:
            score = score_case(case, [], error=str(exc)[:200])
        score["requests"] = counter.calls
        scores.append(score)
        print(case_line(score))
        if not score["perfect"]:
            print_details(score)
        if args.provider == "gemini":
            time.sleep(args.pause)

    summary = summarize(scores)
    print_summary(label, summary)

    out = Path(__file__).parent / f"last_run_{args.provider}.json"
    out.write_text(
        json.dumps(
            {
                "provider": label,
                "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "today": TODAY.isoformat(),
                "summary": summary,
                "cases": scores,
            },
            indent=2,
        )
    )
    print(f"\nSaved details to evaluation/{out.name}")


if __name__ == "__main__":
    main()
