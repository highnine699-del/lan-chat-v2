/**
 * ui/sidebarManager.js
 *
 * Renders the sidebar user/room lists and handles chat switching.
 */

import { chatState } from '../core/state/chatState.js';
import { eventBus } from '../core/eventBus.js';
import { UserItem } from './components/UserItem.js';
import { roomUI } from '../rooms/roomUI.js';
import { messageRenderer } from '../messages/index.js';

const userItems = new Map();

export const sidebarManager = {
  _initialized: false,

  init() {
    if (this._initialized) return;

    eventBus.on('presence:user_list', (users) => this.renderUserList(users));
    eventBus.on('presence:updated', (user) => this.updateUser(user));
    eventBus.on('room:list', (rooms) => this.renderRoomList(rooms));
    eventBus.on('room:created', () => {
      if (chatState.roomList?.length) this.renderRoomList(chatState.roomList);
    });
    eventBus.on('room:joined', (data) => {
      if (data?.room_id) this.switchToRoom(data.room_id, data.name);
    });
    eventBus.on('room:left', () => this.switchChat('global'));
    eventBus.on('room:deleted', (data) => {
      const el = document.getElementById('chat-item-room-' + data.room_id);
      if (el) el.remove();
      if (chatState.currentRoom === data.room_id) this.switchChat('global');
    });

    const globalItem = document.getElementById('chat-item-global');
    if (globalItem) {
      globalItem.onclick = () => this.switchChat('global');
    }

    this._initialized = true;
  },

  renderUserList(users) {
    document.querySelectorAll('.chat-item.user-item').forEach(el => el.remove());
    userItems.clear();

    const list = document.getElementById('chat-list');
    if (!list || !users?.length) return;

    const myDisplay = chatState.getDisplay();

    users.forEach(user => {
      if (!user?.display || user.display === myDisplay) return;

      const item = new UserItem(user, {
        isActive: chatState.currentChat === user.display,
        onClick: (display) => this.switchChat(display),
        onMute: (display) => {
          if (chatState.isMuted(display)) {
            chatState.unmuteUser(display);
          } else {
            chatState.muteUser(display);
          }
        },
      });

      const el = item.render();
      list.appendChild(el);
      userItems.set(user.display, item);
    });
  },

  updateUser(user) {
    const item = userItems.get(user.display);
    if (item) {
      item.update(user);
    } else {
      this.renderUserList(chatState.users);
    }
  },

  renderRoomList(rooms) {
    roomUI.renderRoomList(rooms, (roomId) => {
      // If already in this room, just switch the view — don't re-join (which
      // would cause the server to kick-and-readd, resetting history and keys).
      if (chatState.currentRoom === roomId) {
        this.switchChat(roomId);
        return;
      }
      const socket = chatState.getSocket();
      if (socket) {
        window.LANCHAT?.rooms?.manager?.joinPublicRoom(roomId, socket);
      }
    });
  },

  switchToRoom(roomId, name) {
    chatState.setCurrentRoom(roomId, name || '');
    chatState.setCurrentChat(roomId);

    // If there's no sidebar item for this room yet (e.g. private rooms don't
    // appear in the public room:list), create one so the user can switch back.
    if (!document.getElementById('chat-item-room-' + roomId)) {
      const list = document.getElementById('chat-list');
      if (list) {
        roomUI.renderRoomList(
          [{ room_id: roomId, name: name || roomId, members: 1, is_frozen: false }],
          (rid) => {
            if (chatState.currentRoom === rid) { this.switchChat(rid); return; }
            const socket = chatState.getSocket();
            if (socket) window.LANCHAT?.rooms?.manager?.joinPublicRoom(rid, socket);
          }
        );
      }
    }

    this._applyChatUI(roomId, name || 'Group', `Room: ${roomId}`, true);
    roomUI.showRoomIdBanner(roomId);
  },

  switchChat(chatId) {
    if (chatId === 'global') {
      chatState.setCurrentRoom(null, '');
      chatState.setCurrentChat('global');
      roomUI.hideRoomIdBanner();
      this._applyChatUI('global', 'Global Chat', 'Everyone online', false);
      return;
    }

    const isRoom = chatState.roomList?.some(r => r.room_id === chatId);
    if (isRoom) {
      const room = chatState.roomList.find(r => r.room_id === chatId);
      chatState.setCurrentRoom(chatId, room?.name || '');
      chatState.setCurrentChat(chatId);
      roomUI.showRoomIdBanner(chatId);
      this._applyChatUI(chatId, room?.name || chatId, `${room?.members || 0} members`, true);
      return;
    }

    chatState.setCurrentRoom(null, '');
    chatState.setCurrentChat(chatId);
    roomUI.hideRoomIdBanner();

    const user = chatState.users.find(u => u.display === chatId);
    const status = user?.online ? 'Online' : 'Offline';
    this._applyChatUI(chatId, chatId, status, false, user);
  },

  _applyChatUI(chatId, headerName, headerStatus, isRoom, user) {
    document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));

    let activeEl;
    if (chatId === 'global') {
      activeEl = document.getElementById('chat-item-global');
    } else if (isRoom) {
      activeEl = document.getElementById('chat-item-room-' + chatId);
    } else {
      activeEl = document.getElementById('chat-item-' + CSS.escape(chatId));
    }
    if (activeEl) activeEl.classList.add('active');

    const placeholder = document.getElementById('chat-placeholder');
    const activeChat = document.getElementById('active-chat');
    if (placeholder) placeholder.style.display = 'none';
    if (activeChat) activeChat.style.display = 'flex';

    const nameEl = document.getElementById('header-name');
    const statusEl = document.getElementById('header-status');
    const avatarEl = document.getElementById('header-avatar');
    if (nameEl) nameEl.textContent = headerName;
    if (statusEl) statusEl.textContent = headerStatus;
    if (avatarEl && user?.color) {
      avatarEl.style.background = user.color;
    }

    chatState.clearUnread(chatId);

    this._renderMessages(chatId);

    const showCalls = chatId !== 'global' && !isRoom;
    const voiceBtn = document.getElementById('voice-call-btn');
    const videoBtn = document.getElementById('video-call-btn');
    if (voiceBtn) voiceBtn.style.display = showCalls ? '' : 'none';
    if (videoBtn) videoBtn.style.display = showCalls ? '' : 'none';

    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (overlay) overlay.classList.remove('active');

    eventBus.emit('chat:switched', { chatId });
  },

  _renderMessages(chatId) {
    const container = document.getElementById('messages');
    if (!container) return;

    container.innerHTML = '';
    const messages = chatState.getMessages(chatId);
    const display = chatState.getDisplay();

    messages.forEach(msg => {
      const isOwn = msg.from === display;
      const el = messageRenderer.createMessageElement(msg, { isOwn });
      if (el) container.appendChild(el);
    });

    container.scrollTop = container.scrollHeight;
  },
};
