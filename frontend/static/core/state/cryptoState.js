/**
 * core/state/cryptoState.js
 * 
 * Cryptography state - keys, shared secrets, room keys.
 * Pure functions only, no side effects.
 */

export const cryptoState = {
  myKeyPair: null,
  myPublicKeyJwk: null,
  peerPublicKeys: {},
  sharedSecrets: {},
  roomKeys: {},
  pendingDecrypt: {},

  /**
   * Set our key pair
   * @param {CryptoKey} keyPair - ECDH key pair
   */
  setKeyPair(keyPair) {
    this.myKeyPair = keyPair;
  },

  /**
   * Set our public key JWK
   * @param {Object} jwk - JWK public key
   */
  setPublicKeyJwk(jwk) {
    this.myPublicKeyJwk = jwk;
  },

  /**
   * Register a peer's public key
   * @param {string} username - Peer's username
   * @param {CryptoKey} publicKey - Peer's public key
   */
  setPeerPublicKey(username, publicKey) {
    this.peerPublicKeys[username] = publicKey;
  },

  /**
   * Get a peer's public key
   * @param {string} username - Peer's username
   * @returns {CryptoKey|null} Public key or null
   */
  getPeerPublicKey(username) {
    return this.peerPublicKeys[username] || null;
  },

  /**
   * Set shared secret for a peer
   * @param {string} username - Peer's username
   * @param {CryptoKey} secret - Shared secret
   */
  setSharedSecret(username, secret) {
    this.sharedSecrets[username] = secret;
  },

  /**
   * Get shared secret for a peer
   * @param {string} username - Peer's username
   * @returns {CryptoKey|null} Shared secret or null
   */
  getSharedSecret(username) {
    return this.sharedSecrets[username] || null;
  },

  /**
   * Set room key
   * @param {string} roomId - Room ID
   * @param {CryptoKey} key - Room key
   */
  setRoomKey(roomId, key) {
    this.roomKeys[roomId] = key;
  },

  /**
   * Get room key
   * @param {string} roomId - Room ID
   * @returns {CryptoKey|null} Room key or null
   */
  getRoomKey(roomId) {
    return this.roomKeys[roomId] || null;
  },

  /**
   * Delete room key
   * @param {string} roomId - Room ID
   */
  deleteRoomKey(roomId) {
    delete this.roomKeys[roomId];
  },

  /**
   * Add message to pending decrypt queue
   * @param {string} roomId - Room ID
   * @param {Object} msg - Message object
   */
  addToPendingDecrypt(roomId, msg) {
    if (!this.pendingDecrypt[roomId]) this.pendingDecrypt[roomId] = [];
    this.pendingDecrypt[roomId].push(msg);
  },

  /**
   * Get and clear pending decrypt queue for a room
   * @param {string} roomId - Room ID
   * @returns {Array} Pending messages
   */
  flushPendingDecrypt(roomId) {
    const pending = this.pendingDecrypt[roomId] || [];
    delete this.pendingDecrypt[roomId];
    return pending;
  },

  /**
   * Check if room has pending decrypt messages
   * @param {string} roomId - Room ID
   * @returns {boolean} True if has pending messages
   */
  hasPendingDecrypt(roomId) {
    return !!(this.pendingDecrypt[roomId] && this.pendingDecrypt[roomId].length > 0);
  }
};
