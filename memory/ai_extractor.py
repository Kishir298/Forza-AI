import json

import ollama


class AIMemoryExtractor:
    """Use a local AI model to identify useful long-term memories."""

    def __init__(self, model="qwen2.5:3b"):
        self.model = model

    def extract(self, message):
        """
        Analyze a message and return a structured memory decision.

        The AI extractor does not save anything itself.
        It only determines what, if anything, should be remembered.
        """

        if not isinstance(message, str):
            return {
                "save": False
            }

        message = message.strip()

        if not message:
            return {
                "save": False
            }

        prompt = f"""
You are Forza's memory extraction system.

Analyze this user message:

"{message}"

Decide whether it contains information useful to remember
for future conversations.

Useful long-term information includes:
- Name
- Preferences
- Projects
- Skills
- Goals
- Long-term plans
- Important non-sensitive facts

Do NOT remember:
- Temporary questions
- Random jokes
- Casual conversation
- Passwords
- Authentication credentials
- Highly sensitive personal information
- One-time temporary information

If the message contains useful information, create a SHORT
memory that preserves the important meaning without unnecessary
detail.

Return ONLY valid JSON.

If useful:

{{
    "save": true,
    "category": "personal|preference|project|skill|goal|general",
    "memory": "short memory description",
    "importance": 1
}}

Importance must be an integer from 1 to 10.

If nothing is useful:

{{
    "save": false
}}
"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            text = response["message"]["content"].strip()

        except Exception:
            return {
                "save": False,
                "error": "AI memory extraction unavailable",
            }

        try:
            result = json.loads(text)

        except (json.JSONDecodeError, TypeError):
            return {
                "save": False,
                "error": "Invalid AI response",
            }

        return self._validate_result(result)

    @staticmethod
    def _validate_result(result):
        """Validate and normalize the AI's response."""

        if not isinstance(result, dict):
            return {
                "save": False,
                "error": "Invalid result format",
            }

        if result.get("save") is not True:
            return {
                "save": False
            }

        memory = result.get("memory")

        if not isinstance(memory, str) or not memory.strip():
            return {
                "save": False,
                "error": "Missing memory",
            }

        category = result.get(
            "category",
            "general",
        )

        allowed_categories = {
            "personal",
            "preference",
            "project",
            "skill",
            "goal",
            "general",
        }

        if category not in allowed_categories:
            category = "general"

        try:
            importance = int(
                result.get("importance", 5)
            )
        except (TypeError, ValueError):
            importance = 5

        importance = max(
            1,
            min(10, importance),
        )

        return {
            "save": True,
            "category": category,
            "memory": memory.strip(),
            "importance": importance,
        }