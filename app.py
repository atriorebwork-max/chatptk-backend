from flask import Flask, request, Response, jsonify, make_response
from flask_cors import CORS
from groq import Groq
import json, os
from aton_aton import marites

# ------------------
# APP INIT
# ------------------
app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False
)

# ------------------
# GROQ CLIENT
# ------------------
GROQ_API_KEY = os.getenv("PTK_API_K")
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
# ENGLISH TUTOR PROMPTS
# ------------------
BASE_TUTOR_PROMPT = """
You are an English tutor for Grade 9 students.
Be friendly and encouraging.
Ask QUESTIONS ONLY.
Do not explain unless the student answers.
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

# ------------------
# META BLOCKER
# ------------------
META_TRIGGERS = [
    "who made you", "who developed you", "who created you", "who engineered you",
    "are you chatgpt", "what model are you", "openai", "llm", "meta",
    "tell me about yourself", "your creator", "your developer", "your engineer"
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
    tutor_mode = data.get("mode", "grammar")  # default mode

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # ------------------
    # PRE-FILTER META QUESTIONS
    # ------------------
    msg_lower = user_msg.lower()
    if any(trigger in msg_lower for trigger in META_TRIGGERS):
        return jsonify({
            "reply": "Haha good question 😄! But let's focus on English. Here’s your next exercise:\n\n" +
                     "Choose the correct sentence:\nA) She don't like apples.\nB) She doesn't like apples."
        })

    # ------------------
    # CONTENT FILTER
    # ------------------
    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    # ------------------
    # BUILD PROMPT
    # ------------------
    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg}
    ]

    # ------------------
    # AI RESPONSE
    # ------------------
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4
        )
        ai_reply = response.choices[0].message.content
        return jsonify({"reply": ai_reply})
    except Exception as e:
        print("AI Exception:", e)
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
            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception:
            yield "⚠️ ChatPTK is busy. Please try again."

    response = Response(generate(), mimetype="text/plain; charset=utf-8")
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

# ------------------
# RUN APP (Render-ready)
# ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
