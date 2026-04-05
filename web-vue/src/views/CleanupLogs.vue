<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">
        <i class="bi bi-journal-text"></i>
        {{ $t('cleanupLogs.title') }}
      </h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="loadData">
          <i class="bi bi-arrow-clockwise"></i> {{ $t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('cleanupLogs.stats.totalCleanups') }}</span>
          <i class="bi bi-clipboard-check text-primary"></i>
        </div>
        <div class="stat-value">{{ formatNumber(stats.total_cleanups) }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('cleanupLogs.stats.recordsProcessed') }}</span>
          <i class="bi bi-database text-success"></i>
        </div>
        <div class="stat-value">{{ formatNumber(stats.total_records_processed) }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('cleanupLogs.stats.spaceReclaimed') }}</span>
          <i class="bi bi-hdd text-warning"></i>
        </div>
        <div class="stat-value">{{ stats.total_space_reclaimed_mb }} MB</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">{{ $t('cleanupLogs.stats.recent7d') }}</span>
          <i class="bi bi-calendar-check text-info"></i>
        </div>
        <div class="stat-value">{{ formatNumber(stats.recent_cleanups_7d) }}</div>
        <div class="stat-subtitle">{{ $t('cleanupLogs.stats.cleanupsThisWeek') }}</div>
      </div>
    </div>

    <!-- By Type Breakdown -->
    <div class="card" v-if="stats?.by_type && Object.keys(stats.by_type).length > 0">
      <div class="card-header">
        <h3 class="card-title">{{ $t('cleanupLogs.byType') }}</h3>
      </div>
      <div class="card-body">
        <div class="table-breakdown">
          <div v-for="(count, type) in stats.by_type" :key="type" class="breakdown-item">
            <span class="type-badge" :class="`type-${type}`">
              {{ formatType(type) }}
            </span>
            <span class="count">{{ formatNumber(count) }} {{ $t('cleanupLogs.auto') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Cleanup Logs List -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ $t('cleanupLogs.cleanupHistory') }}</h3>
        <div class="filter-bar">
          <select v-model="typeFilter" @change="loadLogs" class="filter-select">
            <option value="">{{ $t('cleanupLogs.allTypes') }}</option>
            <option value="auto">{{ $t('cleanupLogs.auto') }}</option>
            <option value="manual">{{ $t('cleanupLogs.manual') }}</option>
            <option value="recycle_bin_purge">{{ $t('cleanupLogs.recycleBinPurge') }}</option>
          </select>
        </div>
      </div>
      <div class="card-body">
        <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>

        <div v-else-if="logs.length === 0" class="empty-state">
          <i class="bi bi-inbox"></i>
          <p>{{ $t('cleanupLogs.empty') }}</p>
        </div>

        <div v-else class="logs-list">
          <div
            v-for="log in logs"
            :key="log.id"
            class="log-item"
            :class="`type-${log.cleanup_type}`"
          >
            <div class="log-header">
              <div class="log-info">
                <span class="log-type">{{ formatType(log.cleanup_type) }}</span>
                <span class="log-id">#{{ log.id }}</span>
              </div>
              <div class="log-time">
                <i class="bi bi-clock"></i>
                {{ formatDate(log.started_at) }}
              </div>
            </div>

            <div class="log-stats">
              <div class="stat-item">
                <span class="stat-label">{{ $t('sessions.table.requests') }}</span>
                <span class="stat-value">{{ formatNumber(log.records_processed) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">{{ $t('cleanupLogs.stats.spaceReclaimed') }}</span>
                <span class="stat-value">{{ formatBytes(log.space_reclaimed_bytes) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">{{ $t('nav.recycleBin') }}</span>
                <span class="stat-value">{{ formatNumber(log.recycle_bin_entries) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">{{ $t('common.time') }}</span>
                <span class="stat-value">{{ formatDuration(log.started_at, log.completed_at) }}</span>
              </div>
            </div>

            <div v-if="log.records_by_table" class="log-tables">
              <div v-for="(count, table) in parseRecordsByTable(log.records_by_table)" :key="table" class="table-tag">
                {{ table }}: {{ count }}
              </div>
            </div>

            <div v-if="log.details" class="log-details">
              <details>
                <summary>{{ $t('common.description') }}</summary>
                <pre class="details-content">{{ formatDetails(log.details) }}</pre>
              </details>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="btn btn-sm btn-outline"
            :disabled="page === 1"
            @click="page--; loadLogs()"
          >
            <i class="bi bi-chevron-left"></i>
          </button>
          <span class="page-info">{{ $t('recycleBin.page', { current: page, total: totalPages }) }}</span>
          <button
            class="btn btn-sm btn-outline"
            :disabled="page === totalPages"
            @click="page++; loadLogs()"
          >
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const logs = ref([])
const stats = ref(null)
const loading = ref(false)
const page = ref(1)
const perPage = ref(20)
const totalPages = ref(1)
const typeFilter = ref('')

async function loadLogs() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: page.value,
      per_page: perPage.value,
    })
    if (typeFilter.value) {
      params.append('type', typeFilter.value)
    }

    const response = await fetch(`/api/cleanup/logs?${params}`)
    if (response.ok) {
      const data = await response.json()
      logs.value = data.logs
      totalPages.value = data.total_pages
    }
  } catch (err) {
    console.error('Failed to load cleanup logs:', err)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await fetch('/api/cleanup/stats')
    if (response.ok) {
      stats.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load cleanup stats:', err)
  }
}

function loadData() {
  loadLogs()
  loadStats()
}

function formatType(type) {
  const typeMap = {
    'auto': 'Auto Cleanup',
    'manual': 'Manual Cleanup',
    'recycle_bin_purge': 'Recycle Bin Purge'
  }
  return typeMap[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function formatNumber(num) {
  return num?.toLocaleString() || '0'
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatDuration(started, completed) {
  if (!started || !completed) return 'N/A'
  const start = new Date(started)
  const end = new Date(completed)
  const diff = end - start
  if (diff < 1000) return '< 1s'
  if (diff < 60000) return Math.round(diff / 1000) + 's'
  return Math.round(diff / 60000) + 'm ' + Math.round((diff % 60000) / 1000) + 's'
}

function parseRecordsByTable(recordsJson) {
  try {
    return JSON.parse(recordsJson)
  } catch {
    return {}
  }
}

function formatDetails(detailsJson) {
  try {
    const details = JSON.parse(detailsJson)
    return JSON.stringify(details, null, 2)
  } catch {
    return detailsJson
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px;
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.stat-header i {
  font-size: 20px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

/* Table Breakdown */
.table-breakdown {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius);
}

.type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.type-badge.type-auto {
  background: var(--primary);
  color: white;
}

.type-badge.type-manual {
  background: var(--warning);
  color: white;
}

.type-badge.type-recycle_bin_purge {
  background: var(--danger);
  color: white;
}

.count {
  color: var(--text-secondary);
}

/* Filter Bar */
.filter-bar {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* Logs List */
.logs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px;
  border-left: 3px solid var(--border-color);
}

.log-item.type-auto {
  border-left-color: var(--primary);
}

.log-item.type-manual {
  border-left-color: var(--warning);
}

.log-item.type-recycle_bin_purge {
  border-left-color: var(--danger);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.log-type {
  font-weight: 600;
  color: var(--text-primary);
}

.log-id {
  color: var(--text-secondary);
  font-size: 13px;
}

.log-time {
  color: var(--text-secondary);
  font-size: 13px;
}

.log-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item .stat-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.stat-item .stat-value {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.log-tables {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.table-tag {
  padding: 4px 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  font-size: 12px;
  color: var(--text-secondary);
}

.log-details details {
  font-size: 13px;
}

.log-details summary {
  color: var(--primary);
  cursor: pointer;
}

.details-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 12px;
  margin-top: 8px;
  font-family: monospace;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.page-info {
  color: var(--text-secondary);
}

/* Responsive */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .log-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
