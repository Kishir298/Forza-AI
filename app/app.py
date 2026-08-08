from brain.ollama_provider import OllamaBrain
from memory.extractor import MemoryExtractor
from memory.manager import MemoryManager
from tools.router import ToolRouter


class Forza:


    def __init__(self):

        self.brain = OllamaBrain()
        self.extractor = MemoryExtractor()
        self.memory = MemoryManager()
        self.tools = ToolRouter()



    def process(self, message):


        # Check tools first

        tool_response = self.tools.check_tools(message)


        if tool_response:

            return iter([tool_response])


        # Save possible memories

        self.extractor.analyze(message)


        # Normal AI conversation

        return self.brain.chat_stream(message)