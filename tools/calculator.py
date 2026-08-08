import re


def calculate(expression):

    try:

        # Find only the math part
        match = re.search(
            r'[0-9+\-*/().\s]+',
            expression
        )


        if not match:

            return "I couldn't find a calculation."


        clean_expression = match.group().strip()


        result = eval(clean_expression)


        return f"The answer is {result}."


    except Exception:

        return "I couldn't calculate that."
