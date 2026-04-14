from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

users_db = {}      # username -> password
sessions = {}      # sid -> username
messages = []      # chat history

@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html>
<head>
<title>LAN Chat</title>
<style>
body { font-family: Arial; background:#0b141a; color:white; margin:0 }
#login, #chat { display:flex; flex-direction:column; align-items:center; margin-top:50px }
input { padding:10px; margin:5px; border:none; border-radius:5px }
button { padding:10px; background:#25D366; border:none; border-radius:5px; cursor:pointer }
#messages { width:90%; max-width:600px; height:400px; overflow-y:auto; background:#111; padding:10px; border-radius:10px }
.msg { margin:5px; padding:10px; border-radius:10px; max-width:70% }
.me { background:#005c4b; align-self:flex-end }
.other { background:#202c33; align-self:flex-start }
#users { position:fixed; right:10px; top:10px; background:#111; padding:10px; border-radius:10px }
</style>
</head>
<body>

<div id="login">
<h2>Login / Register</h2>
<input id="username" placeholder="Username">
<input id="password" type="password" placeholder="Password">
<button onclick="login()">Enter</button>
</div>

<div id="chat" style="display:none;">
<h3>LAN Chat</h3>
<div id="messages"></div>
<input id="msg" placeholder="Type message">
<button onclick="sendMsg()">Send</button>
</div>

<div id="users"></div>

<script src="https://cdn.socket.io/4.0.1/socket.io.min.js"></script>
<script>
let socket;
let username;

function login(){
    username = document.getElementById("username").value;
    let password = document.getElementById("password").value;

    if(!username || !password) return;

    socket = io();

    socket.emit("login", {username, password});

    socket.on("login_success", data => {
        document.getElementById("login").style.display="none";
        document.getElementById("chat").style.display="flex";

        data.messages.forEach(m => addMsg(m));
    });

    socket.on("message", addMsg);

    socket.on("users", list => {
        document.getElementById("users").innerHTML = "<b>Online:</b><br>" + list.join("<br>");
    });
}

function addMsg(data){
    let div = document.createElement("div");
    div.className = "msg " + (data.user === username ? "me" : "other");
    div.innerText = data.user + ": " + data.msg;
    document.getElementById("messages").appendChild(div);
}

function sendMsg(){
    let input = document.getElementById("msg");
    socket.emit("message", input.value);
    input.value = "";
}
</script>

</body>
</html>
"""

@socketio.on("login")
def handle_login(data):
    username = data["username"]
    password = data["password"]

    if username in users_db:
        if users_db[username] != password:
            return
    else:
        users_db[username] = password

    sessions[request.sid] = username

    emit("login_success", {"messages": messages})

    emit("users", list(sessions.values()), broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    sessions.pop(request.sid, None)
    emit("users", list(sessions.values()), broadcast=True)

@socketio.on("message")
def handle_message(msg):
    user = sessions.get(request.sid, "Unknown")
    data = {"user": user, "msg": msg}
    messages.append(data)
    emit("message", data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000)
