/**
 * core/index.js
 * 
 * Core module exports - provides a clean facade over all core modules.
 */

export { eventBus } from './eventBus.js';
export { encryption } from './encryption.js';
export { config } from './config.js';
export { socketClient } from './socket.js';
export * from './state/index.js';
