from memory.manager import MemoryManager


class MemoryExtractor:

    def __init__(self):
        self.memory = MemoryManager()


    def analyze(self, message):

        text = message.lower()

        memory_triggers = [
            "my name is",
            "i like",
            "i love",
            "i prefer",
            "i use",
            "i am building",
            "my project",
            "remember"
        ]


        important = False


        for trigger in memory_triggers:
            if trigger in text:
                important = True
                break


        if not important:
            return


        category = "general"


        if "name" in text:
            category = "personal"

        elif "project" in text or "building" in text:
            category = "project"

        elif "like" in text or "prefer" in text:
            category = "preference"


        self.memory.save_memory(
            category,
            message,
            5
        )
