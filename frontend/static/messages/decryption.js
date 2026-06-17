/**
 * messages/decryption.js
 * 
 * Message decryption with retry logic.
 * Handles both DM (ECDH) and room (AES-GCM) decryption.
 */

import { encryption } from '../core/encryption.js';

export const decryption = {
  /**
   * Decrypt a message based on its target
   * @param {Object} msg - Message object with encrypted field
   * @param {string} currentRoom - Current room ID
   * @param {Object} roomKeys - Room keys map
   * @param {string} myDisplay - My display name
   * @returns {Promise<Object>} Decrypted message
   */
  async decryptMessage(msg, currentRoom, roomKeys, myDisplay) {
    if (!msg.encrypted) return msg;

    const isRoomMsg = msg.to && roomKeys[msg.to] !== undefined;
    const isRoomTarget = msg.to && (
      msg.to === currentRoom ||
      roomKeys[msg.to] !== undefined ||
      /^[0-9A-F]{8}$/i.test(msg.to)
    );

    if (isRoomMsg) {
      // Room message with key available
      const plaintext = await encryption.decryptRoom(msg.encrypted, msg.to);
      return { ...msg, text: plaintext !== null ? plaintext : '🔒 [decryption failed]' };
    } else if (isRoomTarget && !isRoomMsg) {
      // Room message but key not yet available - return as-is for buffering
      return msg;
    } else if (msg.to !== 'global') {
      // DM decryption
      const peer = msg.from === myDisplay ? msg.to : msg.from;
      const plaintext = await encryption.decrypt(msg.encrypted, peer);
      return { ...msg, text: plaintext !== null ? plaintext : '🔒 [encrypted - key not available]' };
    }

    return msg;
  },

  /**
   * Check if message can be decrypted now
   * @param {Object} msg - Message object
   * @param {string} currentRoom - Current room ID
   * @param {Object} roomKeys - Room keys map
   * @returns {boolean} True if decryptable
   */
  canDecrypt(msg, currentRoom, roomKeys) {
    if (!msg.encrypted) return true;

    const isRoomMsg = msg.to && roomKeys[msg.to] !== undefined;
    if (isRoomMsg) return true;

    const isRoomTarget = msg.to && (
      msg.to === currentRoom ||
      roomKeys[msg.to] !== undefined ||
      /^[0-9A-F]{8}$/i.test(msg.to)
    );

    if (isRoomTarget && !isRoomMsg) return false; // Need room key

    if (msg.to !== 'global') {
      // DM - need peer key
      return encryption.peerPublicKeys[msg.from] !== undefined;
    }

    return true;
  }
};
