<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">
        <i class="bi bi-recycle"></i>
        Recycle Bin
      </h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="loadStats">
          <i class="bi bi-arrow-clockwise"></i> Refresh
        </button>
        <button class="btn btn-danger" @click="confirmClearAll" :disabled="stats?.total_entries === 0">
          <i class="bi bi-trash"></i> Clear All
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Entries</span>
          <i class="bi bi-folder text-primary"></i>
        </div>
        <div class="stat-value">{{ formatNumber(stats.total_entries) }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Size</span>
          <i class="bi bi-hdd text-warning"></i>
        </div>
        <div class="stat-value">{{ stats.total_size_mb }} MB</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Expiring Soon</span>
          <i class="bi bi-clock text-danger"></i>
        </div>
        <div class="stat-value">{{ stats.expiring_soon }}</div>
        <div class="stat-subtitle">within 24 hours</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Retention</span>
          <i class="bi bi-calendar text-success"></i>
        </div>
        <div class="stat-value">{{ stats.retention_days }}d</div>
        <div class="stat-subtitle">auto-delete after</div>
      </div>
    </div>

    <!-- By Table Breakdown -->
    <div class="card" v-if="stats?.by_table?.length">
      <div class="card-header">
        <h3 class="card-title">By Table</h3>
      </div>
      <div class="card-body">
        <div class="table-breakdown">
          <div v-for="item in stats.by_table" :key="item.table" class="breakdown-item">
            <span class="table-name">{{ item.table }}</span>
            <span class="count">{{ formatNumber(item.count) }} entries</span>
            <span class="size">{{ item.size_mb }} MB</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Recycle Bin Entries -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Entries</h3>
        <div class="filter-bar">
          <select v-model="tableFilter" @change="loadEntries" class="filter-select">
            <option value="">All Tables</option>
            <option value="requests">Requests</option>
            <option value="tool_calls">Tool Calls</option>
            <option value="messages">Messages</option>
          </select>
        </div>
      </div>
      <div class="card-body">
        <div v-if="loading" class="loading">Loading...</div>

        <div v-else-if="entries.length === 0" class="empty-state">
          <i class="bi bi-inbox"></i>
          <p>Recycle bin is empty</p>
        </div>

        <div v-else class="entries-list">
          <div
            v-for="entry in entries"
            :key="entry.id"
            class="entry-item"
            :class="{ 'expiring-soon': isExpiringSoon(entry) }"
          >
            <div class="entry-header">
              <div class="entry-info">
                <span class="entry-type">{{ entry.original_table }}</span>
                <span class="entry-id">#{{ entry.original_id }}</span>
              </div>
              <div class="entry-actions">
                <button class="btn btn-sm btn-outline" @click="viewDetails(entry)">
                  <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline btn-danger" @click="confirmDelete(entry)">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </div>

            <div class="entry-details">
              <div class="detail-row" v-if="entry.request_id">
                <span class="label">Request:</span>
                <span class="value">{{ entry.request_id }}</span>
              </div>
              <div class="detail-row" v-if="entry.session_id">
                <span class="label">Session:</span>
                <span class="value">{{ entry.session_id }}</span>
              </div>
              <div class="detail-row">
                <span class="label">Cleaned:</span>
                <span class="value">{{ formatDate(entry.cleaned_at) }}</span>
              </div>
              <div class="detail-row">
                <span class="label">Expires:</span>
                <span class="value" :class="{ 'text-danger': isExpiringSoon(entry) }">
                  {{ formatDate(entry.expires_at) }}
                </span>
              </div>
              <div class="detail-row">
                <span class="label">Size:</span>
                <span class="value">{{ entry.content_size_mb }} MB</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="btn btn-sm btn-outline"
            :disabled="page === 1"
            @click="page--; loadEntries()"
          >
            <i class="bi bi-chevron-left"></i>
          </button>
          <span class="page-info">Page {{ page }} of {{ totalPages }}</span>
          <button
            class="btn btn-sm btn-outline"
            :disabled="page === totalPages"
            @click="page++; loadEntries()"
          >
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Entry Detail Modal -->
    <div class="modal" v-if="showDetailModal">
      <div class="modal-overlay" @click="showDetailModal = false"></div>
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>Entry Details</h3>
          <button class="btn btn-sm btn-outline" @click="showDetailModal = false">
            <i class="bi bi-x"></i>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="selectedEntry" class="entry-detail">
            <div class="detail-section">
              <h4>Metadata</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">Original Table</span>
                  <span class="value">{{ selectedEntry.original_table }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Original ID</span>
                  <span class="value">{{ selectedEntry.original_id }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Request ID</span>
                  <span class="value">{{ selectedEntry.request_id || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Session ID</span>
                  <span class="value">{{ selectedEntry.session_id || 'N/A' }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Cleaned At</span>
                  <span class="value">{{ formatDate(selectedEntry.cleaned_at) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Expires At</span>
                  <span class="value">{{ formatDate(selectedEntry.expires_at) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Size</span>
                  <span class="value">{{ selectedEntry.content_size_mb }} MB ({{ formatNumber(selectedEntry.content_size_bytes) }} bytes)</span>
                </div>
                <div class="detail-item">
                  <span class="label">Type</span>
                  <span class="value">{{ selectedEntry.cleanup_type }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <h4>Content Preview</h4>
              <pre class="content-preview">{{ formatContent(selectedEntry.content_data) }}</pre>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="showDetailModal = false">Close</button>
          <button class="btn btn-danger" @click="confirmDelete(selectedEntry); showDetailModal = false">
            <i class="bi bi-trash"></i> Delete Permanently
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const entries = ref([])
const stats = ref(null)
const loading = ref(false)
const page = ref(1)
const perPage = ref(20)
const totalPages = ref(1)
const tableFilter = ref('')

const showDetailModal = ref(false)
const selectedEntry = ref(null)

async function loadEntries() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: page.value,
      per_page: perPage.value,
    })
    if (tableFilter.value) {
      params.append('table', tableFilter.value)
    }

    const response = await fetch(`/api/recycle-bin?${params}`)
    if (response.ok) {
      const data = await response.json()
      entries.value = data.entries
      totalPages.value = data.total_pages
    }
  } catch (err) {
    console.error('Failed to load entries:', err)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await fetch('/api/recycle-bin/stats')
    if (response.ok) {
      stats.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

function viewDetails(entry) {
  selectedEntry.value = entry
  showDetailModal.value = true
}

async function confirmDelete(entry) {
  if (!confirm(`Permanently delete this entry?\n\nTable: ${entry.original_table}\nID: ${entry.original_id}\nSize: ${entry.content_size_mb} MB`)) {
    return
  }

  try {
    const response = await fetch(`/api/recycle-bin/${entry.id}`, {
      method: 'DELETE'
    })

    if (response.ok) {
      entries.value = entries.value.filter(e => e.id !== entry.id)
      await loadStats()
    } else {
      const error = await response.json()
      alert('Failed to delete: ' + (error.error || 'Unknown error'))
    }
  } catch (err) {
    console.error('Failed to delete entry:', err)
    alert('Failed to delete entry')
  }
}

async function confirmClearAll() {
  if (!confirm(`Clear all ${stats.value?.total_entries || 0} entries from recycle bin?\n\nThis will permanently delete ${stats.value?.total_size_mb || 0} MB of data.`)) {
    return
  }

  try {
    const response = await fetch('/api/recycle-bin', {
      method: 'DELETE'
    })

    if (response.ok) {
      const result = await response.json()
      alert(`Cleared ${result.deleted} entries (${result.space_reclaimed_mb} MB)`)
      entries.value = []
      await loadStats()
    } else {
      const error = await response.json()
      alert('Failed to clear: ' + (error.error || 'Unknown error'))
    }
  } catch (err) {
    console.error('Failed to clear recycle bin:', err)
    alert('Failed to clear recycle bin')
  }
}

function isExpiringSoon(entry) {
  if (!entry.expires_at) return false
  const expires = new Date(entry.expires_at)
  const soon = new Date()
  soon.setHours(soon.getHours() + 24)
  return expires <= soon
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function formatNumber(num) {
  return num?.toLocaleString() || '0'
}

function formatContent(content) {
  if (!content) return 'No content'
  // Show first 500 chars of JSON
  const json = JSON.stringify(content, null, 2)
  return json.length > 500 ? json.substring(0, 500) + '\n...' : json
}

onMounted(() => {
  loadEntries()
  loadStats()
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

.table-name {
  flex: 1;
  font-weight: 500;
}

.count {
  color: var(--text-secondary);
}

.size {
  font-weight: 500;
  color: var(--text-primary);
  min-width: 80px;
  text-align: right;
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

/* Entries List */
.entries-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.entry-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px;
}

.entry-item.expiring-soon {
  border-left: 3px solid var(--danger);
}

.entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.entry-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.entry-type {
  font-weight: 600;
  color: var(--primary);
}

.entry-id {
  color: var(--text-secondary);
  font-size: 13px;
}

.entry-actions {
  display: flex;
  gap: 8px;
}

.entry-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.detail-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.detail-row .label {
  color: var(--text-secondary);
  min-width: 60px;
}

.detail-row .value {
  color: var(--text-primary);
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

/* Modal */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.modal-content {
  position: relative;
  background: var(--bg-primary);
  border-radius: var(--radius);
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.modal-lg {
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

/* Detail Sections */
.detail-section {
  margin-bottom: 20px;
}

.detail-section h4 {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item .label {
  font-size: 12px;
  color: var(--text-secondary);
}

.detail-item .value {
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-all;
}

.content-preview {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px;
  font-family: monospace;
  font-size: 12px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
