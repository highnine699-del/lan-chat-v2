/**
 * core/encryption.js
 * 
 * E2E encryption module using Web Crypto API.
 * Handles ECDH key generation, shared secret derivation, and AES-GCM encryption/decryption.
 */

export const encryption = {
  myKeyPair: null,
  myPublicKeyJwk: null,
  peerPublicKeys: {},
  sharedSecrets: {},
  roomKeys: {},

  /**
   * Generate our ECDH key pair
   * @returns {Promise<Object>} JWK public key
   */
  async generateKeys() {
    this.myKeyPair = await crypto.subtle.generateKey(
      { name: 'ECDH', namedCurve: 'P-256' },
      true,
      ['deriveKey']
    );
    this.myPublicKeyJwk = await crypto.subtle.exportKey('jwk', this.myKeyPair.publicKey);
    return this.myPublicKeyJwk;
  },

  /**
   * Import a peer's JWK public key
   * @param {Object} jwk - JWK public key
   * @returns {Promise<CryptoKey>} Imported public key
   */
  async importPeerKey(jwk) {
    return crypto.subtle.importKey(
      'jwk', jwk,
      { name: 'ECDH', namedCurve: 'P-256' },
      true,
      []
    );
  },

  /**
   * Derive a shared AES-GCM key from our private key + peer's public key
   * @param {CryptoKey} peerPublicKey - Peer's public key
   * @returns {Promise<CryptoKey>} Shared secret key
   */
  async deriveSharedKey(peerPublicKey) {
    return crypto.subtle.deriveKey(
      { name: 'ECDH', public: peerPublicKey },
      this.myKeyPair.privateKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  },

  /**
   * Get (or derive) the shared key for a peer
   * @param {string} username - Peer's username
   * @returns {Promise<CryptoKey|null>} Shared secret key or null if not available
   */
  async getSharedKey(username) {
    if (this.sharedSecrets[username]) return this.sharedSecrets[username];
    const peerKey = this.peerPublicKeys[username];
    if (!peerKey) return null;
    const key = await this.deriveSharedKey(peerKey);
    this.sharedSecrets[username] = key;
    return key;
  },

  /**
   * Encrypt a plaintext string for a peer
   * @param {string} plaintext - Text to encrypt
   * @param {string} username - Target username
   * @returns {Promise<string|null>} Base64-encoded (iv + ciphertext) or null on failure
   */
  async encrypt(plaintext, username) {
    const key = await this.getSharedKey(username);
    if (!key) return null;
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plaintext);
    const cipherBuf = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
    const combined = new Uint8Array(iv.byteLength + cipherBuf.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(cipherBuf), iv.byteLength);
    return btoa(String.fromCharCode(...combined));
  },

  /**
   * Decrypt a base64(iv + ciphertext) string from a peer
   * @param {string} b64 - Base64-encoded ciphertext
   * @param {string} username - Sender's username
   * @returns {Promise<string|null>} Decrypted plaintext or null on failure
   */
  async decrypt(b64, username) {
    const key = await this.getSharedKey(username);
    if (!key) return null;
    try {
      const combined = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const iv = combined.slice(0, 12);
      const cipherBuf = combined.slice(12);
      const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, cipherBuf);
      return new TextDecoder().decode(plainBuf);
    } catch {
      return null;
    }
  },

  /**
   * Register a peer's public key and derive shared secret immediately
   * @param {string} username - Peer's username
   * @param {Object} jwk - Peer's JWK public key
   */
  async registerPeerKey(username, jwk) {
    if (this.peerPublicKeys[username]) return;
    const pubKey = await this.importPeerKey(jwk);
    this.peerPublicKeys[username] = pubKey;
    const shared = await this.deriveSharedKey(pubKey);
    this.sharedSecrets[username] = shared;
    console.log(`[E2E] Shared key derived with ${username}`);
  },

  // -- Room session key methods --

  /**
   * Generate a fresh AES-GCM-256 session key for a room
   * @param {string} roomId - Room ID
   * @returns {Promise<CryptoKey>} Room key
   */
  async generateRoomKey(roomId) {
    const key = await crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );
    this.roomKeys[roomId] = key;
    return key;
  },

  /**
   * Export a room key as JWK for server relay
   * @param {string} roomId - Room ID
   * @returns {Promise<Object|null>} JWK key or null if not found
   */
  async exportRoomKey(roomId) {
    const key = this.roomKeys[roomId];
    if (!key) return null;
    return crypto.subtle.exportKey('jwk', key);
  },

  /**
   * Import a JWK room key received from the server
   * @param {string} roomId - Room ID
   * @param {Object} jwk - JWK room key
   */
  async importRoomKey(roomId, jwk) {
    const key = await crypto.subtle.importKey(
      'jwk', jwk,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
    this.roomKeys[roomId] = key;
    console.log(`[E2E] Room key imported for ${roomId}`);
  },

  /**
   * Encrypt plaintext for a room
   * @param {string} plaintext - Text to encrypt
   * @param {string} roomId - Room ID
   * @returns {Promise<string|null>} Base64-encoded ciphertext or null on failure
   */
  async encryptRoom(plaintext, roomId) {
    const key = this.roomKeys[roomId];
    if (!key) {
      console.warn(`[E2E] No room key for ${roomId} - cannot encrypt`);
      return null;
    }
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plaintext);
    const cipherBuf = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
    const combined = new Uint8Array(iv.byteLength + cipherBuf.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(cipherBuf), iv.byteLength);
    return btoa(String.fromCharCode(...combined));
  },

  /**
   * Decrypt a base64(iv + ciphertext) room message
   * @param {string} b64 - Base64-encoded ciphertext
   * @param {string} roomId - Room ID
   * @returns {Promise<string|null>} Decrypted plaintext or null on failure
   */
  async decryptRoom(b64, roomId) {
    const key = this.roomKeys[roomId];
    if (!key) {
      console.warn(`[E2E] No room key for ${roomId} - cannot decrypt`);
      return null;
    }
    try {
      const combined = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const iv = combined.slice(0, 12);
      const cipherBuf = combined.slice(12);
      const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, cipherBuf);
      return new TextDecoder().decode(plainBuf);
    } catch (err) {
      console.error(`[E2E] Room decrypt failed for ${roomId}:`, err);
      return null;
    }
  }
};
