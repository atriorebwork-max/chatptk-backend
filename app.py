from flask import Flask, request, Response, jsonify, make_response
from flask_cors import CORS
from groq import Groq
import json, os
from aton_aton import marites

# ------------------
# APP INIT
# ------------------
app = Flask(__name__)

# ✅ Allow CORS for ALL routes (Render-safe)
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
# LOAD STUDENTS (JSON MODE)
# ------------------
try:
    with open("students.json", "r", encoding="utf-8") as f:
        STUDENTS = json.load(f)["students"]
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
""",


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

Do NOT explain unless checking the answer.
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
# HOME
# ------------------
@app.route("/")
def home():
    return "ChatPTK English Tutor backend is running 🚀"

# ------------------#
# CHAT (NON-STREAM)
# ------------------#
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    user_msg = data.get("message", "").strip()
    system_prompt = data.get("system") or "You are ChatPTK, a friendly tutor."

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.4
    )

    return jsonify({
        "reply": response.choices[0].message.content
    })

# ------------------
# STREAM CHAT (CORS FIXED)
# ------------------
@app.route("/stream", methods=["POST", "OPTIONS"])
def stream():
    # ✅ HANDLE PREFLIGHT FIRST
    if request.method == "OPTIONS":
        response = make_response("", 200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

    # -------------------------
    # REAL POST REQUEST
    # -------------------------
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()
    system_prompt = data.get("system") or "You are ChatPTK, a friendly tutor."
    
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    masked = marites(user_msg)
    if masked:
        return Response(masked, mimetype="Text/Plain")

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

    response = Response(
        generate(),
        mimetype="text/plain; charset=utf-8"
    )

    # ✅ ATTACH CORS HEADERS TO STREAM RESPONSE
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"

    return response


# =================================================
# AI HANDLER
# =================================================

def ask_ai(user_msg):
    cleaned = user_msg.strip().lower()

    # 🔐 Easter egg
    if marites(user_msg):
        return "My Master, Mr. Atrio, he's the guy. He is the one created me. 😊"

    # ✅ Exact knowledge
    if cleaned in knowledge:
        return knowledge[cleaned]

    # 🔍 Fuzzy match
    fk = fuzzy_find(cleaned, knowledge)
    if fk:
        return knowledge[fk]

    try:
        response = client.chat.completions.create(
            model= MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are PTK SmartChat, a helpful school assistant. "
                        "Answer clearly and simply."
                    )
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ],
            temperature=0.4
        )

        ai_msg = response.choices[0].message.content

        # 💾 Save learned knowledge
        save_knowledge(user_msg, ai_msg)
        knowledge[cleaned] = ai_msg

        return ai_msg

    except Exception as e:
        print("AI ERROR:", e)
        return "I was programmed by the Students of Mr. Atrio, He guided them to develop me."


# =================================================
# ROUTES
# =================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_msg = data.get("message", "")
    reply = ask_ai(user_msg)
    return jsonify({"reply": reply})

