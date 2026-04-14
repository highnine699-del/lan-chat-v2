from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import os, time, json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lanchatsecret2024'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50*1024*1024)

# State
users = {}       # sid -> {username, color, joined_at}
sid_map = {}     # username -> sid
public_keys = {} # username -> public key
message_history = []  # global chat history (RAM only)
private_history = {}  # "user1|user2" -> [messages]

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USER_COLORS = [
    '#25D366', '#00a884', '#53bdeb', '#f0b429',
    '#e06c75', '#c678dd', '#56b6c2', '#e5c07b'
]
color_index = [0]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    ext = os.path.splitext(file.filename)[1] if file.filename else '.bin'
    filename = str(int(time.time() * 1000)) + '_' + (file.filename or 'file' + ext)
    # sanitize
    filename = filename.replace(' ', '_')
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return jsonify({
        'url': '/uploads/' + filename,
        'name': file.filename or 'file',
        'type': file.content_type or 'application/octet-stream'
    })

@socketio.on('join')
def handle_join(data):
    username = data.get('username', 'Anonymous')[:20]
    color = USER_COLORS[color_index[0] % len(USER_COLORS)]
    color_index[0] += 1

    users[request.sid] = {
        'username': username,
        'color': color,
        'joined_at': time.time()
    }
    sid_map[username] = request.sid

    # Send history to new user
    emit('message_history', message_history[-100:])

    # Broadcast updated user list
    emit('user_list', get_user_list(), broadcast=True)
    
    # Announce join
    system_msg = {
        'type': 'system',
        'text': f'{username} joined',
        'time': int(time.time() * 1000)
    }
    emit('system_message', system_msg, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    user = users.get(request.sid)
    if not user:
        return

    target = data.get('to', 'global')
    text = data.get('text', '').strip()
    if not text:
        return

    msg = {
        'type': 'text',
        'from': user['username'],
        'color': user['color'],
        'text': text,
        'time': int(time.time() * 1000),
        'to': target
    }

    if target == 'global':
        message_history.append(msg)
        if len(message_history) > 500:
            message_history.pop(0)
        emit('new_message', msg, broadcast=True)
    else:
        # Private message
        if target in sid_map:
            emit('new_message', msg, to=sid_map[target])
        emit('new_message', msg, to=request.sid)

@socketio.on('send_file')
def handle_file(data):
    user = users.get(request.sid)
    if not user:
        return

    msg = {
        'type': 'file',
        'from': user['username'],
        'color': user['color'],
        'url': data['url'],
        'name': data['name'],
        'file_type': data.get('file_type', 'file'),
        'time': int(time.time() * 1000),
        'to': data.get('to', 'global')
    }

    target = data.get('to', 'global')
    if target == 'global':
        message_history.append(msg)
        emit('new_message', msg, broadcast=True)
    else:
        if target in sid_map:
            emit('new_message', msg, to=sid_map[target])
        emit('new_message', msg, to=request.sid)

@socketio.on('typing')
def handle_typing(data):
    user = users.get(request.sid)
    if not user:
        return
    target = data.get('to', 'global')
    payload = {'username': user['username'], 'to': target}
    
    if target == 'global':
        emit('typing', payload, broadcast=True, include_self=False)
    elif target in sid_map:
        emit('typing', payload, to=sid_map[target])

@socketio.on('stop_typing')
def handle_stop_typing(data):
    user = users.get(request.sid)
    if not user:
        return
    target = data.get('to', 'global')
    payload = {'username': user['username'], 'to': target}
    if target == 'global':
        emit('stop_typing', payload, broadcast=True, include_self=False)
    elif target in sid_map:
        emit('stop_typing', payload, to=sid_map[target])

@socketio.on('webrtc_signal')
def handle_signal(data):
    target = data.get('to')
    if target in sid_map:
        data['from'] = users[request.sid]['username']
        emit('webrtc_signal', data, to=sid_map[target])

@socketio.on("call-user")
def handle_call_user():
    emit("incoming-call", broadcast=True, include_self=False)

@socketio.on("video-call-user")
def handle_video_call_user():
    emit("incoming-call", broadcast=True, include_self=False)

@socketio.on("call-accepted")
def handle_call_accepted():
    emit("call-started", broadcast=True, include_self=False)

@socketio.on("call-rejected")
def handle_call_rejected():
    emit("call-ended", broadcast=True, include_self=False)

@socketio.on("end-call")
def handle_end_call():
    emit("call-ended", broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        sid_map.pop(user['username'], None)
        emit('user_list', get_user_list(), broadcast=True)
        emit('system_message', {
            'type': 'system',
            'text': f"{user['username']} left",
            'time': int(time.time() * 1000)
        }, broadcast=True)

def get_user_list():
    return [
        {'username': u['username'], 'color': u['color']}
        for u in users.values()
    ]

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  LAN CHAT - Starting server...")
    print("="*50)
    import socket as sock
    try:
        s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    print(f"\n  Local:   http://127.0.0.1:3000")
    print(f"  Network: http://{local_ip}:3000")
    print(f"\n  Share the Network URL with classmates!")
    print("="*50 + "\n")
    socketio.run(app, host='0.0.0.0', port=3000, debug=False)
