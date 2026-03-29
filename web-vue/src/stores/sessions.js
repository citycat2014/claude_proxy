import { defineStore } from 'pinia'

export const useSessionsStore = defineStore('sessions', {
  state: () => ({
    sessions: [],
    total: 0,
    page: 1,
    perPage: 20,
    totalPages: 0,
    loading: false,
    error: null,
    filters: {
      sessionId: '',
      requestId: '',
      model: '',
      dateFrom: '',
      dateTo: ''
    },
    currentSession: null,
    sessionRequests: [],
    sessionPagination: null
  }),

  getters: {
    hasFilters: (state) => {
      return state.filters.sessionId || state.filters.requestId || state.filters.model ||
             state.filters.dateFrom || state.filters.dateTo
    }
  },

  actions: {
    async fetchSessions(page = 1) {
      this.loading = true
      this.error = null
      this.page = page

      try {
        const params = new URLSearchParams({
          page: page.toString(),
          per_page: this.perPage.toString()
        })

        if (this.filters.sessionId) params.append('session_id', this.filters.sessionId)
        if (this.filters.requestId) params.append('request_id', this.filters.requestId)
        if (this.filters.model) params.append('model', this.filters.model)
        if (this.filters.dateFrom) params.append('date_from', this.filters.dateFrom)
        if (this.filters.dateTo) params.append('date_to', this.filters.dateTo)

        const response = await fetch(`/api/sessions?${params.toString()}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)

        const data = await response.json()
        this.sessions = data.sessions
        this.total = data.total
        this.totalPages = data.total_pages
      } catch (err) {
        this.error = err.message
        console.error('Failed to fetch sessions:', err)
      } finally {
        this.loading = false
      }
    },

    async fetchSessionDetail(sessionId, page = 1, perPage = 20) {
      this.loading = true
      this.error = null

      try {
        const params = new URLSearchParams({
          page: page.toString(),
          per_page: perPage.toString()
        })

        const response = await fetch(`/api/sessions/${sessionId}?${params.toString()}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)

        const data = await response.json()
        this.currentSession = data.session
        this.sessionRequests = data.requests
        this.sessionPagination = data.pagination
      } catch (err) {
        this.error = err.message
        console.error('Failed to fetch session detail:', err)
      } finally {
        this.loading = false
      }
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
      this.fetchSessions(1)
    },

    clearFilters() {
      this.filters = {
        sessionId: '',
        requestId: '',
        model: '',
        dateFrom: '',
        dateTo: ''
      }
      this.fetchSessions(1)
    }
  }
})
