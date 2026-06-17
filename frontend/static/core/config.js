/**
 * core/config.js
 * 
 * Client-side configuration.
 * Fetches ICE config from server and provides fallback STUN servers.
 */

export const config = {
  iceConfig: null,

  /**
   * Fetch ICE configuration from server
   * @param {string} sid - Socket session ID for authentication
   * @returns {Promise<Object>} ICE configuration
   */
  async getIceConfig(sid = '') {
    if (this.iceConfig) return this.iceConfig;
    
    try {
      const res = await fetch('/ice-config?sid=' + encodeURIComponent(sid));
      if (res.ok) {
        this.iceConfig = await res.json();
        console.log('[ICE] Config loaded from server, servers:', this.iceConfig.iceServers.length);
        return this.iceConfig;
      } else {
        throw new Error('HTTP ' + res.status);
      }
    } catch (err) {
      console.warn('[ICE] Could not fetch config, using STUN-only fallback:', err.message);
      this.iceConfig = {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' },
        ],
        iceCandidatePoolSize: 10,
        bundlePolicy: 'max-bundle',
        rtcpMuxPolicy: 'require',
      };
      return this.iceConfig;
    }
  },

  /**
   * Check if TURN server is available in ICE config
   * @returns {boolean} True if TURN is configured
   */
  hasTURN() {
    const servers = this.iceConfig && this.iceConfig.iceServers;
    if (!servers || servers.length === 0) return false;
    return servers.some(s => {
      const urls = s.urls;
      if (!urls) return false;
      if (typeof urls === 'string') return urls.startsWith('turn:');
      return urls.some(u => u.startsWith('turn:'));
    });
  }
};
