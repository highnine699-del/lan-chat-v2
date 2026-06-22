/**
 * core/state/chatState.js
 * 
 * Chat state management - messages, users, rooms, typing indicators.
 * Pure functions only, no side effects.
 */

export const chatState = {
  // Identity state (from window.state)
  username: null,
  display: null,
  uid: null,
  socket: null,

  // Chat state
  messages: { global: [] },
  users: [],
  currentChat: 'global',
  currentRoom: null,
  currentRoomName: '',
  roomList: [],
  typingUsers: {},
  typingTimers: {},
  unread: {},
  mutedUsers: new Set(),
  replyTo: null,
  preJoinQueue: [],
  offlineQueue: [],

  /**
   * Add a message to the appropriate chat
   * @param {Object} msg - Message object
   */
  addMessage(msg) {
    const chatId = this._getChatId(msg);
    if (!this.messages[chatId]) this.messages[chatId] = [];
    
    // Insert in sequence/timestamp order
    const arr = this.messages[chatId];
    const msgOrder = msg.seq !== undefined ? msg.seq : msg.time;
    const insertAt = arr.findIndex(m => {
      const mOrder = m.seq !== undefined ? m.seq : m.time;
      return mOrder > msgOrder;
    });
    
    if (insertAt === -1) {
      arr.push(msg);
    } else {
      arr.splice(insertAt, 0, msg);
    }
  },

  /**
   * Get messages for a chat
   * @param {string} chatId - Chat ID
   * @returns {Array} Messages array
   */
  getMessages(chatId) {
    return this.messages[chatId] || [];
  },

  /**
   * Set current chat
   * @param {string} chatId - Chat ID
   */
  setCurrentChat(chatId) {
    this.currentChat = chatId;
  },

  /**
   * Set current room
   * @param {string} roomId - Room ID
   * @param {string} name - Room name
   */
  setCurrentRoom(roomId, name = '') {
    this.currentRoom = roomId;
    this.currentRoomName = name;
  },

  /**
   * Update users list
   * @param {Array} users - Users array
   */
  setUsers(users) {
    this.users = users;
  },

  /**
   * Update room list
   * @param {Array} rooms - Rooms array
   */
  setRoomList(rooms) {
    this.roomList = rooms;
  },

  /**
   * Add typing user
   * @param {string} chatId - Chat ID
   * @param {string} username - Username
   */
  addTypingUser(chatId, username) {
    if (!this.typingUsers[chatId]) this.typingUsers[chatId] = new Set();
    this.typingUsers[chatId].add(username);
  },

  /**
   * Remove typing user
   * @param {string} chatId - Chat ID
   * @param {string} username - Username
   */
  removeTypingUser(chatId, username) {
    if (this.typingUsers[chatId]) this.typingUsers[chatId].delete(username);
  },

  /**
   * Get typing users for a chat
   * @param {string} chatId - Chat ID
   * @returns {Set} Set of typing usernames
   */
  getTypingUsers(chatId) {
    return this.typingUsers[chatId] || new Set();
  },

  /**
   * Increment unread count for a chat
   * @param {string} chatId - Chat ID
   */
  incrementUnread(chatId) {
    this.unread[chatId] = (this.unread[chatId] || 0) + 1;
  },

  /**
   * Clear unread count for a chat
   * @param {string} chatId - Chat ID
   */
  clearUnread(chatId) {
    this.unread[chatId] = 0;
  },

  /**
   * Get unread count for a chat
   * @param {string} chatId - Chat ID
   * @returns {number} Unread count
   */
  getUnread(chatId) {
    return this.unread[chatId] || 0;
  },

  /**
   * Mute a user
   * @param {string} display - User display name
   */
  muteUser(display) {
    this.mutedUsers.add(display);
  },

  /**
   * Unmute a user
   * @param {string} display - User display name
   */
  unmuteUser(display) {
    this.mutedUsers.delete(display);
  },

  /**
   * Check if user is muted
   * @param {string} display - User display name
   * @returns {boolean} True if muted
   */
  isMuted(display) {
    return this.mutedUsers.has(display);
  },

  /**
   * Set reply-to message
   * @param {Object} replyTo - Reply-to message object
   */
  setReplyTo(replyTo) {
    this.replyTo = replyTo;
  },

  /**
   * Clear reply-to
   */
  clearReplyTo() {
    this.replyTo = null;
  },

  /**
   * Add message to pre-join queue
   * @param {Object} msg - Message object
   */
  addToPreJoinQueue(msg) {
    this.preJoinQueue.push(msg);
  },

  /**
   * Get and clear pre-join queue
   * @returns {Array} Pre-join queue
   */
  flushPreJoinQueue() {
    const queue = [...this.preJoinQueue];
    this.preJoinQueue = [];
    return queue;
  },

  /**
   * Add message to offline queue
   * @param {Object} payload - Message payload
   */
  addToOfflineQueue(payload) {
    this.offlineQueue.push(payload);
  },

  /**
   * Get and clear offline queue
   * @returns {Array} Offline queue
   */
  flushOfflineQueue() {
    const queue = [...this.offlineQueue];
    this.offlineQueue = [];
    return queue;
  },

  /**
   * Helper to determine chat ID from message
   * @private
   * @param {Object} msg - Message object
   * @returns {string} Chat ID
   */
  _getChatId(msg) {
    if (msg.to === 'global') return 'global';
    const isRoomMsg = msg.to && (msg.to === this.currentRoom || this.currentRoom === msg.to);
    if (isRoomMsg) return msg.to;
    // DMs: always key by the OTHER person's display name regardless of which
    // chat the user currently has open.  Using currentChat here was the bug —
    // it changes as the user navigates, so the same message could be stored
    // under a different key depending on navigation state.
    const myDisplay = this.display;
    return msg.from === myDisplay ? msg.to : msg.from;
  },

  /**
   * Set username
   * @param {string} username - Username
   */
  setUsername(username) {
    this.username = username;
  },

  /**
   * Get username
   * @returns {string|null} Username
   */
  getUsername() {
    return this.username;
  },

  /**
   * Set display name
   * @param {string} display - Display name
   */
  setDisplay(display) {
    this.display = display;
  },

  /**
   * Get display name
   * @returns {string|null} Display name
   */
  getDisplay() {
    return this.display;
  },

  /**
   * Set user ID
   * @param {string} uid - User ID
   */
  setUid(uid) {
    this.uid = uid;
  },

  /**
   * Get user ID
   * @returns {string|null} User ID
   */
  getUid() {
    return this.uid;
  },

  /**
   * Set socket instance
   * @param {Object} socket - Socket instance
   */
  setSocket(socket) {
    this.socket = socket;
  },

  /**
   * Get socket instance
   * @returns {Object|null} Socket instance
   */
  getSocket() {
    return this.socket;
  }
};
