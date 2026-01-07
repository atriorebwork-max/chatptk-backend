from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from groq import Groq
import json, os
from aton_aton import marites

app = Flask(__name__)
CORS(app)

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
        STUDENTS = json.load(f)["students"]
except Exception:
    STUDENTS = []

def get_student(student_id):
    for s in STUDENTS:
        if s["student_id"] == student_id:
            return s
    return None

# ------------------
# ENGLISH TUTOR PROMPTS
# ------------------
BASE_TUTOR_PROMPT = """
You are an English tutor for Grade 9 students.
Be friendly, clear, and encouraging.
Do NOT give long lectures.
Ask questions step by step.
"""

TUTOR_MODES = {
    "menu": """
First, ask the student to choose one activity:
1. Grammar practice
2. Vocabulary
3. Sentence correction
4. Conversation practice

Only ask this question. Do not explain yet.
""",
    "grammar": "Focus on grammar questions. Use multiple choice or fill-in-the-blank.",
    "vocabulary": "Ask vocabulary questions and usage in sentences.",
    "sentence": "Ask the student to correct incorrect sentences.",
    "conversation": "Start a simple English conversation and ask follow-up questions."
}

# ------------------
# ROUTES
# ------------------
@app.route("/")
def home():
    return "ChatPTK English Tutor is running 🚀"

# ------------------
# CHAT (MAIN)
# ------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    user_msg = data.get("message", "").strip()
    tutor_mode = data.get("mode", "menu")  # default = question-first
    student_id = "STU001"  # demo mode

    if not user_msg and tutor_mode != "menu":
        return jsonify({"error": "Empty message"}), 400

    student = get_student(student_id)

    # 🔐 Student-based responses (example)
    if student and user_msg:
        msg_lower = user_msg.lower()
        if "balance" in msg_lower:
            return jsonify({"reply": f"Your current balance is ₱{student['balance']}."})
        if "name" in msg_lower:
            return jsonify({"reply": f"You are {student['first_name']} {student['last_name']}."})

    # 🛡️ Content filter
    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    # 🧠 BUILD SYSTEM PROMPT
    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")

    messages = [{"role": "system", "content": system_prompt}]

    if tutor_mode != "menu":
        messages.append({"role": "user", "content": user_msg})

    # 🤖 AI RESPONSE
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.4
    )

    return jsonify({
        "reply": response.choices[0].message.content
    })
