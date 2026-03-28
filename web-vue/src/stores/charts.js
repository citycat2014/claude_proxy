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
      try {
        const params = new URLSearchParams()
        if (hours) params.append('hours', hours.toString())
        if (days) params.append('days', days.toString())

        const response = await fetch(`/api/statistics/timeline?${params.toString()}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        this.timelineData = await response.json()
      } catch (err) {
        console.error('Failed to fetch timeline:', err)
      }
    },

    async fetchModelDistribution(hours = null) {
      try {
        const params = hours ? `?hours=${hours}` : ''
        const response = await fetch(`/api/statistics/models${params}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        this.modelDistribution = await response.json()
      } catch (err) {
        console.error('Failed to fetch model distribution:', err)
      }
    }
  }
})
