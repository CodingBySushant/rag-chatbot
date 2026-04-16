"""
pipeline/memory.py
Sliding window conversation memory.

Stores the last N turns (user + assistant pairs).
Older turns are dropped to keep context window manageable.

Why sliding window over full history:
  - Full history grows unbounded and eventually exceeds LLM context limit
  - Most questions depend only on the last 2-3 turns
  - MEMORY_TURNS=6 means 3 user + 3 assistant messages
"""
from collections import deque
import config as cfg


class ConversationMemory:
    def __init__(self, max_turns: int = None):
        self.max_turns = max_turns or cfg.MEMORY_TURNS
        # Each entry: {"role": "user"|"assistant", "content": str}
        self._history: deque = deque(maxlen=self.max_turns * 2)

    def add(self, role: str, content: str):
        """Add a turn to memory."""
        self._history.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        """Return all stored turns as a list."""
        return list(self._history)

    def format_for_prompt(self) -> str:
        """
        Format history as a readable block for the system prompt.
        Returns empty string if no history yet.
        """
        if not self._history:
            return ""

        lines = ["Conversation so far:"]
        for turn in self._history:
            prefix = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {turn['content']}")
        return "\n".join(lines)

    def clear(self):
        """Reset memory."""
        self._history.clear()

    def is_empty(self) -> bool:
        return len(self._history) == 0

    def turn_count(self) -> int:
        return len(self._history) // 2
