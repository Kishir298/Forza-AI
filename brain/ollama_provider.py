import ollama
from brain.prompts import FORZA_SYSTEM_PROMPT


class OllamaBrain:

    def __init__(self, model="qwen2.5:3b"):

        self.model = model

        self.messages = [
            {
                "role": "system",
                "content": FORZA_SYSTEM_PROMPT
            }
        ]


    def chat_stream(self, message):

        self.messages.append(
            {
                "role": "user",
                "content": message
            }
        )


        # Keep conversation small for speed
        if len(self.messages) > 9:

            self.messages = (
                [self.messages[0]]
                + self.messages[-8:]
            )


        response = ollama.chat(
            model=self.model,
            messages=self.messages,
            stream=True,
            options={
                "temperature": 0.7,
                "num_predict": 300
            }
        )


        full_response = ""


        for chunk in response:

            content = chunk["message"]["content"]

            if content:

                full_response += content
                yield content


        self.messages.append(
            {
                "role": "assistant",
                "content": full_response
            }
        )
