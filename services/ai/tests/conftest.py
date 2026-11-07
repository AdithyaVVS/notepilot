SAMPLE_NOTE = (
    "Weekly sync, 4 Nov\n"
    "- Priya will send the revised budget to finance by Friday.\n"
    "- Rahul needs to fix the login bug ASAP, before next week.\n"
    "We decided to postpone the launch.\n"
    "- Ananya should book the venue by 20 Nov."
)


class ScriptedLLM:
    """Returns pre-written replies in order and records what it was asked."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate(self, instructions, content):
        self.calls.append({"instructions": instructions, "content": content})
        if not self.replies:
            raise AssertionError("LLM was called more times than scripted")
        return self.replies.pop(0)
