TOOLS = []


def register_tool(
    name,
    description,
    keywords,
    function
):

    TOOLS.append(
        {
            "name": name,
            "description": description,
            "keywords": keywords,
            "function": function
        }
    )


def find_tool(message):

    text = message.lower()

    for tool in TOOLS:

        if any(keyword in text for keyword in tool["keywords"]):
            return tool

    return None
