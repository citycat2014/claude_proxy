<template>
  <div v-if="store.currentSession">
    <!-- Breadcrumb -->
    <div class="breadcrumb">
      <router-link to="/sessions">Sessions</router-link>
      <span class="separator">/</span>
      <span class="current">{{ store.currentSession.session_id.substring(0, 16) }}...</span>
    </div>

    <!-- Session Info Card -->
    <div class="card" style="margin-bottom: 24px;">
      <div class="card-header">
        <h3 class="card-title">
          <i class="bi bi-info-circle"></i>
          Session Information
        </h3>
      </div>
      <div class="card-body">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
          <div>
            <label style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px;">Session ID</label>
            <code>{{ store.currentSession.session_id }}</code>
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px;">Started</label>
            <span>{{ formatDateTime(store.currentSession.started_at) }}</span>
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px;">Model</label>
            <span class="badge badge-primary">{{ formatModel(store.currentSession.model) }}</span>
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px;">Working Directory</label>
            <span>{{ store.currentSession.working_directory || '-' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Requests Section -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="bi bi-chat-dots"></i>
          Requests ({{ store.sessionPagination?.total || 0 }})
        </h3>
      </div>
      <div class="card-body">
        <!-- Requests List -->
        <div v-if="store.sessionRequests.length > 0">
          <div
            v-for="request in store.sessionRequests"
            :key="request.request_id"
            class="message-bubble"
          >
            <div class="message-role-header">
              <div class="message-avatar user">
                <i class="bi bi-person"></i>
              </div>
              <span class="message-role-label">User</span>
              <span style="font-size: 12px; color: var(--text-muted);">
                {{ formatDateTime(request.timestamp) }}
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
        <div v-else-if="!store.loading" class="empty-state">
          <div class="empty-state-icon"><i class="bi bi-inbox"></i></div>
          <div class="empty-state-title">No requests in this session</div>
        </div>

        <!-- Loading -->
        <div v-if="store.loading" class="loading">
          <div class="loading-spinner"></div>
          Loading requests...
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <nav v-if="store.sessionPagination && store.sessionPagination.total_pages > 1" style="padding: 16px;">
      <ul class="pagination">
        <li
          v-if="store.sessionPagination.page > 1"
          class="page-item"
          @click="changePage(store.sessionPagination.page - 1)"
        >
          <a href="#"><i class="bi bi-chevron-left"></i></a>
        </li>
        <li
          v-for="pageNum in displayedPages"
          :key="pageNum"
          class="page-item"
          :class="{ active: pageNum === store.sessionPagination.page }"
          @click="changePage(pageNum)"
        >
          <a href="#">{{ pageNum }}</a>
        </li>
        <li
          v-if="store.sessionPagination.page < store.sessionPagination.total_pages"
          class="page-item"
          @click="changePage(store.sessionPagination.page + 1)"
        >
          <a href="#"><i class="bi bi-chevron-right"></i></a>
        </li>
      </ul>
    </nav>
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
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { formatDateTime, formatModel } from '@/utils/formatters'

const route = useRoute()
const store = useSessionsStore()

const sessionId = route.params.id

const displayedPages = computed(() => {
  if (!store.sessionPagination) return []
  const pages = []
  const total = store.sessionPagination.total_pages
  const current = store.sessionPagination.page

  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - 1 && i <= current + 1)) {
      pages.push(i)
    } else if (i === current - 2 || i === current + 2) {
      pages.push('...')
    }
  }
  return pages.filter((p, idx, arr) => p !== '...' || arr[idx - 1] !== '...')
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
