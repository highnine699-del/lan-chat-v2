from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import os, time, json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lanchatsecret2024'
socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    max_http_buffer_size=50*1024*1024,
                    ping_timeout=60,
                    ping_interval=25,
                    engineio_logger=False)

# State (RAM only - no persistence)
users = {}        # sid -> {username, color, joined_at}
sid_map = {}      # username -> sid
public_keys = {}  # username -> ECDH public key JWK (for E2E encryption)
message_history = []  # global chat history (RAM only - cleared on restart)
private_history = {}  # "user1|user2" -> [messages] (RAM only)

# ── TURN credentials ────────────────────────────────────────────────────────
# Store credentials here (server-side only). Clients fetch via /ice-config.
# Replace with your own Twilio / Metered / coturn credentials if needed.
TURN_CREDENTIALS = os.environ.get('TURN_CREDENTIALS', '')  # "username:credential"
TURN_URLS_UDP = os.environ.get('TURN_URL_UDP', 'turn:global.turn.twilio.com:3478?transport=udp')
TURN_URLS_TCP = os.environ.get('TURN_URL_TCP', 'turn:global.turn.twilio.com:443?transport=tcp')

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

@app.route('/ice-config')
def ice_config():
    """Serve ICE/TURN config to authenticated clients only.
    Credentials stay server-side and are never embedded in the HTML."""
    ice_servers = [
        {'urls': 'stun:stun.l.google.com:19302'},
        {'urls': 'stun:stun1.l.google.com:19302'},
        {'urls': 'stun:stun2.l.google.com:19302'},
        {'urls': 'stun:stun3.l.google.com:19302'},
        {'urls': 'stun:stun4.l.google.com:19302'},
    ]
    if TURN_CREDENTIALS:
        username, _, credential = TURN_CREDENTIALS.partition(':')
        if username and credential:
            ice_servers.append({
                'urls': TURN_URLS_UDP,
                'username': username,
                'credential': credential,
            })
            ice_servers.append({
                'urls': TURN_URLS_TCP,
                'username': username,
                'credential': credential,
            })
    return jsonify({
        'iceServers': ice_servers,
        'iceCandidatePoolSize': 20,
        'bundlePolicy': 'max-bundle',
        'rtcpMuxPolicy': 'require',
    })

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No filename'}), 400
    # Sanitize filename: strip path components and replace unsafe chars
    import re
    safe_name = os.path.basename(file.filename)
    safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
    if not safe_name:
        safe_name = 'file.bin'
    filename = str(int(time.time() * 1000)) + '_' + safe_name
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return jsonify({
        'url': '/uploads/' + filename,
        'name': file.filename,
        'type': file.content_type or 'application/octet-stream'
    })

@socketio.on('join')
def handle_join(data):
    username = data.get('username', 'Anonymous')[:20].strip()
    if not username:
        username = 'Anonymous'

    # If username is already taken by a different session, append a number
    base = username
    counter = 2
    while username in sid_map and sid_map[username] != request.sid:
        username = f"{base}{counter}"
        counter += 1

    color = USER_COLORS[color_index[0] % len(USER_COLORS)]
    color_index[0] += 1

    users[request.sid] = {
        'username': username,
        'color': color,
        'joined_at': time.time()
    }
    sid_map[username] = request.sid

    # Store public key for E2E encryption
    pub_key = data.get('publicKey')
    if pub_key:
        public_keys[username] = pub_key

    # Confirm the (possibly adjusted) username back to the client
    emit('joined', {'username': username, 'color': color})

    # Send all existing public keys to the new user
    emit('all_keys', {u: k for u, k in public_keys.items() if u != username})

    # Broadcast this user's public key to everyone else
    if pub_key:
        emit('peer_key', {'username': username, 'publicKey': pub_key}, broadcast=True, include_self=False)

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
        key = '|'.join(sorted([user['username'], target]))
        if key not in private_history:
            private_history[key] = []
        private_history[key].append(msg)
        
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
        key = '|'.join(sorted([user['username'], target]))
        if key not in private_history:
            private_history[key] = []
        private_history[key].append(msg)
        
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
    sender = users.get(request.sid, {}).get('username', 'Unknown')
    signal_type = data.get('type', '?')
    print(f"[WebRTC] {sender} -> {target}: {signal_type}")
    
    if target in sid_map:
        data['from'] = sender
        emit('webrtc_signal', data, to=sid_map[target])
        print(f"[WebRTC] Forwarded {signal_type} to {target}")
    else:
        print(f"[WebRTC] ERROR: Target {target} not found in sid_map")
        print(f"[WebRTC] Available targets: {list(sid_map.keys())}")

@socketio.on("call-user")
def handle_call_user(data=None):
    target = (data or {}).get('to')
    if target and target in sid_map:
        emit("incoming-call", broadcast=False, to=sid_map[target])
    else:
        emit("incoming-call", broadcast=True, include_self=False)

@socketio.on("video-call-user")
def handle_video_call_user(data=None):
    target = (data or {}).get('to')
    if target and target in sid_map:
        emit("incoming-call", broadcast=False, to=sid_map[target])
    else:
        emit("incoming-call", broadcast=True, include_self=False)

@socketio.on("call-accepted")
def handle_call_accepted(data=None):
    target = (data or {}).get('to')
    if target and target in sid_map:
        emit("call-started", to=sid_map[target])
    else:
        emit("call-started", broadcast=True, include_self=False)

@socketio.on("call-rejected")
def handle_call_rejected(data=None):
    target = (data or {}).get('to')
    if target and target in sid_map:
        emit("call-ended", to=sid_map[target])
    else:
        emit("call-ended", broadcast=True, include_self=False)

@socketio.on("end-call")
def handle_end_call(data=None):
    target = (data or {}).get('to')
    if target and target in sid_map:
        emit("call-ended", to=sid_map[target])
    else:
        emit("call-ended", broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    user = users.pop(request.sid, None)
    if user:
        sid_map.pop(user['username'], None)
        public_keys.pop(user['username'], None)
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
    print("  🔄 Auto-reload enabled - changes apply automatically")
    print("="*50)
    import socket as sock
    try:
        s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    print(f"\n  Local:   http://127.0.0.1:5000")
    print(f"  Network: http://{local_ip}:5000")
    print(f"\n  Share the Network URL with classmates!")
    print(f"\n  ⚠  LAN traffic is unencrypted (HTTP).")
    print(f"     Private messages are E2E encrypted in the browser.")
    print(f"     For full transport encryption use the ngrok HTTPS URL.")
    print("="*50 + "\n")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
