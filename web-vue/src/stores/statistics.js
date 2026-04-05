import { defineStore } from 'pinia'

export const useStatisticsStore = defineStore('statistics', {
  state: () => ({
    summary: null,
    loading: false,
    error: null,
    timeFilter: 1 // hours
  }),

  getters: {
    totalRequests: (state) => state.summary?.total_requests || 0,
    totalSessions: (state) => state.summary?.total_sessions || 0,
    totalInputTokens: (state) => state.summary?.total_input_tokens || 0,
    totalOutputTokens: (state) => state.summary?.total_output_tokens || 0,
    cacheCreationTokens: (state) => state.summary?.cache_creation_tokens || 0,
    cacheReadTokens: (state) => state.summary?.cache_read_tokens || 0,
    totalCost: (state) => state.summary?.total_cost || 0,
    avgResponseTime: (state) => state.summary?.avg_response_time_ms || 0,
    requestsToday: (state) => state.summary?.requests_today || 0,
    costToday: (state) => state.summary?.cost_today || 0,
    totalTokens: (state) => (state.summary?.total_input_tokens || 0) + (state.summary?.total_output_tokens || 0)
  },

  actions: {
    async fetchSummary(hours = null, models = []) {
      this.loading = true
      this.error = null
      try {
        const params = new URLSearchParams()
        if (hours !== null && hours !== undefined) params.append('hours', hours.toString())
        if (models && models.length > 0) params.append('models', models.join(','))

        const response = await fetch(`/api/statistics/summary?${params.toString()}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        this.summary = await response.json()
      } catch (err) {
        this.error = err.message
        console.error('Failed to fetch summary:', err)
      } finally {
        this.loading = false
      }
    },

    setTimeFilter(hours) {
      this.timeFilter = hours
      this.fetchSummary(hours)
    }
  }
})
