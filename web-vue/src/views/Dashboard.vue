<template>
  <div>
    <!-- Time Filter Bar -->
    <div class="filter-bar" style="margin-bottom: 20px; padding: 12px 16px; background: var(--bg-secondary); border-radius: var(--radius); border: 1px solid var(--border-color); display: flex; align-items: center; gap: 16px;">
      <span style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">Time Range:</span>
      <select
        v-model="timeFilter"
        @change="onTimeFilterChange"
        style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary); font-size: 13px; min-width: 150px; cursor: pointer;"
      >
        <option :value="0.5">Last 30 Minutes</option>
        <option :value="1">Last 1 Hour</option>
        <option :value="5">Last 5 Hours</option>
        <option :value="24">Last 24 Hours</option>
        <option :value="168">Last 7 Days</option>
        <option :value="720">Last 30 Days</option>
        <option :value="null">All Time</option>
      </select>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Requests</span>
          <div class="stat-icon primary">
            <i class="bi bi-chat-dots"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(stats.totalRequests) }}</div>
        <div class="stat-subtitle">Today: {{ formatNumber(stats.requestsToday) }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Sessions</span>
          <div class="stat-icon success">
            <i class="bi bi-collection"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(stats.totalSessions) }}</div>
        <div class="stat-subtitle">Unique sessions</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Tokens</span>
          <div class="stat-icon info">
            <i class="bi bi-cpu"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(stats.totalTokens) }}</div>
        <div class="stat-subtitle">
          Input: {{ formatNumber(stats.totalInputTokens) }} / Output: {{ formatNumber(stats.totalOutputTokens) }}
        </div>
        <div class="stat-subtitle" style="margin-top: 4px; font-size: 11px; color: var(--text-muted);">
          <i class="bi bi-lightning-charge"></i> Cache Read: {{ formatNumber(stats.cacheReadTokens) }} |
          <i class="bi bi-database"></i> Cache Write: {{ formatNumber(stats.cacheCreationTokens) }}
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Cost</span>
          <div class="stat-icon warning">
            <i class="bi bi-currency-dollar"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatCost(stats.totalCost) }}</div>
        <div class="stat-subtitle">Today: {{ formatCost(stats.costToday) }}</div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-grid">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-graph-up"></i>
            Request Volume
          </h3>
          <span class="text-muted" style="font-size: 12px;">{{ chartSubtitle }}</span>
        </div>
        <div class="card-body">
          <canvas ref="requestsChart" height="200"></canvas>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-pie-chart"></i>
            Model Distribution
          </h3>
        </div>
        <div class="card-body">
          <canvas ref="modelsChart" height="200"></canvas>
        </div>
      </div>
    </div>

    <!-- Timing Analysis Row -->
    <div class="charts-grid" style="margin-top: 20px;">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-stopwatch"></i>
            Response Time Breakdown
          </h3>
          <span class="text-muted" style="font-size: 12px;">Average phase timing (ms)</span>
        </div>
        <div class="card-body">
          <canvas ref="timingChart" height="200"></canvas>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-speedometer2"></i>
            Latency Percentiles
            <i class="bi bi-question-circle" style="font-size: 14px; margin-left: 8px; color: var(--text-muted); cursor: help;"
               title="Percentiles show the distribution of response times. P50 means half of requests are faster. P95 means 95% of requests are faster (only 5% slower). P99 captures outliers."></i>
          </h3>
        </div>
        <div class="card-body">
          <div class="latency-stats">
            <div class="latency-item" title="P50 (Median): 50% of requests are faster than this value. Half of all requests complete within this time.">
              <div class="latency-label">P50 (Median)</div>
              <div class="latency-value">{{ formatNumber(timingStats.p50_ms) }} ms</div>
            </div>
            <div class="latency-item" title="P95: 95% of requests are faster than this value. Only 5% of requests are slower.">
              <div class="latency-label">P95</div>
              <div class="latency-value">{{ formatNumber(timingStats.p95_ms) }} ms</div>
            </div>
            <div class="latency-item" title="P99: 99% of requests are faster than this value. Only 1% of requests (outliers) are slower.">
              <div class="latency-label">P99</div>
              <div class="latency-value">{{ formatNumber(timingStats.p99_ms) }} ms</div>
            </div>
            <div class="latency-item" title="Average: Sum of all response times divided by number of requests. Can be skewed by outliers.">
              <div class="latency-label">Average</div>
              <div class="latency-value">{{ formatNumber(timingStats.avg_ms) }} ms</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Row -->
    <div class="section-grid section-grid-2">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-tools"></i>
            Top Tools
          </h3>
        </div>
        <div class="card-body">
          <canvas ref="toolsChart" height="150"></canvas>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-lightning-charge"></i>
            Streaming Latency
            <i class="bi bi-question-circle" style="font-size: 14px; margin-left: 8px; color: var(--text-muted); cursor: help;"
               title="Streaming metrics measure the real-time response characteristics. Lower times indicate faster, more responsive streaming."></i>
          </h3>
        </div>
        <div class="card-body">
          <div class="streaming-stats">
            <div class="streaming-item" title="Time from sending request to receiving the first token in the streaming response. Includes network latency + server processing time.">
              <div class="streaming-label">Time to First Token</div>
              <div class="streaming-value">{{ formatNumber(streamingStats.avg_time_to_first_token_ms) }} ms</div>
            </div>
            <div class="streaming-item" title="Average time between consecutive tokens in the streaming response. Lower is better for smooth streaming.">
              <div class="streaming-label">Avg Token Latency</div>
              <div class="streaming-value">{{ formatNumber(streamingStats.avg_token_latency_ms) }} ms</div>
            </div>
            <div class="streaming-item" title="Time To First Byte (TTFB): Server processing time from receiving the request to sending the first byte of response. Pure server-side latency.">
              <div class="streaming-label">Server Processing (TTFB)</div>
              <div class="streaming-value">{{ formatNumber(timingBreakdown.avg_wait_ms) }} ms</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import Chart from 'chart.js/auto'
import { useStatisticsStore } from '@/stores/statistics'
import { useChartsStore } from '@/stores/charts'
import { useSessionsStore } from '@/stores/sessions'
import { formatNumber, formatCost, formatDateTime } from '@/utils/formatters'

const statsStore = useStatisticsStore()
const chartsStore = useChartsStore()
const sessionsStore = useSessionsStore()

const timeFilter = ref(statsStore.timeFilter)
const requestsChart = ref(null)
const modelsChart = ref(null)
const toolsChart = ref(null)
const timingChart = ref(null)

let requestsChartInstance = null
let modelsChartInstance = null
let toolsChartInstance = null
let timingChartInstance = null
let lastTimeFilter = null

const stats = computed(() => statsStore)
const toolStats = ref([])
const timingStats = ref({ avg_ms: 0, p50_ms: 0, p95_ms: 0, p99_ms: 0 })
const timingBreakdown = ref({
  avg_connect_ms: 0,
  avg_tls_ms: 0,
  avg_send_ms: 0,
  avg_wait_ms: 0,
  avg_receive_ms: 0
})
const streamingStats = ref({
  avg_time_to_first_token_ms: 0,
  avg_token_latency_ms: 0
})
const recentSessions = ref([])

const chartSubtitle = computed(() => {
  if (timeFilter.value === 720) return 'Last 30 days'
  if (timeFilter.value === 168) return 'Last 7 days'
  if (timeFilter.value === 24) return 'Last 24 hours'
  if (timeFilter.value === 5) return 'Last 5 hours'
  if (timeFilter.value === 1) return 'Last 1 hour'
  if (timeFilter.value === 0.5) return 'Last 30 minutes'
  return 'Last 7 days'
})

function onTimeFilterChange() {
  statsStore.setTimeFilter(timeFilter.value)
  loadDashboardData()
}

async function loadDashboardData() {
  // Load summary
  await statsStore.fetchSummary(timeFilter.value)

  // Load timeline based on time filter
  if (timeFilter.value === 720) {
    // 30 days
    await chartsStore.fetchTimeline(null, 30)
  } else if (timeFilter.value === 168) {
    // 7 days
    await chartsStore.fetchTimeline(null, 7)
  } else if (timeFilter.value) {
    // Hours-based filter
    await chartsStore.fetchTimeline(timeFilter.value, null)
  } else {
    // All Time - default to 7 days
    await chartsStore.fetchTimeline(null, 7)
  }
  updateRequestsChart()

  // Load model distribution
  await chartsStore.fetchModelDistribution(timeFilter.value)
  updateModelsChart()

  // Load tool stats
  try {
    const response = await fetch(`/api/statistics/tools?hours=${timeFilter.value || ''}`)
    if (response.ok) {
      toolStats.value = await response.json()
      updateToolsChart()
    }
  } catch (err) {
    console.error('Failed to load tool stats:', err)
  }

  // Load recent sessions
  await sessionsStore.fetchSessions(1)
  recentSessions.value = sessionsStore.sessions.slice(0, 5)

  // Load timing statistics
  await loadTimingData()
}

async function loadTimingData() {
  try {
    // Load latency stats
    const latencyResponse = await fetch(`/api/statistics/latency?hours=${timeFilter.value || ''}`)
    if (latencyResponse.ok) {
      timingStats.value = await latencyResponse.json()
    }

    // Load timing breakdown
    const timingResponse = await fetch(`/api/statistics/timing?hours=${timeFilter.value || ''}`)
    if (timingResponse.ok) {
      const timing = await timingResponse.json()
      timingBreakdown.value = timing.overall || {}
    }

    // Load streaming stats
    const streamingResponse = await fetch(`/api/statistics/streaming?hours=${timeFilter.value || ''}`)
    if (streamingResponse.ok) {
      streamingStats.value = await streamingResponse.json()
    }

    updateTimingChart()
  } catch (err) {
    console.error('Failed to load timing data:', err)
  }
}

function updateRequestsChart() {
  if (!requestsChart.value) return

  const isMinuteLevel = timeFilter.value && timeFilter.value <= 1
  const isHourLevel = timeFilter.value && timeFilter.value > 1 && timeFilter.value <= 24
  const wasMinuteLevel = lastTimeFilter && lastTimeFilter <= 1
  const wasHourLevel = lastTimeFilter && lastTimeFilter > 1 && lastTimeFilter <= 24

  // Check if granularity changed - need to recreate chart
  const granularityChanged = (isMinuteLevel !== wasMinuteLevel) || (isHourLevel !== wasHourLevel)

  const labels = chartsStore.timelineData.map(d => {
    const date = new Date(d.date || d.timestamp || d.hour)
    if (isMinuteLevel) {
      // Minute granularity: show "HH:MM"
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
    } else if (isHourLevel) {
      // Hour granularity: show "HH:00"
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
    } else {
      // Day granularity: show "MMM DD"
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  })
  const data = chartsStore.timelineData.map(d => d.count || d.requests || 0)

  if (requestsChartInstance && !granularityChanged) {
    // Update existing chart data
    requestsChartInstance.data.labels = labels
    requestsChartInstance.data.datasets[0].data = data
    requestsChartInstance.update('none') // Update without animation
  } else {
    // Destroy old chart if exists
    if (requestsChartInstance) {
      requestsChartInstance.destroy()
    }
    // Create new chart
    requestsChartInstance = new Chart(requestsChart.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Requests',
          data,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          borderWidth: 2,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#e2e8f0' }
          },
          x: {
            grid: { display: false },
            ticks: {
              maxTicksLimit: isMinuteLevel ? 6 : (isHourLevel ? 8 : 7),
              maxRotation: isMinuteLevel ? 45 : 0
            }
          }
        }
      }
    })
  }

  lastTimeFilter = timeFilter.value
}

function updateModelsChart() {
  if (!modelsChart.value) return

  const entries = Object.entries(chartsStore.modelDistribution)
  if (entries.length === 0) return

  const labels = entries.map(([model]) => model)
  const data = entries.map(([, count]) => count)

  if (modelsChartInstance) {
    modelsChartInstance.destroy()
  }

  modelsChartInstance = new Chart(modelsChart.value, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#3b82f6', '#ef4444'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 15, usePointStyle: true }
        }
      }
    }
  })
}

function updateToolsChart() {
  if (!toolsChart.value || toolStats.value.length === 0) return

  const labels = toolStats.value.slice(0, 5).map(t => t.name)
  const data = toolStats.value.slice(0, 5).map(t => t.calls)

  if (toolsChartInstance) {
    toolsChartInstance.destroy()
  }

  toolsChartInstance = new Chart(toolsChart.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Calls',
        data,
        backgroundColor: '#6366f1',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#e2e8f0' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  })
}

function updateTimingChart() {
  if (!timingChart.value) return

  const labels = ['Connect', 'TLS', 'Send', 'Wait', 'Receive']
  const data = [
    timingBreakdown.value.avg_connect_ms || 0,
    timingBreakdown.value.avg_tls_ms || 0,
    timingBreakdown.value.avg_send_ms || 0,
    timingBreakdown.value.avg_wait_ms || 0,
    timingBreakdown.value.avg_receive_ms || 0
  ]

  if (timingChartInstance) {
    timingChartInstance.destroy()
  }

  timingChartInstance = new Chart(timingChart.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Time (ms)',
        data,
        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#e2e8f0' },
          title: {
            display: true,
            text: 'Milliseconds'
          }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  })
}

onMounted(() => {
  loadDashboardData()
})

watch(() => chartsStore.timelineData, updateRequestsChart)
watch(() => chartsStore.modelDistribution, updateModelsChart)
watch(() => toolStats.value, updateToolsChart)
watch(() => timeFilter.value, loadTimingData)
</script>

<style scoped>
.latency-stats, .streaming-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.latency-item, .streaming-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius);
  cursor: help;
  transition: background 0.2s;
}

.latency-item:hover, .streaming-item:hover {
  background: var(--bg-hover, #e2e8f0);
}

.latency-label, .streaming-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.latency-value, .streaming-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
