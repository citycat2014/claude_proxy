import { defineStore } from 'pinia'

export const useChartsStore = defineStore('charts', {
  state: () => ({
    timelineData: [],
    modelDistribution: {},
    loading: false,
    error: null
  }),

  actions: {
    async fetchTimeline(hours = null, days = null) {
      this.loading = true
      this.error = null
      try {
        const params = new URLSearchParams()
        if (hours !== null && hours !== undefined) params.append('hours', hours.toString())
        if (days !== null && days !== undefined) params.append('days', days.toString())

        const response = await fetch(`/api/statistics/timeline?${params.toString()}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        this.timelineData = await response.json()
      } catch (err) {
        this.error = err.message
        console.error('Failed to fetch timeline:', err)
      } finally {
        this.loading = false
      }
    },

    async fetchModelDistribution(hours = null) {
      this.loading = true
      this.error = null
      try {
        const params = hours !== null && hours !== undefined ? `?hours=${hours}` : ''
        const response = await fetch(`/api/statistics/models${params}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        this.modelDistribution = await response.json()
      } catch (err) {
        this.error = err.message
        console.error('Failed to fetch model distribution:', err)
      } finally {
        this.loading = false
      }
    }
  }
})
