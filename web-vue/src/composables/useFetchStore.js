import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Factory function to create a store with common fetch patterns.
 *
 * @param {string} name - Store name
 * @param {object} options - Store configuration
 * @param {function} options.fetchData - Async function to fetch data
 * @param {object} options.initialState - Initial state (optional)
 * @returns {StoreDefinition} Pinia store
 *
 * @example
 * export const useMyStore = createFetchStore('myStore', {
 *   fetchData: async (params) => {
 *     const response = await fetch(`/api/data?${new URLSearchParams(params)}`)
 *     return response.json()
 *   },
 *   initialState: { items: [] }
 * })
 */
export function createFetchStore(name, options) {
  const { fetchData, initialState = {} } = options

  return defineStore(name, {
    state: () => ({
      data: null,
      loading: false,
      error: null,
      ...initialState
    }),

    actions: {
      async fetch(params = {}) {
        this.loading = true
        this.error = null
        try {
          this.data = await fetchData(params)
          return this.data
        } catch (err) {
          this.error = err.message
          console.error(`Failed to fetch ${name}:`, err)
          throw err
        } finally {
          this.loading = false
        }
      },

      clearError() {
        this.error = null
      },

      reset() {
        this.data = null
        this.loading = false
        this.error = null
      }
    }
  })
}

/**
 * Composable for simple API fetching with loading/error state.
 *
 * @param {string} endpoint - API endpoint (relative)
 * @returns {object} Fetch utilities
 *
 * @example
 * const { data, loading, error, fetch } = useFetch('/api/sessions')
 */
export function useFetch(endpoint) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetch(params = {}) {
    loading.value = true
    error.value = null
    try {
      const queryString = params ? `?${new URLSearchParams(params)}` : ''
      const response = await fetch(`${endpoint}${queryString}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      data.value = await response.json()
      return data.value
    } catch (err) {
      error.value = err.message
      console.error(`Failed to fetch ${endpoint}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, fetch }
}
