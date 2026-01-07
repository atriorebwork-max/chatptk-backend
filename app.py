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

TUTOR_MODES = {
    "menu": """
Ask the student to choose one:
1. Grammar practice
2. Vocabulary
3. Sentence correction
4. Conversation practice
Only ask this question.
""",
    "grammar": "Ask grammar questions only.",
    "vocabulary": "Ask vocabulary questions only.",
    "sentence": "Ask sentence correction questions only.",
    "conversation": "Ask short conversational questions only."
}

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
        return Response(masked, mimetype="text/plain")

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
