import ollama
import json


class AIMemoryExtractor:

    def __init__(self, model="qwen2.5:3b"):
        self.model = model


    def extract(self, message):

        prompt = f"""
You are a memory extraction system.

Analyze this user message:

"{message}"

Decide if it contains information useful to remember
for future conversations.

Remember things like:
- Name
- Preferences
- Projects
- Skills
- Goals
- Important facts

Do NOT remember:
- Temporary questions
- Random jokes
- Passwords
- Private sensitive information

Return ONLY valid JSON.

Format:

{{
"save": true/false,
"category": "category name",
"memory": "short memory description",
"importance": 1-10
}}

If nothing is useful:

{{
"save": false
}}
"""


        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )


        text = response["message"]["content"]


        try:
            return json.loads(text)

        except:
            return {
                "save": False
            }
