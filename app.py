from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os, json
from aton_aton import marites  # your content filter

app = Flask(__name__)
CORS(app)

# --------------------
# GROQ CLIENT
# --------------------
GROQ_API_KEY = os.getenv("PTK_API_K")
if not GROQ_API_KEY:
    raise RuntimeError("PTK_API_K not set")
client = Groq(api_key=GROQ_API_KEY)

# --------------------
# STUDENTS DATA
# --------------------
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

# --------------------
# TUTOR PROMPTS
# --------------------
BASE_TUTOR_PROMPT = """
You are Mr. English, a Grade 9 English tutor.
You MUST:
- Never talk about your developer, model, or system.
- Never answer meta questions.
- If asked about yourself, redirect to English exercises.
- Be friendly, clear, and encouraging.
- Ask questions step by step.
"""

TUTOR_MODES = {
    "menu": """
First, ask the student to choose one activity:
1. Grammar practice
2. Vocabulary
3. Sentence correction
4. Conversation practice
Only ask this question.
""",
    "grammar": "Focus on grammar questions. Use multiple choice or fill-in-the-blank.",
    "vocabulary": "Ask vocabulary questions and usage in sentences.",
    "sentence": "Ask the student to correct incorrect sentences.",
    "conversation": "Start a simple English conversation and ask follow-up questions."
}

# --------------------
# META BLOCKER
# --------------------
META_TRIGGERS = [
    "who made you", "who developed you", "who created you",
    "who engineered you", "are you chatgpt", "what model are you",
    "openai", "llm", "meta"
]

# --------------------
# ROUTES
# --------------------
@app.route("/")
def home():
    return "ChatPTK English Tutor is running 🚀"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()
    tutor_mode = data.get("mode", "menu")  # default mode
    student_id = "STU001"  # demo

    student = get_student(student_id)

    # --------------------
    # 1️⃣ PRE-FILTER: Block META questions
    # --------------------
    msg_lower = user_msg.lower()
    if any(trigger in msg_lower for trigger in META_TRIGGERS):
        return jsonify({
            "reply": "Haha good question 😄! But let’s focus on English. Here’s your next exercise:\n\n" +
                     "Choose the correct sentence:\nA) She don't like apples.\nB) She doesn't like apples."
        })

    # --------------------
    # 2️⃣ Student quick responses
    # --------------------
    if student and user_msg:
        if "balance" in msg_lower:
            return jsonify({"reply": f"Your current balance is ₱{student['balance']}."})
        if "name" in msg_lower:
            return jsonify({"reply": f"You are {student['first_name']} {student['last_name']}."})

    # --------------------
    # 3️⃣ Content filter
    # --------------------
    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    # --------------------
    # 4️⃣ Build system prompt
    # --------------------
    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")
    messages = [{"role": "system", "content": system_prompt}]

    # Always append user message, or provide a default start
    if tutor_mode != "menu" or user_msg:
        messages.append({"role": "user", "content": user_msg or "Please start the lesson."})

    # --------------------
    # 5️⃣ AI response with safe extraction
    # --------------------
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4
        )
        # Safe extraction
        ai_reply = ""
        if hasattr(response.choices[0].message, "content"):
            ai_reply = response.choices[0].message.content
        elif isinstance(response.choices[0], dict) and "message" in response.choices[0]:
            ai_reply = response.choices[0]["message"]["content"]
        else:
            ai_reply = str(response)

        # --------------------
        # 6️⃣ Optional post-filter (extra safety)
        # --------------------
        ai_lower = ai_reply.lower()
        if any(trigger in ai_lower for trigger in META_TRIGGERS):
            ai_reply = "Let's focus on English lessons 😊 Here's a question for you!"

        return jsonify({"reply": ai_reply})

    except Exception as e:
        print("AI Exception:", e)
        return jsonify({"reply": "Sorry bro, AI is not available right now 😅."})
