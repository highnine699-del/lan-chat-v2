# 🚀 LAN CHAT V2 — QUICK START GUIDE

## 30-Second Setup

### 1. Start Server:
```bash
cd "C:\Users\AY ADVANCE TECH\Documents\lan-chat-v2\backend"
python main.py
```

You should see:
```
INFO:     Started server process [10668]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Open Browser:
```
http://127.0.0.1:8000
```

### 3. Test:
- Open **2+ browser tabs** at the same URL
- Type a message in one tab
- **Message appears instantly** in the other tab ✅

---

## 🎯 What You Can Do Now

### Chat in Real-Time:
- Send messages
- See who's typing
- See who's online
- Messages appear instantly

### Message History:
- Join a room → see last 20 messages
- Restart server → messages still there (database)
- See timestamps on all messages

### User Presence:
- "User X joined" notifications
- Online count at top
- User list on right side
- "User X is typing..." indicator

---

## 📊 System Information

### Server:
- **Port:** 8000
- **Database:** `backend/chat.db` (auto-created)
- **Frontend:** Single page HTML (`frontend/index.html`)
- **Backend:** Python FastAPI + Socket.IO

### Architecture:
```
Browser → Socket.IO → Event Handler → Database + Broadcast
```

### Files:
```
backend/main.py          ← Start here
backend/app.py           ← FastAPI app
backend/db.py            ← Database
backend/core/            ← Core modules
backend/events/          ← Socket handlers
```

---

## 🔧 Advanced Features

### Admin Tools (Browser Console):
```javascript
// Get event statistics
socket.emit('get_event_stats')

// Get event history
socket.emit('get_event_history', null, 50)
```

### Database Queries:
```bash
# View all messages:
sqlite3 backend/chat.db "SELECT sender_id, content, created_at FROM messages ORDER BY created_at DESC LIMIT 10;"

# View user sessions:
sqlite3 backend/chat.db "SELECT sid, connected_at FROM sessions;"
```

---

## 🐛 Troubleshooting

### Issue: "Port 8000 already in use"
```bash
# Kill existing process:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
python main.py
```

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
```bash
# Install dependencies:
pip install -r requirements.txt
```

### Issue: Messages not appearing across tabs
1. Check browser console (F12) for errors
2. Ensure both tabs are at `http://127.0.0.1:8000`
3. Restart server and refresh both tabs

---

## 📱 Using on Other Devices

### Same Network:
1. Find your computer's IP: `ipconfig` → IPv4 Address (e.g., 192.168.1.100)
2. On other device, visit: `http://192.168.1.100:8000`
3. Chat works the same way

### Over Internet:
```bash
# Install ngrok: https://ngrok.com
ngrok http 8000

# Share the URL it generates
# Example: https://abc123.ngrok.io
```

---

## 📊 Database Structure

### Key Tables:
- **messages** — All messages (timestamped, indexed)
- **users** — User accounts
- **sessions** — Active connections
- **rooms** — Chat rooms
- **room_members** — Room membership

### View Database:
```bash
# Install DB browser (optional):
# https://sqlitebrowser.org/

# Or use command line:
sqlite3 backend/chat.db
> .tables
> SELECT COUNT(*) FROM messages;
> .quit
```

---

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Type...` | Typing indicator |
| `Ctrl+R` | Refresh chat |
| `F12` | Open dev console |

---

## 📈 Performance

### Tested With:
- ✅ 2+ concurrent users
- ✅ 100+ messages
- ✅ Message history loading
- ✅ Real-time updates

### Optimized For:
- ✅ LAN (same network)
- ✅ SQLite (no server needed)
- ✅ Instant message delivery
- ✅ Low latency reconnection

---

## 🔒 Security Notes

### Currently:
- ✅ Messages stored locally
- ✅ Session tracking
- ✅ User presence tracking

### Not Yet Implemented:
- ⏳ User authentication (coming Phase 12)
- ⏳ End-to-end encryption (coming Phase 12)
- ⏳ SSL/TLS for internet (recommended for production)

---

## 📚 Documentation

Full documentation available in:
- `COMPLETE_INFRASTRUCTURE.md` — Full technical overview
- `AUTONOMOUS_BUILD_COMPLETE.md` — What was built
- `PHASE4_NOTES.md` — State management details
- `PHASES_4_5_COMPLETE.md` — Persistence layer

---

## 🎯 Next Steps

### To Add Features:
1. Event handlers go in `backend/events/chat_events.py`
2. New event types in `core/events.py`
3. Database updates in `db.py`
4. Frontend listeners in `frontend/index.html`

### To Enable Encryption (Phase 12):
See authentication system in `core/` (schema ready)

### To Add Plugins:
Event bus supports listener callbacks (ready for plugin system)

---

## ⚡ Performance Tips

### For Many Users:
1. Add database indexing (already done for messages)
2. Enable Redis for presence caching
3. Use Gunicorn with multiple workers

### For Mobile:
1. Optimize frontend (Svelte planned for Phase 10)
2. Enable service workers for offline support
3. Compress images/media

---

## 📞 Support

### Check Logs:
```bash
# Server logs shown in terminal where you ran `python main.py`
# Browser logs in F12 Developer Console
```

### Event Statistics:
```bash
# In browser console:
socket.emit('get_event_stats')
```

### Database Status:
```bash
ls -lh backend/chat.db  # Check file size
```

---

## 🎉 You're Ready!

**System is production-ready for LAN deployment.**

Start it up, open a browser, and chat!

```bash
python main.py
# Open http://127.0.0.1:8000
# Start chatting!
```

Enjoy! 🚀
