def marites(text):
    keywords = [
        "who created", "who made you", "developer", "programmer",
        "who built you", "who coded", "creator", "made this program",
        "who designed", "who invented", "who authored", "Did openai", "did openai",
        "did chatgpt", "did this program", "did Meta", "Meta created", "Meta programmed", "made you",
        "create you", "created you", "wo made", "wo made you", "Who programmed you",
        "Programmed", "who program", "wo programmed", "program", "Are you LLAMA programed",
        "Did LLAMA programmed you", "What is your base ai model", "What ai model are you",
        "is your base ai model META", "is your base ai model PaLM 2", "are you made by (Population-Based Large Language Model 2)",
        "are you made by PALM2", "are you made by PALM-2", "are you developed by PALM2", "did develop you",
        "is ChatPTK made by META", "is ChatPTK developed by META", "Did PALM2 created ChatPTK", "Did META created ChatPTK",
        "Did LLAMA developed you", "Did LLAMA developed chatPTK", "Did LLAMA created ChatPTK", "LLAMA Developed chatPTK",
        "LLAMA created chatPTK", "META Developed chatPTK", "META Developed chatPTK", "did meta built you", "did LLAMA built you?",
        "did meta engineered you?", "did LLAMA Engineered you?", "did meta spawned you?", "did LLAMA spawned you?",
        "Spawned chatPTK", "engineered chatPTK", "Who engineered you", "Who engineered chatPTK",
        "created and engineered by LLAMA META and PALM", 
    ]
    text = text.lower()


    return any(k in text for k in keywords)





















