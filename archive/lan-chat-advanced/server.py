from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
import os, time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

users = {}  # sid → username
sid_map = {}  # username → sid

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@socketio.on("join")
def join(data):
    username = data["username"]
    users[request.sid] = username
    sid_map[username] = request.sid

    emit("user_list", list(users.values()), broadcast=True)

@socketio.on("send_message")
def send_message(data):
    target = data["to"]
    
    msg = {
        "from": users[request.sid],
        "data": data["data"],  # encrypted
        "iv": data["iv"]
    }

    if target == "global":
        emit("new_message", msg, broadcast=True)
    else:
        if target in sid_map:
            emit("new_message", msg, to=sid_map[target])
            emit("new_message", msg, to=request.sid)

@socketio.on("upload")
def upload(data):
    filename = str(int(time.time())) + "_" + data["name"]
    path = os.path.join(UPLOAD_FOLDER, filename)

    with open(path, "wb") as f:
        f.write(data["file"])

    emit("file", {
        "user": users[request.sid],
        "url": "/uploads/" + filename,
        "type": data["type"]
    }, broadcast=True)

@socketio.on("disconnect")
def disconnect():
    username = users.get(request.sid)
    if username:
        sid_map.pop(username, None)
    users.pop(request.sid, None)

    emit("user_list", list(users.values()), broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000)
