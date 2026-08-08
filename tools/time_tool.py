from datetime import datetime


def get_time():

    now = datetime.now()

    formatted_time = now.strftime("%I:%M %p")

    formatted_date = now.strftime("%A, %d %B %Y")


    return f"It is {formatted_time}. Today is {formatted_date}."
