from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from groq import Groq
import json, os
from aton_aton import marites

# ------------------
# APP SETUP
# ------------------
app = Flask(__name__)

CORS(
    app,
    resources={
        r"/stream": {
            "origins": [
                "https://ptkaizone.com",
                "https://www.ptkaizone.com",
                "https://z259914-y016nt.ls03.zwhhosting.com"
            ]
        }
    }
)

# ------------------
# DATABASE CONFIG
# ------------------
# Set this in your hosting ENV:
# DATABASE_URL=mysql+pymysql://dbuser:password@localhost/zyntlszw_PTK_DB

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------
# DATABASE MODEL
# ------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    F_Name = db.Column(db.String(255))
    L_Name = db.Column(db.String(250))
    s_ID = db.Column(db.String(255), unique=True)
    S_Balance = db.Column(db.Integer)

# ------------------
# GROQ CLIENT
# ------------------
GROQ_API_KEY = os.getenv("PTK_API_K")
if not GROQ_API_KEY:
    raise RuntimeError("PTK_API_K not set")

client = Groq(api_key=GROQ_API_KEY)

# ------------------
# LOAD KNOWLEDGE
# ------------------
try:
    with open("knowledge.json", "r", encoding="utf-8") as f:
        KNOWLEDGE = json.load(f)["lessons"]
except Exception:
    KNOWLEDGE = []

# ------------------
# ROUTES
# ------------------
@app.route("/")
def home():
    return "ChatPTK backend with DB is running 🚀"

# 🔹 DB TEST ROUTE (IMPORTANT)
@app.route("/test-db")
def test_db():
    user = User.query.first()
    if not user:
        return jsonify({"error": "No users found"})

    return jsonify({
        "first_name": user.F_Name,
        "last_name": user.L_Name,
        "student_id": user.s_ID,
        "balance": user.S_Balance
    })

# ------------------
# STREAM CHAT
# ------------------
@app.route("/stream", methods=["POST"])
def stream():
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    masked = marites(user_msg)
    if masked:
        return Response(masked, mimetype="text/plain; charset=utf-8")

    system_prompt = "You are ChatPTK, a friendly tutor."

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

    return Response(
        generate(),
        mimetype="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

# ------------------
# NORMAL CHAT
# ------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    masked = marites(user_msg)
    if masked:
        return jsonify({"reply": masked})

    system_prompt = "You are ChatPTK, a friendly tutor."

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

