<template>
  <div v-if="store.currentSession">
    <!-- Breadcrumb -->
    <div class="breadcrumb">
      <router-link to="/sessions">Sessions</router-link>
      <span class="separator">/</span>
      <span class="current">{{ store.currentSession.session_id.substring(0, 16) }}...</span>
    </div>

    <!-- Session Overview - Two Column Layout -->
    <div class="section-grid section-grid-2">
      <!-- Session Information -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-info-circle"></i>
            Session Information
          </h3>
        </div>
        <div class="card-body">
          <div class="dl-grid">
            <dt>Session ID</dt>
            <dd><code>{{ store.currentSession.session_id }}</code></dd>

            <dt>Started</dt>
            <dd>{{ formatDateTimeDetailed(store.currentSession.started_at) }}</dd>

            <dt>Ended</dt>
            <dd>{{ store.currentSession.ended_at ? formatDateTimeDetailed(store.currentSession.ended_at) : '-' }}</dd>

            <dt>Model</dt>
            <dd>{{ formatModel(store.currentSession.model) }}</dd>

            <dt>Working Directory</dt>
            <dd>{{ store.currentSession.working_directory || '-' }}</dd>
          </div>
        </div>
      </div>

      <!-- Statistics -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            <i class="bi bi-bar-chart"></i>
            Statistics
          </h3>
        </div>
        <div class="card-body">
          <div class="dl-grid">
            <dt>Total Requests</dt>
            <dd>{{ store.currentSession.total_requests }}</dd>

            <dt>Input Tokens</dt>
            <dd>{{ formatTokens(store.currentSession.total_input_tokens) }}</dd>

            <dt>Output Tokens</dt>
            <dd>{{ formatTokens(store.currentSession.total_output_tokens) }}</dd>

            <dt>Total Cost</dt>
            <dd>{{ formatCost(store.currentSession.total_cost) }}</dd>
          </div>
        </div>
      </div>
    </div>

    <!-- Timeline View -->
    <div class="card">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h3 class="card-title">
            <i class="bi bi-clock-history"></i>
            Conversation Timeline
          </h3>
          <span class="text-muted" style="font-size: 12px;">
            {{ store.sessionPagination?.total || 0 }} total
          </span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <label style="font-size: 12px; color: var(--text-secondary);">Filter by Model:</label>
          <select
            v-model="modelFilter"
            style="padding: 6px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary); font-size: 13px; min-width: 150px;"
          >
            <option value="">All Models</option>
            <option v-for="model in availableModels" :key="model" :value="model">{{ model }}</option>
          </select>
        </div>
      </div>

      <!-- Timeline Container -->
      <div style="padding: 24px;">
        <div v-if="store.loading" class="loading" style="text-align: center; padding: 48px;">
          <div class="loading-spinner" style="margin: 0 auto 16px;"></div>
          <div>Loading conversation timeline...</div>
        </div>

        <div v-else-if="filteredRequests.length > 0">
          <div
            v-for="request in filteredRequests"
            :key="request.request_id"
            class="message-bubble"
          >
            <div class="message-role-header">
              <div class="message-avatar user">
                <i class="bi bi-person"></i>
              </div>
              <span class="message-role-label">User</span>
              <span style="font-size: 12px; color: var(--text-muted);">
                {{ formatDateTimeDetailed(request.timestamp) }}
              </span>
            </div>
            <div class="message-content-bubble user">
              <pre>{{ extractUserInput(request.messages_json) }}</pre>

              <!-- Tool Calls Summary -->
              <div v-if="request.tool_calls && request.tool_calls.length > 0" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-light);">
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">
                  <i class="bi bi-tools"></i> {{ request.tool_calls.length }} tool call(s)
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                  <span
                    v-for="tool in request.tool_calls"
                    :key="tool.id"
                    class="badge badge-primary"
                  >
                    {{ tool.tool_name }}
                  </span>
                </div>
              </div>

              <!-- Message Actions -->
              <div class="message-actions">
                <router-link :to="`/requests/${request.request_id}`" class="btn btn-sm btn-outline">
                  <i class="bi bi-eye"></i> View Details
                </router-link>
              </div>
            </div>

            <!-- Assistant Response -->
            <div v-if="request.response_text" style="margin-top: 16px;">
              <div class="message-role-header">
                <div class="message-avatar assistant">
                  <i class="bi bi-robot"></i>
                </div>
                <span class="message-role-label">Assistant</span>
              </div>
              <div class="message-content-bubble">
                <pre>{{ request.response_text }}</pre>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="empty-state">
          <div class="empty-state-icon"><i class="bi bi-inbox"></i></div>
          <div class="empty-state-title">No requests in this session</div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="store.sessionPagination && store.sessionPagination.total_pages > 1" style="display: flex; justify-content: space-between; align-items: center; padding: 16px; border-top: 1px solid var(--border-color);">
        <div style="font-size: 13px; color: var(--text-secondary);">
          Showing {{ filteredRequests.length }} of {{ store.sessionPagination.total }} requests
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button
            class="btn btn-sm btn-outline"
            :disabled="store.sessionPagination.page <= 1"
            @click="changePage(store.sessionPagination.page - 1)"
          >
            <i class="bi bi-chevron-left"></i> Previous
          </button>
          <span style="font-size: 13px; color: var(--text-secondary);">
            Page {{ store.sessionPagination.page }} of {{ store.sessionPagination.total_pages }}
          </span>
          <button
            class="btn btn-sm btn-outline"
            :disabled="store.sessionPagination.page >= store.sessionPagination.total_pages"
            @click="changePage(store.sessionPagination.page + 1)"
          >
            Next <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Loading State -->
  <div v-else-if="store.loading" class="loading">
    <div class="loading-spinner"></div>
    Loading session...
  </div>

  <!-- Error State -->
  <div v-else-if="store.error" class="error-state">
    <i class="bi bi-exclamation-triangle" style="font-size: 48px; margin-bottom: 16px;"></i>
    <div class="empty-state-title">Failed to load session</div>
    <p>{{ store.error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { formatDateTime, formatDateTimeDetailed, formatModel, formatTokens, formatCost } from '@/utils/formatters'

const route = useRoute()
const store = useSessionsStore()

const sessionId = route.params.id
const modelFilter = ref('')

const availableModels = computed(() => {
  const models = new Set(store.sessionRequests.map(r => r.model).filter(Boolean))
  return Array.from(models).sort()
})

const filteredRequests = computed(() => {
  if (!modelFilter.value) return store.sessionRequests
  return store.sessionRequests.filter(r => r.model === modelFilter.value)
})

function extractUserInput(messagesJson) {
  if (!messagesJson) return 'No user input'
  try {
    const messages = JSON.parse(messagesJson)
    for (const msg of messages.reverse()) {
      if (msg.role === 'user') {
        let content = msg.content
        if (typeof content === 'string') {
          // Remove system-reminder sections
          while (content.includes('<system-reminder>') && content.includes('</system-reminder>')) {
            const start = content.indexOf('<system-reminder>')
            const end = content.indexOf('</system-reminder>') + '</system-reminder>'.length
            content = content.slice(0, start) + content.slice(end)
          }
          return content.trim() || 'No user input'
        }
      }
    }
    return 'No user input'
  } catch {
    return 'Error parsing input'
  }
}

function changePage(page) {
  store.fetchSessionDetail(sessionId, page)
}

onMounted(() => {
  store.fetchSessionDetail(sessionId, 1, 20)
})
</script>
