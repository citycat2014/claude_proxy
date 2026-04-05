/**
 * SocketIO store for real-time updates.
 *
 * Manages WebSocket connection to Flask-SocketIO server
 * and handles real-time events for new requests and statistics updates.
 */

import { defineStore } from 'pinia'
import { io } from 'socket.io-client'

const SOCKET_URL = window.location.origin

export const useSocketStore = defineStore('socket', {
  state: () => ({
    connected: false,
    socket: null,
    newRequestListener: null,
    statsUpdateListener: null,
  }),

  getters: {
    isConnected: (state) => state.connected,
  },

  actions: {
    /**
     * Connect to the WebSocket server.
     */
    connect() {
      if (this.socket && this.socket.connected) {
        console.log('[SocketIO] Already connected')
        return
      }

      console.log('[SocketIO] Connecting to', SOCKET_URL)

      this.socket = io(SOCKET_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10,
      })

      this.socket.on('connect', () => {
        console.log('[SocketIO] Connected')
        this.connected = true

        // Subscribe to channels
        this.socket.emit('subscribe', { channels: ['requests', 'stats'] })
      })

      this.socket.on('disconnect', () => {
        console.log('[SocketIO] Disconnected')
        this.connected = false
      })

      this.socket.on('connected', (data) => {
        console.log('[SocketIO] Server confirmation:', data.message)
      })

      this.socket.on('new_request', (data) => {
        console.log('[SocketIO] New request captured:', data)
        if (this.newRequestListener) {
          this.newRequestListener(data)
        }
      })

      this.socket.on('stats_update', (data) => {
        console.log('[SocketIO] Stats update:', data)
        if (this.statsUpdateListener) {
          this.statsUpdateListener(data)
        }
      })

      this.socket.on('connect_error', (error) => {
        console.error('[SocketIO] Connection error:', error.message)
      })
    },

    /**
     * Disconnect from the WebSocket server.
     */
    disconnect() {
      if (this.socket) {
        this.socket.disconnect()
        this.socket = null
        this.connected = false
        console.log('[SocketIO] Disconnected by client')
      }
    },

    /**
     * Set callback for new request events.
     * @param {Function} listener - Callback function receiving request data
     */
    onNewRequest(listener) {
      this.newRequestListener = listener
    },

    /**
     * Set callback for statistics update events.
     * @param {Function} listener - Callback function receiving stats data
     */
    onStatsUpdate(listener) {
      this.statsUpdateListener = listener
    },

    /**
     * Clear all listeners.
     */
    clearListeners() {
      this.newRequestListener = null
      this.statsUpdateListener = null
    },
  },
})
