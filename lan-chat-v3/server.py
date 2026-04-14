from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import os, time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

users = {}        # sid → username
sid_map = {}      # username → sid
public_keys = {}  # username → public key

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    filename = str(int(time.time())) + "_" + file.filename
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return jsonify({"url": f"/uploads/{filename}"})

# JOIN
@socketio.on("join")
def join(data):
    username = data["username"]
    users[request.sid] = username
    sid_map[username] = request.sid
    public_keys[username] = data["publicKey"]

    emit("user_list", list(users.values()), broadcast=True)
    emit("public_keys", public_keys, broadcast=True)

# MESSAGE RELAY
@socketio.on("send_message")
def send_message(data):
    target = data["to"]

    if target in sid_map:
        emit("new_message", data, to=sid_map[target])
        emit("new_message", data, to=request.sid)

# FILE
@socketio.on("file")
def handle_file(url):
    emit("file", url, broadcast=True)

# WEBRTC SIGNALING
@socketio.on("signal")
def signal(data):
    target = data["to"]
    if target in sid_map:
        emit("signal", data, to=sid_map[target])

# DISCONNECT
@socketio.on("disconnect")
def disconnect():
    username = users.get(request.sid)
    if username:
        sid_map.pop(username, None)
        public_keys.pop(username, None)

    users.pop(request.sid, None)

    emit("user_list", list(users.values()), broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000)
