import json
import re

NOTE_RE = re.compile(r"<note>\n?(.*?)\n?</note>", re.DOTALL)
ACTION_RE = re.compile(
    r"\b(will|needs? to|must|should|has to|todo|action)\b", re.IGNORECASE
)
OWNER_RE = re.compile(r"^([A-Z][a-z]+)\s+(?:will|needs? to|must|should|has to|to)\b")
URGENT_RE = re.compile(r"\b(urgent|asap|immediately|critical)\b", re.IGNORECASE)
DEADLINE_RE = re.compile(
    r"\b((?:by|before|until)\s+(?:"
    r"(?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|today|tomorrow|next week|end of (?:the )?(?:week|month)"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+|[a-z]+\s+\d{1,2}(?:st|nd|rd|th)?"
    r"))",
    re.IGNORECASE,
)
NOT_NAMES = {
    "We", "I", "They", "He", "She", "It", "You", "This", "That", "There",
    "Someone", "Everyone", "Team", "The", "Please", "Also", "Then",
}


class FakeProvider:
    """Offline stand-in for a real LLM that finds action-like lines with simple rules.
    Used for tests, local development and the free sample mode."""

    def generate(self, instructions: str, content: str) -> str:
        match = NOTE_RE.search(content)
        note = match.group(1) if match else content
        items = []
        for line in note.splitlines():
            text = line.strip().lstrip("-*\u2022 ").strip()
            if len(text) < 5 or not ACTION_RE.search(text):
                continue
            owner_match = OWNER_RE.match(text)
            owner = None
            if owner_match and owner_match.group(1) not in NOT_NAMES:
                owner = owner_match.group(1)
            deadline = DEADLINE_RE.search(text)
            items.append(
                {
                    "task": text[:300],
                    "owner": owner,
                    "deadline_text": deadline.group(1) if deadline else None,
                    "priority": "high" if URGENT_RE.search(text) else "medium",
                    "evidence": text[:500],
                }
            )
        first_line = next((x.strip() for x in note.splitlines() if x.strip()), "")
        return json.dumps(
            {
                "summary": f"Sample analysis of: {first_line[:150]}",
                "action_items": items[:30],
            }
        )
