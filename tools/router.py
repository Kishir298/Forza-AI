from tools.registry import find_tool


class ToolRouter:


    def check_tools(self, message):

        tool = find_tool(message)


        if tool:

            return tool["function"]()


        return None
