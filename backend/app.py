"""
app.py — Lost in Random: Quantum Treasure Hunt
Full backend: quantum level gen, auth, leaderboard, multiplayer

INSTALL:
    pip install flask flask-cors flask-socketio pyjwt qiskit qiskit-aer

RUN:
    python app.py  →  open http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import jwt, uuid, random, math

from quantum_model import check_answer
from auth import register, login, users, SECRET
from leaderboard import update_score, get_leaderboard

app = Flask(__name__, static_folder=".")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ── sessions ──────────────────────────────────────────────────
sessions = {}   # session_id → game state
rooms     = {}  # room_id   → { players }

# ── level base config (quantum circuit will extend these) ─────
BASE_LEVELS = {
    1: {"theme":"horror",  "grid":3, "blocks":9,  "treasures":3},
    2: {"theme":"disney",  "grid":4, "blocks":16, "treasures":4},
    3: {"theme":"quantum", "grid":5, "blocks":25, "treasures":5},
    4: {"theme":"mythic",  "grid":5, "blocks":25, "treasures":4},
}

HINTS = {
    "horror":  "The haunted qubit collapses — |1⟩ measured where shadows are deepest.",
    "disney":  "Fairy-dust entanglement: Bell pairs shimmer near the grid's heart.",
    "quantum": "Apply Hadamard — constructive interference peaks at the hidden weights.",
    "mythic":  "The golden Hamiltonian eigenstate points toward the mythic gate.",
}

# ══════════════════════════════════════════════════════════════
# QUANTUM HELPERS
# ══════════════════════════════════════════════════════════════

def quantum_bool():
    """Single-shot Hadamard — true quantum random bit via Qiskit."""
    try:
        return check_answer("superposition")
    except Exception:
        return random.random() > 0.5


def quantum_int(n):
    """Quantum random integer 0..n-1 using repeated quantum coin flips."""
    bits_needed = math.ceil(math.log2(max(n, 2)))
    while True:
        val = 0
        for b in range(bits_needed):
            if quantum_bool():
                val |= (1 << b)
        if val < n:
            return val


def quantum_pick_treasures(total_blocks, treasure_count):
    """
    Use quantum circuit to pick unique treasure positions.
    Each position is selected by quantum_int — genuine quantum randomness.
    """
    positions = []
    attempts = 0
    while len(positions) < treasure_count and attempts < total_blocks * 10:
        attempts += 1
        idx = quantum_int(total_blocks)
        if idx not in positions:
            positions.append(idx)
    # fallback if quantum somehow stalls
    while len(positions) < treasure_count:
        r = random.randint(0, total_blocks - 1)
        if r not in positions:
            positions.append(r)
    return positions


def quantum_generate_level(level_id):
    """
    Use quantum RNG to auto-generate level parameters beyond base config.
    - Quantum bits decide bonus block count (±2)
    - Quantum bits decide bonus treasure (sometimes +1)
    - Returns fully generated level dict
    """
    base = BASE_LEVELS.get(level_id, BASE_LEVELS[1])
    theme = base["theme"]

    # Quantum-expand the grid slightly for replayability
    bonus_blocks = 0
    for _ in range(2):
        if quantum_bool():
            bonus_blocks += 1

    total_blocks = base["blocks"] + bonus_blocks
    grid_size = math.ceil(math.sqrt(total_blocks))
    total_blocks = grid_size * grid_size   # keep it square

    # Quantum-decide bonus treasure
    treasure_count = base["treasures"] + (1 if quantum_bool() and level_id >= 2 else 0)
    treasure_count = min(treasure_count, total_blocks // 3)

    # Quantum-pick treasure positions
    treasure_positions = quantum_pick_treasures(total_blocks, treasure_count)

    # Quantum-shuffle block label seeds (passed to frontend for visual variety)
    label_seed = quantum_int(1000)

    return {
        "level_id": level_id,
        "theme": theme,
        "grid_size": grid_size,
        "total_blocks": total_blocks,
        "treasure_count": treasure_count,
        "treasure_positions": treasure_positions,  # SECRET — never sent to frontend
        "label_seed": label_seed,
        "hint": HINTS[theme],
    }


# ══════════════════════════════════════════════════════════════
# SERVE FRONTEND
# ══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ══════════════════════════════════════════════════════════════
# AUTH  (auth.py)
# ══════════════════════════════════════════════════════════════
@app.route("/register", methods=["POST"])
def reg():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"msg": "Username and password required"}), 400
    if data["username"] in users:
        return jsonify({"msg": "Username already taken"}), 409
    users[data["username"]] = data["password"]
    return jsonify({"msg": "registered"})

@app.route("/login", methods=["POST"])
def log():
    return login()

def decode_token(req):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return jwt.decode(auth.split(" ")[1], SECRET, algorithms=["HS256"]).get("user")
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# LEADERBOARD  (leaderboard.py)
# ══════════════════════════════════════════════════════════════
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    return jsonify(get_leaderboard())

@app.route("/score", methods=["POST"])
def score():
    username = decode_token(request)
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    update_score(username, data.get("score", 0))
    return jsonify({"msg": "updated"})


# ══════════════════════════════════════════════════════════════
# GAME API
# ══════════════════════════════════════════════════════════════
@app.route("/api/level/start", methods=["POST"])
def start_level():
    data = request.get_json()
    level_id = int(data.get("level", 1))
    session_id = data.get("session_id") or str(uuid.uuid4())[:8]
    username = decode_token(request)

    # Quantum-generate this level instance
    lv = quantum_generate_level(level_id)

    sessions[session_id] = {
        "level": level_id,
        "username": username,
        "theme": lv["theme"],
        "treasure_positions": lv["treasure_positions"],
        "revealed": [],
        "found": 0,
        "hints_used": 0,
        "score": 0,
        "lives": 3,
        "wrong_count": 0,
    }

    # Return config (NO treasure_positions — keep secret)
    return jsonify({
        "session_id": session_id,
        "level": level_id,
        "theme": lv["theme"],
        "grid_size": lv["grid_size"],
        "total_blocks": lv["total_blocks"],
        "treasure_count": lv["treasure_count"],
        "label_seed": lv["label_seed"],
    })


@app.route("/api/check-block", methods=["POST"])
def check_block():
    data = request.get_json()
    session_id = data.get("session_id")
    block_index = int(data.get("block_index", 0))

    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    s = sessions[session_id]
    if block_index in s["revealed"]:
        return jsonify({"error": "Already revealed"}), 400

    s["revealed"].append(block_index)
    is_treasure = block_index in s["treasure_positions"]

    if is_treasure:
        s["found"] += 1
        s["score"] += 100 + max(0, (3 - s["hints_used"])) * 20
    else:
        # Deduct 1 life on EVERY wrong click
        s["lives"] = max(0, s["lives"] - 1)

    level_complete = s["found"] >= len(s["treasure_positions"])
    game_over = (not is_treasure) and (s["lives"] <= 0)

    if level_complete and s.get("username"):
        update_score(s["username"], s["score"])

    return jsonify({
        "is_treasure": is_treasure,
        "found": s["found"],
        "total": len(s["treasure_positions"]),
        "score": s["score"],
        "lives": s["lives"],
        "wrong_count": s["wrong_count"],
        "level_complete": level_complete,
        "game_over": game_over,
    })


@app.route("/api/hint", methods=["POST"])
def hint():
    data = request.get_json()
    session_id = data.get("session_id")
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    s = sessions[session_id]
    if s["hints_used"] >= 3:
        return jsonify({"hints_remaining": 0, "hint_text": "No hints left."}), 400

    s["hints_used"] += 1
    unrevealed = [i for i in s["treasure_positions"] if i not in s["revealed"]]
    highlight = quantum_int(len(unrevealed)) if unrevealed else None
    highlight_block = unrevealed[highlight] if unrevealed else None

    return jsonify({
        "hint_text": HINTS.get(s["theme"], ""),
        "highlight_block": highlight_block,
        "hints_remaining": 3 - s["hints_used"],
    })


@app.route("/api/level/complete", methods=["POST"])
def level_complete():
    data = request.get_json()
    session_id = data.get("session_id")
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    s = sessions[session_id]
    if s.get("username"):
        update_score(s["username"], s["score"])
    return jsonify({
        "final_score": s["score"],
        "next_level": s["level"] + 1 if s["level"] < 4 else None,
        "lives_remaining": s["lives"],
    })


# ══════════════════════════════════════════════════════════════
# MULTIPLAYER SocketIO  (multiplayer.py)
# ══════════════════════════════════════════════════════════════
@socketio.on("join_room")
def on_join(data):
    room_id = data.get("room_id", "global")
    username = data.get("username", "Anonymous")
    join_room(room_id)
    if room_id not in rooms:
        rooms[room_id] = {"players": {}}
    rooms[room_id]["players"][request.sid] = {"username": username, "score": 0}
    emit("room_update", {"msg": f"{username} entered the quantum realm", "players": list(rooms[room_id]["players"].values())}, to=room_id)

@socketio.on("move")
def on_move(data):
    room_id = data.get("room_id", "global")
    if room_id in rooms:
        p = rooms[room_id]["players"].get(request.sid, {})
        p["score"] = data.get("score", 0)
    emit("update", {"event": data, "players": list(rooms.get(room_id, {}).get("players", {}).values())}, to=room_id)

@socketio.on("disconnect")
def on_disconnect():
    for rid, room in rooms.items():
        if request.sid in room["players"]:
            u = room["players"].pop(request.sid, {}).get("username", "Player")
            emit("room_update", {"msg": f"{u} left"}, to=rid)

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n🔮  Lost in Random — Quantum Treasure Hunt")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  http://localhost:5000")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    socketio.run(app, debug=True, port=5000)

