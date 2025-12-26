from flask import Flask, request, Response
from groq import Groq
import os
import json

app = Flask(__name__)

# ---------- GROQ CLIENT ----------
client = Groq(api_key=os.environ.get("PTK_API_K"))

# ---------- LOAD KNOWLEDGE ----------
with open("knowledge.json", "r", encoding="utf-8") as f:
    knowledge = json.load(f)["lessons"]

# ---------- MASKING ----------
def marites(text):
    keywords = [
        "who created", "who made you", "developer", "programmer",
        "who built you", "creator", "who coded"
    ]
    text = text.lower()

    if any(k in text for k in keywords):
        return (
            "I was created by a group of PTK students 🌸 "
            "This project was built for the Open House."
        )
    return None

# ---------- KNOWLEDGE MATCH ----------
def get_relevant_knowledge(user_msg):
    user_msg = user_msg.lower()
    matches = []

    for item in knowledge:
        topic = item["topic"].lower()
        if topic in user_msg:
            matches.append(item["content"])

    return "\n".join(matches)

# ---------- ROUTES ----------
@app.route("/stream", methods=["POST"])
def stream():
    user_msg = request.json.get("message", "")

    # Masking first
    masked = marites(user_msg)
    if masked:
        return Response(masked.encode("utf-8"), mimetype="text/plain")

    context = get_relevant_knowledge(user_msg)

    system_prompt = (
        "You are ChatPTK, a friendly AI tutor.\n"
        "Use the knowledge if relevant.\n"
        "Do not say you are an AI model."
    )

    def generate():
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\n{user_msg}"}
            ],
            stream=True
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content.encode("utf-8")

    return Response(generate(), mimetype="text/plain")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

