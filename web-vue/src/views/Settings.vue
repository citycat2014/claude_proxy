<template>
  <div>
    <h1 class="page-title">Settings</h1>

    <!-- Cleanup Settings Section -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="bi bi-trash"></i>
          Data Cleanup Settings
        </h3>
        <button
          v-if="!isEditingSettings && cleanupSettings"
          class="btn btn-sm btn-primary"
          @click="startEditSettings"
        >
          <i class="bi bi-pencil"></i> Edit
        </button>
      </div>
      <div class="card-body">
        <div v-if="cleanupSettings" class="cleanup-settings">
          <!-- Enable/Disable -->
          <div class="setting-row">
            <div class="setting-label">
              <span>Enable Auto Cleanup</span>
              <span class="setting-desc">Automatically clean old data to save space</span>
            </div>
            <label class="switch">
              <input
                type="checkbox"
                v-model="editableSettings.cleanup_enabled"
                :disabled="!isEditingSettings"
              >
              <span class="slider"></span>
            </label>
          </div>

          <div class="setting-row">
            <div class="setting-label">
              <span>Enable Recycle Bin</span>
              <span class="setting-desc">Move cleaned data to recycle bin instead of deleting</span>
            </div>
            <label class="switch">
              <input
                type="checkbox"
                v-model="editableSettings.recycle_bin_enabled"
                :disabled="!isEditingSettings"
              >
              <span class="slider"></span>
            </label>
          </div>

          <!-- Data Retention Days -->
          <div class="setting-row">
            <div class="setting-label">
              <span>Data Retention Days</span>
              <span class="setting-desc">Keep full data for this many days before cleanup</span>
            </div>
            <div class="setting-control">
              <input
                type="number"
                v-model.number="editableSettings.data_retention_days"
                class="form-input number-input"
                min="1"
                max="365"
                :disabled="!isEditingSettings"
              />
              <span class="unit">days</span>
            </div>
          </div>

          <!-- Recycle Bin Retention -->
          <div class="setting-row">
            <div class="setting-label">
              <span>Recycle Bin Retention</span>
              <span class="setting-desc">Keep data in recycle bin before permanent deletion</span>
            </div>
            <div class="setting-control">
              <input
                type="number"
                v-model.number="editableSettings.recycle_bin_retention_days"
                class="form-input number-input"
                min="1"
                max="30"
                :disabled="!isEditingSettings"
              />
              <span class="unit">days</span>
            </div>
          </div>

          <!-- Cleanup Interval -->
          <div class="setting-row">
            <div class="setting-label">
              <span>Cleanup Check Interval</span>
              <span class="setting-desc">How often to check for old data</span>
            </div>
            <div class="setting-control">
              <input
                type="number"
                v-model.number="editableSettings.cleanup_interval_hours"
                class="form-input number-input"
                min="1"
                max="168"
                :disabled="!isEditingSettings"
              />
              <span class="unit">hours</span>
            </div>
          </div>
        </div>

        <div v-else class="loading">Loading settings...</div>

        <!-- Edit Actions -->
        <div v-if="isEditingSettings" class="edit-actions">
          <button class="btn btn-outline" @click="cancelEditSettings">
            <i class="bi bi-x"></i> Cancel
          </button>
          <button class="btn btn-primary" @click="saveSettings" :disabled="savingSettings">
            <i class="bi bi-check"></i>
            {{ savingSettings ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>

        <!-- Actions (view mode) -->
        <div class="cleanup-actions" v-if="cleanupSettings && !isEditingSettings">
          <button class="btn btn-secondary" @click="showCleanupStats">
            <i class="bi bi-bar-chart"></i> View Stats
          </button>
          <button class="btn btn-warning" @click="runCleanup" :disabled="runningCleanup">
            <i class="bi bi-play-circle"></i>
            {{ runningCleanup ? 'Running...' : 'Run Cleanup Now' }}
          </button>
          <button class="btn btn-primary" @click="viewRecycleBin">
            <i class="bi bi-recycle"></i> View Recycle Bin
          </button>
        </div>
      </div>
    </div>

    <!-- Cleanup Stats Modal -->
    <div class="modal" v-if="showStatsModal">
      <div class="modal-overlay" @click="showStatsModal = false"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h3>Cleanup Statistics</h3>
          <button class="btn btn-sm btn-outline" @click="showStatsModal = false">
            <i class="bi bi-x"></i>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="cleanupStats" class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{{ cleanupStats.total_cleanups }}</div>
              <div class="stat-label">Total Cleanups</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ formatNumber(cleanupStats.total_records_processed) }}</div>
              <div class="stat-label">Records Processed</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ cleanupStats.total_space_reclaimed_mb }} MB</div>
              <div class="stat-label">Space Reclaimed</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ cleanupStats.recent_cleanups_7d }}</div>
              <div class="stat-label">Last 7 Days</div>
            </div>
          </div>

          <div v-if="recycleBinStats" class="recycle-bin-stats">
            <h4>Recycle Bin</h4>
            <div class="stat-row">
              <span>Total Entries:</span>
              <span class="value">{{ recycleBinStats.total_entries }}</span>
            </div>
            <div class="stat-row">
              <span>Total Size:</span>
              <span class="value">{{ recycleBinStats.total_size_mb }} MB</span>
            </div>
            <div class="stat-row">
              <span>Expiring Soon:</span>
              <span class="value">{{ recycleBinStats.expiring_soon }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- URL Filters Section -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="bi bi-filter"></i>
          URL Filters
        </h3>
        <button class="btn btn-primary" @click="showAddModal = true">
          <i class="bi bi-plus"></i> Add Filter
        </button>
      </div>
      <div class="card-body">
        <!-- Stats -->
        <div class="filter-stats" v-if="stats">
          <div class="stat-item">
            <span class="stat-value">{{ stats.total }}</span>
            <span class="stat-label">Total Rules</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-success">{{ stats.enabled }}</span>
            <span class="stat-label">Enabled</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-muted">{{ stats.disabled }}</span>
            <span class="stat-label">Disabled</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-primary">{{ stats.include_rules }}</span>
            <span class="stat-label">Include</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-warning">{{ stats.exclude_rules }}</span>
            <span class="stat-label">Exclude</span>
          </div>
        </div>

        <!-- Filters Table -->
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Name</th>
                <th>Pattern</th>
                <th>Type</th>
                <th>Action</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="filter in sortedFilters" :key="filter.id" :class="{ 'disabled-row': !filter.is_enabled }">
                <td>{{ filter.priority }}</td>
                <td>{{ filter.name }}</td>
                <td class="pattern-cell">{{ filter.pattern }}</td>
                <td><span class="badge">{{ filter.filter_type }}</span></td>
                <td>
                  <span class="badge" :class="filter.action === 'include' ? 'badge-success' : 'badge-warning'">
                    {{ filter.action }}
                  </span>
                </td>
                <td>
                  <label class="switch">
                    <input type="checkbox" v-model="filter.is_enabled" @change="toggleFilter(filter)">
                    <span class="slider"></span>
                  </label>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline" @click="editFilter(filter)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline btn-danger" @click="deleteFilter(filter.id)">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Test URL Section -->
        <div class="test-section">
          <h4>Test URL</h4>
          <div class="test-input-row">
            <input
              v-model="testUrl"
              type="text"
              class="form-input"
              placeholder="Enter URL to test (e.g., https://api.anthropic.com/v1/messages)"
            />
            <button class="btn btn-secondary" @click="testUrlPattern">
              Test
            </button>
          </div>
          <div v-if="testResult" class="test-result" :class="testResult.allowed ? 'success' : 'denied'">
            <i :class="testResult.allowed ? 'bi bi-check-circle' : 'bi bi-x-circle'"></i>
            {{ testResult.allowed ? 'Would be CAPTURED' : 'Would be IGNORED' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div class="modal" v-if="showAddModal || showEditModal">
      <div class="modal-overlay" @click="closeModal"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingFilter ? 'Edit Filter' : 'Add Filter' }}</h3>
          <button class="btn btn-sm btn-outline" @click="closeModal">
            <i class="bi bi-x"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" type="text" class="form-input" placeholder="e.g., Anthropic API" />
          </div>
          <div class="form-group">
            <label>Pattern</label>
            <input v-model="form.pattern" type="text" class="form-input" placeholder="e.g., api.anthropic.com" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Filter Type</label>
              <select v-model="form.filter_type" class="form-input">
                <option value="domain">Domain (substring match)</option>
                <option value="path">Path (substring match)</option>
                <option value="exact">Exact URL</option>
                <option value="wildcard">Wildcard (*, ?)</option>
                <option value="regex">Regular Expression</option>
              </select>
            </div>
            <div class="form-group">
              <label>Action</label>
              <select v-model="form.action" class="form-input">
                <option value="include">Include (Capture)</option>
                <option value="exclude">Exclude (Ignore)</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Priority (lower = higher priority)</label>
            <input v-model.number="form.priority" type="number" class="form-input" min="0" max="1000" />
          </div>

          <!-- Live Test -->
          <div class="form-group">
            <label>Test Pattern</label>
            <div class="test-input-row">
              <input v-model="formTestUrl" type="text" class="form-input" placeholder="Enter URL to test pattern" />
              <button class="btn btn-secondary" @click="testFormPattern">Test</button>
            </div>
            <div v-if="formTestResult" class="test-result" :class="formTestResult.matched ? 'success' : 'denied'">
              <i :class="formTestResult.matched ? 'bi bi-check-circle' : 'bi bi-x-circle'"></i>
              {{ formTestResult.matched ? 'MATCHES' : 'Does not match' }}
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeModal">Cancel</button>
          <button class="btn btn-primary" @click="saveFilter">
            {{ editingFilter ? 'Update' : 'Add' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// URL Filters (existing)
const filters = ref([])
const stats = ref(null)
const testUrl = ref('')
const testResult = ref(null)
const showAddModal = ref(false)
const showEditModal = ref(false)
const editingFilter = ref(null)
const formTestUrl = ref('')
const formTestResult = ref(null)

// Cleanup Settings (new)
const cleanupSettings = ref(null)
const editableSettings = ref({})
const isEditingSettings = ref(false)
const savingSettings = ref(false)
const cleanupStats = ref(null)
const recycleBinStats = ref(null)
const showStatsModal = ref(false)
const runningCleanup = ref(false)

const form = ref({
  name: '',
  pattern: '',
  filter_type: 'domain',
  action: 'include',
  priority: 100,
  is_enabled: true
})

// Cleanup functions
async function loadCleanupSettings() {
  try {
    const response = await fetch('/api/settings/cleanup')
    if (response.ok) {
      cleanupSettings.value = await response.json()
      // Copy to editable settings
      editableSettings.value = { ...cleanupSettings.value }
    }
  } catch (err) {
    console.error('Failed to load cleanup settings:', err)
  }
}

function startEditSettings() {
  // Copy current settings to editable
  editableSettings.value = { ...cleanupSettings.value }
  isEditingSettings.value = true
}

function cancelEditSettings() {
  isEditingSettings.value = false
  // Reset editable settings
  editableSettings.value = { ...cleanupSettings.value }
}

async function saveSettings() {
  savingSettings.value = true
  try {
    // Update each setting individually
    const settings = [
      { key: 'cleanup_enabled', value: editableSettings.value.cleanup_enabled, type: 'bool' },
      { key: 'recycle_bin_enabled', value: editableSettings.value.recycle_bin_enabled, type: 'bool' },
      { key: 'data_retention_days', value: editableSettings.value.data_retention_days, type: 'int' },
      { key: 'recycle_bin_retention_days', value: editableSettings.value.recycle_bin_retention_days, type: 'int' },
      { key: 'cleanup_interval_hours', value: editableSettings.value.cleanup_interval_hours, type: 'int' },
    ]

    for (const setting of settings) {
      const response = await fetch(`/api/settings/${setting.key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: setting.value, type: setting.type })
      })

      if (!response.ok) {
        throw new Error(`Failed to update ${setting.key}`)
      }
    }

    // Update saved settings
    cleanupSettings.value = { ...editableSettings.value }
    isEditingSettings.value = false
    alert('Settings saved successfully!')
  } catch (err) {
    console.error('Failed to save settings:', err)
    alert('Failed to save settings: ' + err.message)
  } finally {
    savingSettings.value = false
  }
}

async function loadCleanupStats() {
  try {
    const [cleanupRes, recycleRes] = await Promise.all([
      fetch('/api/cleanup/stats'),
      fetch('/api/recycle-bin/stats')
    ])

    if (cleanupRes.ok) {
      cleanupStats.value = await cleanupRes.json()
    }
    if (recycleRes.ok) {
      recycleBinStats.value = await recycleRes.json()
    }
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

async function showCleanupStats() {
  await loadCleanupStats()
  showStatsModal.value = true
}

async function runCleanup() {
  if (!confirm('Run cleanup now? This will clean data older than the retention period.')) return

  runningCleanup.value = true
  try {
    const response = await fetch('/api/cleanup/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })

    if (response.ok) {
      const result = await response.json()
      alert(`Cleanup completed!\nRequests: ${result.requests_cleaned}\nTool calls: ${result.tool_calls_cleaned}\nSpace: ${result.space_reclaimed_bytes} bytes`)
      await loadCleanupStats()
    } else {
      const error = await response.json()
      alert('Cleanup failed: ' + (error.error || 'Unknown error'))
    }
  } catch (err) {
    console.error('Failed to run cleanup:', err)
    alert('Failed to run cleanup')
  } finally {
    runningCleanup.value = false
  }
}

function viewRecycleBin() {
  router.push('/recycle-bin')
}

function formatNumber(num) {
  return num?.toLocaleString() || '0'
}

// URL Filters (existing)
const sortedFilters = computed(() => {
  return [...filters.value].sort((a, b) => a.priority - b.priority)
})

async function loadFilters() {
  try {
    const response = await fetch('/api/url-filters')
    if (response.ok) {
      filters.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load filters:', err)
  }
}

async function loadStats() {
  try {
    const response = await fetch('/api/url-filters/stats')
    if (response.ok) {
      stats.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

async function toggleFilter(filter) {
  try {
    await fetch(`/api/url-filters/${filter.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_enabled: filter.is_enabled })
    })
    loadStats()
  } catch (err) {
    console.error('Failed to toggle filter:', err)
    filter.is_enabled = !filter.is_enabled
  }
}

async function deleteFilter(id) {
  if (!confirm('Are you sure you want to delete this filter?')) return

  try {
    const response = await fetch(`/api/url-filters/${id}`, { method: 'DELETE' })
    if (response.ok) {
      filters.value = filters.value.filter(f => f.id !== id)
      loadStats()
    }
  } catch (err) {
    console.error('Failed to delete filter:', err)
  }
}

function editFilter(filter) {
  editingFilter.value = filter
  form.value = { ...filter }
  showEditModal.value = true
}

async function saveFilter() {
  try {
    const url = editingFilter.value ? `/api/url-filters/${editingFilter.value.id}` : '/api/url-filters'
    const method = editingFilter.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })

    if (response.ok) {
      closeModal()
      loadFilters()
      loadStats()
    } else {
      const error = await response.json()
      alert(error.error || 'Failed to save filter')
    }
  } catch (err) {
    console.error('Failed to save filter:', err)
    alert('Failed to save filter')
  }
}

async function testUrlPattern() {
  if (!testUrl.value) return

  try {
    const response = await fetch('/api/url-filters/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: testUrl.value })
    })

    if (response.ok) {
      testResult.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to test URL:', err)
  }
}

async function testFormPattern() {
  if (!formTestUrl.value || !form.value.pattern) return

  try {
    const response = await fetch('/api/url-filters/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: formTestUrl.value,
        pattern: form.value.pattern,
        filter_type: form.value.filter_type
      })
    })

    if (response.ok) {
      formTestResult.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to test pattern:', err)
  }
}

function closeModal() {
  showAddModal.value = false
  showEditModal.value = false
  editingFilter.value = null
  form.value = {
    name: '',
    pattern: '',
    filter_type: 'domain',
    action: 'include',
    priority: 100,
    is_enabled: true
  }
  formTestResult.value = null
}

onMounted(() => {
  loadFilters()
  loadStats()
  loadCleanupSettings()
})
</script>

<style scoped>
/* Cleanup Settings */
.cleanup-settings {
  margin-bottom: 24px;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-row:has(input:disabled) {
  opacity: 0.7;
}

.setting-label {
  flex: 1;
}

.setting-label span:first-child {
  display: block;
  font-weight: 500;
  color: var(--text-primary);
}

.setting-desc {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.setting-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.number-input {
  width: 80px;
  text-align: center;
}

.number-input:disabled {
  background: var(--bg-secondary);
  cursor: not-allowed;
}

.unit {
  color: var(--text-secondary);
  font-size: 13px;
}

.cleanup-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.edit-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  justify-content: flex-end;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: var(--radius);
  text-align: center;
}

.stat-card .stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-card .stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.recycle-bin-stats {
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.recycle-bin-stats h4 {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
}

.stat-row .value {
  font-weight: 500;
  color: var(--text-primary);
}

/* Filter Stats (existing) */
.filter-stats {
  display: flex;
  gap: 32px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.pattern-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.disabled-row {
  opacity: 0.6;
}

.test-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color);
}

.test-section h4 {
  margin-bottom: 12px;
  font-size: 16px;
  color: var(--text-primary);
}

.test-input-row {
  display: flex;
  gap: 12px;
}

.test-input-row .form-input {
  flex: 1;
}

.test-result {
  margin-top: 12px;
  padding: 12px 16px;
  border-radius: var(--radius);
  font-weight: 500;
}

.test-result.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.test-result.denied {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

/* Switch Toggle */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #6366f1;
}

input:checked + .slider:before {
  transform: translateX(20px);
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
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.badge-success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}
</style>
