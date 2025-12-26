from flask import Flask, request, jsonify, Response
from groq import Groq
import os, json

app = Flask(__name__)

# ---------- GROQ CLIENT ----------
client = Groq(api_key=os.environ.get("PTK_API_K"))

# ---------- LOAD KNOWLEDGE ----------
knowledge = []
try:
    with open("knowledge.json", "r", encoding="utf-8") as f:
        knowledge = json.load(f).get("lessons", [])
except FileNotFoundError:
    print("knowledge.json not found")

# ---------- MASKING ----------
def marites(text):
    keywords = [
        "who created", "who made you", "developer",
        "programmer", "creator", "who coded"
    ]
    text = text.lower()
    if any(k in text for k in keywords):
        return (
            "I was created by a group of PTK students 🌸 "
            "This project was built for the Open House."
        )
    return None

# ---------- ROUTES ----------
@app.route("/", methods=["GET"])
def home():
    return "ChatPTK backend is running 🚀"

@app.route("/test", methods=["GET"])
def test():
    return jsonify(status="OK", message="Backend is alive 🚀")

@app.route("/stream", methods=["POST"])
def stream():
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "")

    masked = marites(user_msg)
    if masked:
        return Response(masked, mimetype="text/plain")

    def generate():
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": user_msg}],
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return Response(generate(), mimetype="text/plain")
