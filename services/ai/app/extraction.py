import json
import re
from datetime import date

from app.deadlines import resolve_deadline
from app.llm.base import LLMProvider
from app.prompts import SYSTEM_INSTRUCTIONS, retry_note, wrap_note
from app.schemas import ActionItem, AnalysisResult, RawAnalysis


class ExtractionError(Exception):
    """The model never produced a valid reply."""


def parse_json(raw: str):
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def locate(note: str, quote: str):
    """Find the quote in the note, ignoring case and whitespace differences.
    Returns (start, end) in the original note, or None if it isn't there."""
    words = quote.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.search(pattern, note, re.IGNORECASE)
    return (match.start(), match.end()) if match else None


def build_result(analysis: RawAnalysis, note: str, today: date, attempts: int):
    items = []
    dropped = 0
    for raw in analysis.action_items:
        span = locate(note, raw.evidence)
        if span is None:
            dropped += 1  # the model cited something the note doesn't say
            continue

        owner = raw.owner.strip() if raw.owner else None
        if owner and locate(note, owner) is None:
            owner = None  # never keep a guessed owner

        deadline_text = raw.deadline_text.strip() if raw.deadline_text else None
        if deadline_text and locate(note, deadline_text) is None:
            deadline_text = None  # never keep an invented deadline
        deadline = resolve_deadline(deadline_text, today) if deadline_text else None

        items.append(
            ActionItem(
                task=raw.task,
                owner=owner,
                deadline_text=deadline_text,
                deadline=deadline,
                priority=raw.priority,
                evidence=note[span[0] : span[1]],
                evidence_start=span[0],
                evidence_end=span[1],
            )
        )
    return AnalysisResult(
        summary=analysis.summary,
        action_items=items,
        dropped_items=dropped,
        attempts=attempts,
    )


def analyze_note(
    note: str, provider: LLMProvider, today: date, max_attempts: int = 2
) -> AnalysisResult:
    content = wrap_note(note)
    error = None
    for attempt in range(1, max_attempts + 1):
        instructions = SYSTEM_INSTRUCTIONS
        if error:
            instructions += retry_note(error)
        raw = provider.generate(instructions, content)
        try:
            analysis = RawAnalysis.model_validate(parse_json(raw))
        except ValueError as exc:  # bad JSON and failed validation both land here
            error = str(exc).replace("\n", " ")[:300]
            continue
        return build_result(analysis, note, today, attempt)
    raise ExtractionError(f"No valid reply after {max_attempts} attempts: {error}")
