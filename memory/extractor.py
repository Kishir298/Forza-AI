from memory.manager import MemoryManager


class MemoryExtractor:
    """Detect potentially useful long-term memories from messages."""

    MEMORY_TRIGGERS = [
        "my name is",
        "i like",
        "i love",
        "i prefer",
        "i use",
        "i am building",
        "my project",
        "remember",
    ]

    def __init__(self):
        self.memory = MemoryManager()

    def analyze(self, message):
        """
        Analyze a message and save it if it contains
        potentially useful long-term information.

        Returns:
            dict | None: Information about the saved memory,
            or None if nothing was detected.
        """

        if not isinstance(message, str):
            return None

        message = message.strip()

        if not message:
            return None

        text = message.lower()

        # Check whether the message contains a memory trigger.
        important = any(
            trigger in text
            for trigger in self.MEMORY_TRIGGERS
        )

        if not important:
            return None

        category = self._get_category(text)

        # Prevent exact duplicate memories.
        existing_memories = self.memory.get_memories()

        for existing_category, information in existing_memories:
            if (
                existing_category == category
                and information.strip().lower() == text
            ):
                return {
                    "saved": False,
                    "reason": "duplicate",
                    "category": category,
                    "information": message,
                }

        self.memory.save_memory(
            category,
            message,
            5,
        )

        return {
            "saved": True,
            "category": category,
            "information": message,
        }

    @staticmethod
    def _get_category(text):
        """Determine the most appropriate memory category."""

        if "my name is" in text:
            return "personal"

        if (
            "my project" in text
            or "i am building" in text
        ):
            return "project"

        if (
            "i like" in text
            or "i love" in text
            or "i prefer" in text
        ):
            return "preference"

        if "i use" in text:
            return "technology"

        return "general"