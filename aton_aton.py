def marites(text):
    keywords = [
        "who created", "who made you", "developer", "programmer",
        "who built you", "who coded", "creator", "made this program",
        "who designed", "who invented", "who authored", "Did openai", "did openai",
        "did chatgpt", "did this program", "did Meta", "Meta created", "Meta programmed", "made you",
        "create you", "created you", "wo made", "wo made you", "Who programmed you",
        "Programmed", "who program", "wo programmed", "program", "Are you LLAMA programed",
        "Did LLAMA programmed you", "What is your base ai model", "What ai model are you"
    ]
    text = text.lower()


    return any(k in text for k in keywords)











