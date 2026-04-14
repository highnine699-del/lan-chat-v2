# 🔵 LAN Chat - Final Version

## 📂 Project Structure

```
local-whatsapp/
├── lan-chat-final/          ⭐ CURRENT WORKING VERSION
│   ├── server.py
│   ├── templates/
│   │   └── index.html
│   ├── static/
│   ├── uploads/
│   └── README.md
│
├── archive/                 📦 Older versions (archived)
│   ├── lan-chat-advanced/
│   ├── lan-chat-python/
│   └── lan-chat-v3/
│
├── .gitignore
└── README.md (this file)
```

## 🚀 Getting Started

**All development happens in `lan-chat-final/`**

```bash
cd lan-chat-final
python server.py
```

Then open your browser to:
- Local: `http://127.0.0.1:3000`
- Network: `http://<YOUR_LOCAL_IP>:3000`

## ✨ Features

- 💬 Global & private messaging
- 📞 Audio calls (WebRTC)
- 📹 Video calls (WebRTC)
- 📎 File sharing
- 🎤 Voice messages
- 😊 Emoji picker
- 🖼️ Image viewer

## 📋 Recent Updates

- ✅ Added WebRTC call lifecycle handlers
- ✅ Implemented mute/video toggle
- ✅ Added .gitignore for uploads & media files

---

**Note:** Older versions are preserved in the `archive/` folder for reference only.
