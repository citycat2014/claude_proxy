<template>
  <div>
    <!-- Filter Bar -->
    <div class="filter-bar" style="margin-bottom: 20px; padding: 12px 16px; background: var(--bg-secondary); border-radius: var(--radius); border: 1px solid var(--border-color); display: flex; align-items: center; gap: 24px;">
      <!-- Time Filter -->
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">{{ $t('dashboard.timeRange') }}:</span>
        <select
          v-model="timeFilter"
          @change="onTimeFilterChange"
          style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary); font-size: 13px; min-width: 150px; cursor: pointer;"
        >
          <option :value="0.5">{{ $t('dashboard.timeRangeOptions.last30Minutes') }}</option>
          <option :value="1">{{ $t('dashboard.timeRangeOptions.last1Hour') }}</option>
          <option :value="5">{{ $t('dashboard.timeRangeOptions.last5Hours') }}</option>
          <option :value="24">{{ $t('dashboard.timeRangeOptions.last24Hours') }}</option>
          <option :value="168">{{ $t('dashboard.timeRangeOptions.last7Days') }}</option>
          <option :value="720">{{ $t('dashboard.timeRangeOptions.last30Days') }}</option>
          <option :value="null">{{ $t('dashboard.timeRangeOptions.allTime') }}</option>
        </select>
      </div>

      <!-- Model Filter -->
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">{{ $t('dashboard.model') }}:</span>
        <div class="model-filter-wrapper" style="position: relative;">
          <div
            class="model-filter-trigger"
            :class="{ active: isModelDropdownOpen }"
            @click="toggleModelDropdown"
            style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary); font-size: 13px; min-width: 180px; cursor: pointer; display: flex; align-items: center; justify-content: space-between;"
          >
            <span>{{ modelFilterText }}</span>
            <i class="bi bi-chevron-down" :style="{ transform: isModelDropdownOpen ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }"></i>
          </div>

          <!-- Model Dropdown -->
          <div
            v-if="isModelDropdownOpen"
            class="model-dropdown"
            style="position: absolute; top: calc(100% + 4px); left: 0; min-width: 260px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius); box-shadow: 0 10px 40px rgba(0,0,0,0.15); z-index: 100;"
          >
            <!-- Search -->
            <div style="padding: 12px; border-bottom: 1px solid var(--border-color);">
              <input
                v-model="modelSearchQuery"
                type="text"
                :placeholder="$t('dashboard.modelFilter.searchModels')"
                style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 13px;"
                @click.stop
              >
            </div>

            <!-- Actions -->
            <div style="display: flex; padding: 8px 12px; gap: 8px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary);">
              <button
                class="action-btn"
                @click="selectAllModels"
                style="padding: 4px 10px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-primary); font-size: 11px; color: var(--text-secondary); cursor: pointer;"
              >{{ $t('dashboard.modelFilter.selectAll') }}</button>
              <button
                class="action-btn"
                @click="clearModelSelection"
                style="padding: 4px 10px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-primary); font-size: 11px; color: var(--text-secondary); cursor: pointer;"
              >{{ $t('dashboard.modelFilter.clear') }}</button>
            </div>

            <!-- Model List -->
            <div style="max-height: 200px; overflow-y: auto; padding: 4px 0;">
              <div
                v-for="model in filteredModels"
                :key="model"
                class="model-item"
                :class="{ selected: selectedModels.includes(model) }"
                @click="toggleModel(model)"
                style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; transition: background 0.15s;"
                :style="{ background: selectedModels.includes(model) ? 'rgba(99, 102, 241, 0.08)' : 'transparent' }"
              >
                <div
                  class="checkbox"
                  :style="{
                    width: '16px',
                    height: '16px',
                    border: '2px solid var(--border-color)',
                    borderRadius: '3px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: selectedModels.includes(model) ? 'var(--primary)' : 'transparent',
                    borderColor: selectedModels.includes(model) ? 'var(--primary)' : 'var(--border-color)'
                  }"
                >
                  <i v-if="selectedModels.includes(model)" class="bi bi-check" style="color: white; font-size: 10px;"></i>
                </div>
                <span style="font-size: 13px; color: var(--text-primary);">{{ model }}</span>
              </div>
            </div>

            <!-- Footer -->
            <div style="padding: 8px 12px; border-top: 1px solid var(--border-color); background: var(--bg-secondary); font-size: 11px; color: var(--text-secondary); text-align: center;">
              {{ $t('dashboard.modelFilter.modelsAvailable', { count: availableModels.length }) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('dashboard.stats.totalRequests') }}</span>
          <div class="stat-icon primary">
            <i class="bi bi-chat-dots"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(stats.totalRequests) }}</div>
        <div class="stat-subtitle">{{ $t('dashboard.stats.today', { count: formatNumber(stats.requestsToday) }) }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('dashboard.stats.sessions') }}</span>
          <div class="stat-icon success">
            <i class="bi bi-collection"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(stats.totalSessions) }}</div>
        <div class="stat-subtitle">{{ $t('dashboard.stats.uniqueSessions') }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('dashboard.stats.totalTokens') }}</span>
          <div class="stat-icon info">
            <i class="bi bi-cpu"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(stats.totalTokens) }}</div>
        <div class="stat-subtitle">
          {{ $t('dashboard.stats.inputOutput', { input: formatNumber(stats.totalInputTokens), output: formatNumber(stats.totalOutputTokens) }) }}
        </div>
        <div class="stat-subtitle" style="margin-top: 4px; font-size: 11px; color: var(--text-muted);">
          <i class="bi bi-lightning-charge"></i> {{ $t('dashboard.stats.cacheRead', { count: formatNumber(stats.cacheReadTokens) }) }} |
          <i class="bi bi-database"></i> {{ $t('dashboard.stats.cacheWrite', { count: formatNumber(stats.cacheCreationTokens) }) }}
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('dashboard.stats.totalCost') }}</span>
          <div class="stat-icon warning">
            <i class="bi bi-currency-dollar"></i>
          </div>
        </div>
        <div class="stat-value">{{ formatCost(stats.totalCost) }}</div>
        <div class="stat-subtitle">{{ $t('dashboard.stats.today', { count: formatCost(stats.costToday) }) }}</div>
      </div>

      <!-- Success Rate Card -->
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('dashboard.stats.apiSuccessRate') }}</span>
          <div class="stat-icon" :class="successRateClass">
            <i class="bi" :class="successRateIcon"></i>
          </div>
        </div>
        <div class="stat-value" :style="{ color: successRateColor }">{{ successRateStats.success_rate }}%</div>
        <div class="stat-subtitle">
          {{ $t('dashboard.stats.successful', { successful: formatNumber(successRateStats.successful_requests), total: formatNumber(successRateStats.total_requests) }) }}
        </div>
        <div class="stat-subtitle" style="margin-top: 4px; font-size: 11px; color: var(--text-muted);">
          <span v-if="successRateStats.breakdown" :title="$t('dashboard.tooltips.percentiles')">
            <span style="color: var(--success)">{{ $t('dashboard.stats.status2xx', { count: successRateStats.breakdown['2xx'] || 0 }) }}</span> |
            <span style="color: var(--warning)">{{ $t('dashboard.stats.status4xx', { count: successRateStats.breakdown['4xx'] || 0 }) }}</span> |
            <span style="color: var(--danger)">{{ $t('dashboard.stats.status5xx', { count: successRateStats.breakdown['5xx'] || 0 }) }}</span>
          </span>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-grid">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-graph-up"></i>
            {{ $t('dashboard.charts.requestVolume') }}
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
            {{ $t('dashboard.charts.modelDistribution') }}
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
            {{ $t('dashboard.charts.responseTimeBreakdown') }}
          </h3>
          <span class="text-muted" style="font-size: 12px;">{{ $t('dashboard.charts.avgPhaseTiming') }}</span>
        </div>
        <div class="card-body">
          <canvas ref="timingChart" height="200"></canvas>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-speedometer2"></i>
            {{ $t('dashboard.charts.latencyPercentiles') }}
            <i class="bi bi-question-circle" style="font-size: 14px; margin-left: 8px; color: var(--text-muted); cursor: help;"
               :title="$t('dashboard.tooltips.percentiles')"></i>
          </h3>
        </div>
        <div class="card-body">
          <div class="latency-stats">
            <div class="latency-item" :title="$t('dashboard.tooltips.p50')">
              <div class="latency-label">{{ $t('dashboard.charts.p50Median') }}</div>
              <div class="latency-value">{{ formatNumber(timingStats.p50_ms) }} ms</div>
            </div>
            <div class="latency-item" :title="$t('dashboard.tooltips.p95')">
              <div class="latency-label">{{ $t('dashboard.charts.p95') }}</div>
              <div class="latency-value">{{ formatNumber(timingStats.p95_ms) }} ms</div>
            </div>
            <div class="latency-item" :title="$t('dashboard.tooltips.p99')">
              <div class="latency-label">{{ $t('dashboard.charts.p99') }}</div>
              <div class="latency-value">{{ formatNumber(timingStats.p99_ms) }} ms</div>
            </div>
            <div class="latency-item" :title="$t('dashboard.tooltips.average')">
              <div class="latency-label">{{ $t('dashboard.charts.average') }}</div>
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
            {{ $t('dashboard.charts.topTools') }}
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
            {{ $t('dashboard.charts.streamingLatency') }}
            <i class="bi bi-question-circle" style="font-size: 14px; margin-left: 8px; color: var(--text-muted); cursor: help;"
               :title="$t('dashboard.tooltips.streaming')"></i>
          </h3>
        </div>
        <div class="card-body">
          <div class="streaming-stats">
            <div class="streaming-item" :title="$t('dashboard.tooltips.firstToken')">
              <div class="streaming-label">{{ $t('dashboard.charts.timeToFirstToken') }}</div>
              <div class="streaming-value">{{ formatNumber(streamingStats.avg_time_to_first_token_ms) }} ms</div>
            </div>
            <div class="streaming-item" :title="$t('dashboard.tooltips.tokenLatency')">
              <div class="streaming-label">{{ $t('dashboard.charts.avgTokenLatency') }}</div>
              <div class="streaming-value">{{ formatNumber(streamingStats.avg_token_latency_ms) }} ms</div>
            </div>
            <div class="streaming-item" :title="$t('dashboard.tooltips.ttfb')">
              <div class="streaming-label">{{ $t('dashboard.charts.serverProcessing') }}</div>
              <div class="streaming-value">{{ formatNumber(timingBreakdown.avg_wait_ms) }} ms</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Chart from 'chart.js/auto'
import { useStatisticsStore } from '@/stores/statistics'
import { useChartsStore } from '@/stores/charts'
import { useSessionsStore } from '@/stores/sessions'
import { useSocketStore } from '@/stores/socket'
import { formatNumber, formatCost, formatDateTime } from '@/utils/formatters'

const { t, n } = useI18n()

const statsStore = useStatisticsStore()
const chartsStore = useChartsStore()
const sessionsStore = useSessionsStore()
const socketStore = useSocketStore()

const timeFilter = ref(statsStore.timeFilter)
const requestsChart = ref(null)
const modelsChart = ref(null)
const toolsChart = ref(null)
const timingChart = ref(null)

// Model filter state
const isModelDropdownOpen = ref(false)
const modelSearchQuery = ref('')

let requestsChartInstance = null
let modelsChartInstance = null
let toolsChartInstance = null
let timingChartInstance = null
let lastTimeFilter = null

const stats = computed(() => statsStore)
const availableModels = computed(() => chartsStore.availableModels)
const selectedModels = computed({
  get: () => chartsStore.selectedModels,
  set: (value) => chartsStore.setSelectedModels(value)
})

const filteredModels = computed(() => {
  if (!modelSearchQuery.value) return availableModels.value
  const query = modelSearchQuery.value.toLowerCase()
  return availableModels.value.filter(model => model.toLowerCase().includes(query))
})

const modelFilterText = computed(() => {
  if (selectedModels.value.length === 0) return t('dashboard.modelFilter.allModels')
  if (selectedModels.value.length === 1) return selectedModels.value[0]
  return t('dashboard.modelFilter.modelsSelected', { count: selectedModels.value.length })
})
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
const successRateStats = ref({
  total_requests: 0,
  successful_requests: 0,
  failed_requests: 0,
  success_rate: 0,
  breakdown: { '2xx': 0, '4xx': 0, '5xx': 0 }
})

const successRateClass = computed(() => {
  const rate = successRateStats.value.success_rate || 0
  if (rate >= 95) return 'success'
  if (rate >= 80) return 'warning'
  return 'danger'
})

const successRateIcon = computed(() => {
  const rate = successRateStats.value.success_rate || 0
  if (rate >= 95) return 'bi-check-circle-fill'
  if (rate >= 80) return 'bi-exclamation-circle-fill'
  return 'bi-x-circle-fill'
})

const successRateColor = computed(() => {
  const rate = successRateStats.value.success_rate || 0
  if (rate >= 95) return 'var(--success)'
  if (rate >= 80) return 'var(--warning)'
  return 'var(--danger)'
})

const chartSubtitle = computed(() => {
  if (timeFilter.value === 720) return t('dashboard.timeRangeOptions.last30Days')
  if (timeFilter.value === 168) return t('dashboard.timeRangeOptions.last7Days')
  if (timeFilter.value === 24) return t('dashboard.timeRangeOptions.last24Hours')
  if (timeFilter.value === 5) return t('dashboard.timeRangeOptions.last5Hours')
  if (timeFilter.value === 1) return t('dashboard.timeRangeOptions.last1Hour')
  if (timeFilter.value === 0.5) return t('dashboard.timeRangeOptions.last30Minutes')
  return t('dashboard.timeRangeOptions.last7Days')
})

function onTimeFilterChange() {
  statsStore.setTimeFilter(timeFilter.value)
  loadDashboardData()
}

// Model filter functions
function toggleModelDropdown() {
  isModelDropdownOpen.value = !isModelDropdownOpen.value
}

function toggleModel(model) {
  const index = selectedModels.value.indexOf(model)
  if (index > -1) {
    selectedModels.value = selectedModels.value.filter(m => m !== model)
  } else {
    selectedModels.value = [...selectedModels.value, model]
  }
  // Reload data with model filter
  loadDashboardData()
}

function selectAllModels() {
  selectedModels.value = [...availableModels.value]
  loadDashboardData()
}

function clearModelSelection() {
  selectedModels.value = []
  loadDashboardData()
}

// Close dropdown when clicking outside
function handleClickOutside(event) {
  const dropdown = document.querySelector('.model-filter-wrapper')
  if (dropdown && !dropdown.contains(event.target)) {
    isModelDropdownOpen.value = false
  }
}

async function loadDashboardData() {
  // Build model filter parameter
  const modelParam = selectedModels.value.length > 0
    ? `&models=${selectedModels.value.join(',')}`
    : ''

  // Load summary with model filter
  await statsStore.fetchSummary(timeFilter.value, selectedModels.value)

  // Load timeline based on time filter with model filter
  if (timeFilter.value === 720) {
    await chartsStore.fetchTimeline(null, 30, selectedModels.value)
  } else if (timeFilter.value === 168) {
    await chartsStore.fetchTimeline(null, 7, selectedModels.value)
  } else if (timeFilter.value) {
    await chartsStore.fetchTimeline(timeFilter.value, null, selectedModels.value)
  } else {
    await chartsStore.fetchTimeline(null, 7, selectedModels.value)
  }
  updateRequestsChart()

  // Load model distribution
  await chartsStore.fetchModelDistribution(timeFilter.value)
  updateModelsChart()

  // Load tool stats with model filter
  try {
    const response = await fetch(`/api/statistics/tools?hours=${timeFilter.value || ''}${modelParam}`)
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

  // Load timing statistics with model filter
  await loadTimingData()

  // Load success rate statistics with model filter
  await loadSuccessRateData()
}

async function loadSuccessRateData() {
  try {
    const modelParam = selectedModels.value.length > 0
      ? `&models=${selectedModels.value.join(',')}`
      : ''
    const response = await fetch(`/api/statistics/success-rate?hours=${timeFilter.value || ''}${modelParam}`)
    if (response.ok) {
      successRateStats.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load success rate data:', err)
  }
}

async function loadTimingData() {
  try {
    const modelParam = selectedModels.value.length > 0
      ? `&models=${selectedModels.value.join(',')}`
      : ''

    // Load latency stats
    const latencyResponse = await fetch(`/api/statistics/latency?hours=${timeFilter.value || ''}${modelParam}`)
    if (latencyResponse.ok) {
      timingStats.value = await latencyResponse.json()
    }

    // Load timing breakdown
    const timingResponse = await fetch(`/api/statistics/timing?hours=${timeFilter.value || ''}${modelParam}`)
    if (timingResponse.ok) {
      const timing = await timingResponse.json()
      timingBreakdown.value = timing.overall || {}
    }

    // Load streaming stats
    const streamingResponse = await fetch(`/api/statistics/streaming?hours=${timeFilter.value || ''}${modelParam}`)
    if (streamingResponse.ok) {
      streamingStats.value = await streamingResponse.json()
    }

    updateTimingChart()
  } catch (err) {
    console.error('Failed to load timing data:', err)
  }
}

/**
 * Handle real-time new request event.
 * Refreshes dashboard data when new requests are captured.
 */
async function handleNewRequest(requestData) {
  console.log('[Dashboard] New request captured, refreshing data...', requestData)
  // Refresh dashboard data
  await loadDashboardData()
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
          label: t('dashboard.stats.totalRequests'),
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
        label: t('dashboard.charts.calls'),
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

  const labels = [
    t('Connect'),
    t('TLS'),
    t('Send'),
    t('Wait'),
    t('Receive')
  ]
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
        label: t('dashboard.charts.avgPhaseTiming'),
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
            text: t('dashboard.charts.milliseconds')
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
  document.addEventListener('click', handleClickOutside)

  // Connect to WebSocket for real-time updates
  socketStore.connect()
  socketStore.onNewRequest(handleNewRequest)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  socketStore.clearListeners()
  // Note: Keep socket connected for navigation to other pages
})

watch(() => chartsStore.timelineData, updateRequestsChart)
watch(() => chartsStore.modelDistribution, updateModelsChart)
watch(() => toolStats.value, updateToolsChart)
watch(() => timeFilter.value, () => {
  loadTimingData()
  loadSuccessRateData()
})
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
