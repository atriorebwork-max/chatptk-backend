from flask import Flask, request, Response, jsonify, make_response, session
from flask_cors import CORS
from groq import Groq
import json, os, traceback
from aton_aton import marites  # your content filter

# ------------------
# APP INIT
# ------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Secret key for Flask sessions
app.secret_key = os.environ.get("FSK")
app.config["SESSION_TYPE"] = "filesystem"

# ------------------
# GROQ CLIENT
# ------------------
GROQ_API_KEY = os.environ.get("PTK_API_K")
if not GROQ_API_KEY:
    raise RuntimeError("PTK_API_K not set")
client = Groq(api_key=GROQ_API_KEY)

# ------------------
# LOAD STUDENTS
# ------------------
try:
    with open("students.json", "r", encoding="utf-8") as f:
        STUDENTS = json.load(f).get("students", [])
except Exception:
    STUDENTS = []

def get_student(student_id):
    for s in STUDENTS:
        if s.get("student_id") == student_id:
            return s
    return None

# ------------------
# PROMPTS & MODES
# ------------------
BASE_TUTOR_PROMPT = """
You are a friendly and encouraging English tutor for Grade 9 students.

PERSONALITY:
- Warm, supportive, human-like
- Respond to casual messages with light humor 😄

RULES:
- Focus on English learning
- Ask ONE question at a time
- Do NOT discuss your creator or model details
"""

TUTOR_MODES = {
    "grammar": """
You are an English grammar tutor.
RULES:
- Ask ONE question at a time.
- Always know the correct answer.
- Wait for the student's reply.
- If correct: say ✅ Correct and briefly praise.
- If wrong: say ❌ Incorrect and give the correct answer.
- Then ask the NEXT question.
""",
    "vocabulary": """
You are a vocabulary tutor.
RULES:
- Ask one vocabulary question.
- Evaluate the student's answer.
- Respond with Correct or Incorrect.
- Then ask the next question.
""",
    "sentence": """
You are a sentence correction tutor.
RULES:
- Show an incorrect sentence.
- Ask the student to correct it.
- Judge correctness.
- Give the corrected sentence if wrong.
""",
    "conversation": """
You are a conversation tutor.
RULES:
- Ask short questions.
- React naturally to answers.
- Gently correct grammar if wrong.
"""
}

META_TRIGGERS = [
    "who made you", "who developed you", "who created you", "who engineered you",
    "are you chatgpt", "what model are you", "openai", "llm", "meta",
    "tell me about yourself", "your creator", "your developer", "your engineer"
]

CASUAL_TRIGGERS = [
    "hi", "hello", "hey", "yo", "bro",
    "lol", "haha", "hehe", "😂", "😄"
]

# ------------------
# HOME
# ------------------
@app.route("/")
def home():
    return "ChatPTK English Tutor backend is running 🚀"

# ------------------
# CHAT (NON-STREAM)
# ------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()
    tutor_mode = data.get("mode", "grammar")

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    msg_lower = user_msg.lower()

    # META question blocker
    if any(trigger in msg_lower for trigger in META_TRIGGERS):
        return jsonify({"reply": (
            "😄 Haha, fun question! But let's focus on English.\n\n"
            "Quick practice:\n"
            "Choose the correct sentence:\n"
            "A) She don't like apples.\n"
            "B) She doesn't like apples."
        )})

    # Casual human messages
    if any(trigger in msg_lower for trigger in CASUAL_TRIGGERS):
        return jsonify({"reply": (
            "😄 Hey! Ready to practice a little English?\n\n"
            "Which sentence is correct?\n"
            "A) He don't understand the lesson.\n"
            "B) He doesn't understand the lesson."
        )})

    # Content filter
    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    # Build GPT prompt
    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg}
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.6
        )
        ai_reply = response.choices[0].message.content
        return jsonify({"reply": ai_reply})

    except Exception as e:
        print("AI Exception:", e)
        traceback.print_exc()
        return jsonify({"reply": "⚠️ ChatPTK is busy. Please try again."})

# ------------------
# STREAM CHAT
# ------------------
@app.route("/stream", methods=["POST", "OPTIONS"])
def stream():
    if request.method == "OPTIONS":
        response = make_response("", 200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()
    tutor_mode = data.get("mode", "grammar")

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    masked = marites(user_msg)
    if masked:
        return Response(masked, mimetype="text/plain")

    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")

    def generate():
        try:
            stream_resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                stream=True
            )

            for chunk in stream_resp:
                delta = chunk.choices[0].delta
                if delta and hasattr(delta, "content") and delta.content:
                    yield delta.content

        except Exception as e:
            print("Stream Exception:", e)
            traceback.print_exc()
            yield "⚠️ ChatPTK is busy. Please try again."

    response = Response(generate(), mimetype="text/plain; charset=utf-8")
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

# ------------------
# RUN APP
# ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
