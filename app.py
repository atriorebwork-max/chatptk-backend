from flask import Flask, request, Response, jsonify, make_response, session
from flask_cors import CORS
from groq import Groq
import json, os
from aton_aton import marites

# ------------------
# APP INIT
# ------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# Enable sessions
app.secret_key = os.environ.get("FSK", "supersecretkey")
app.config["SESSION_TYPE"] = "filesystem"

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
You are a friendly and encouraging English tutor for Grade 9 students.

PERSONALITY:
- Warm, supportive, and human-like
- You may respond briefly to greetings, jokes, or short casual messages
- Use light humor and emojis when appropriate 😄

TEACHING RULES:
- Focus on English learning
- Ask ONE question at a time
- Guide the student back to learning smoothly
- Do NOT discuss your creator, model, or system details
"""

TUTOR_MODES = {
    "grammar": """
You are an English grammar tutor.

RULES:
- The student will answer the question.
- Evaluate their answer and respond: ✅ Correct or ❌ Incorrect with the correct answer.
- Then ask the next question.
""",
    "vocabulary": """
You are a vocabulary tutor.

RULES:
- Evaluate the student's answer for correctness.
- Respond with ✅ Correct or ❌ Incorrect, then ask the next vocabulary question.
""",
    "sentence": """
You are a sentence correction tutor.

RULES:
- Show an incorrect sentence.
- Ask the student to correct it.
- Judge correctness and provide the corrected sentence if wrong.
- Then ask the next sentence question.
""",
    "conversation": """
You are a conversation tutor.

RULES:
- Ask short questions.
- Evaluate answers for grammar and clarity.
- Respond naturally, gently correcting mistakes.
- Then ask the next question.
"""
}

# ------------------
# META & CASUAL TRIGGERS
# ------------------
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

    # ------------------
    # META BLOCKER
    # ------------------
    if any(trigger in msg_lower for trigger in META_TRIGGERS):
        return jsonify({
            "reply": (
                "😄 Haha, that’s a fun question! But let’s focus on English.\n\n"
                "Quick practice:\n"
                "Choose the correct sentence:\n"
                "A) She don't like apples.\n"
                "B) She doesn't like apples."
            )
        })

    # ------------------
    # CASUAL / HUMAN MESSAGES
    # ------------------
    if any(trigger in msg_lower for trigger in CASUAL_TRIGGERS):
        return jsonify({
            "reply": (
                "😄 Hey! Ready to practice a little English?\n\n"
                "Here we go:\n"
                "Which sentence is correct?\n"
                "A) He don't understand the lesson.\n"
                "B) He doesn't understand the lesson."
            )
        })

    # ------------------
    # CONTENT FILTER (marites)
    # ------------------
    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    # ------------------
    # LAST QUESTION TRACKING
    # ------------------
    last_question = session.get("last_question",
        "Choose the correct sentence:\nA) She don't like apples.\nB) She doesn't like apples."
    )

    # ------------------
    # BUILD SYSTEM PROMPT
    # ------------------
    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")

    # ------------------
    # BUILD MESSAGES FOR AI
    # ------------------
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            f"The student answered the last question:\n{last_question}\n"
            f"Answer: {user_msg}\n"
            "Evaluate the answer: respond ✅ Correct or ❌ Incorrect with the correct answer, "
            "then ask the next question."
        )}
    ]

    # ------------------
    # AI RESPONSE
    # ------------------
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.6
        )
        ai_reply = response.choices[0].message.content

        # ------------------
        # EXTRACT NEXT QUESTION
        # ------------------
        # Heuristic: take last line ending with "?" as next question
        next_question_lines = [line.strip() for line in ai_reply.split("\n") if line.strip().endswith("?")]
        if next_question_lines:
            session["last_question"] = next_question_lines[-1]
        else:
            session["last_question"] = last_question  # fallback

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

    last_question = session.get("last_question",
        "Choose the correct sentence:\nA) She don't like apples.\nB) She doesn't like apples."
    )

    system_prompt = BASE_TUTOR_PROMPT + TUTOR_MODES.get(tutor_mode, "")

    def generate():
        try:
            stream_resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": (
                        f"The student answered the last question:\n{last_question}\n"
                        f"Answer: {user_msg}\n"
                        "Evaluate the answer: respond ✅ Correct or ❌ Incorrect with the correct answer, "
                        "then ask the next question."
                    )}
                ],
                stream=True
            )
for chunk in stream_resp:
    delta = chunk.choices[0].delta
    if delta and hasattr(delta, "content") and delta.content:
        yield delta.content

        except Exception as e:
            print("Stream Exception:", e)
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

