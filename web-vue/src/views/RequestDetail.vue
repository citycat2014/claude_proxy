<template>
  <div v-if="request">
    <!-- Breadcrumb -->
    <div class="breadcrumb">
      <router-link to="/sessions">Sessions</router-link>
      <span class="separator">/</span>
      <router-link :to="`/sessions/${request.session_id}`">Session</router-link>
      <span class="separator">/</span>
      <span class="current">Request</span>
    </div>

    <!-- Metrics Bar -->
    <div class="metrics-bar">
      <div class="metric-card">
        <div class="metric-value">{{ formatTokens(request.input_tokens) }}</div>
        <div class="metric-label">Input Tokens</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ formatTokens(request.output_tokens) }}</div>
        <div class="metric-label">Output Tokens</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ formatCost(request.cost) }}</div>
        <div class="metric-label">Cost</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">{{ formatDuration(request.response_time_ms) }}</div>
        <div class="metric-label">Response Time</div>
      </div>
    </div>

    <!-- Two Column Layout -->
    <div class="two-column-layout">
      <div class="left-column">
        <!-- Request Messages -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">
              <i class="bi bi-chat-dots"></i>
              Messages
            </h3>
          </div>
          <div class="card-body">
            <div v-for="(msg, idx) in parsedMessages" :key="idx" class="message-block">
              <div class="message-header">
                <span class="message-role" :class="msg.role">{{ msg.role }}</span>
              </div>
              <div class="message-content">
                <pre>{{ formatMessageContent(msg.content) }}</pre>
              </div>
            </div>
          </div>
        </div>

        <!-- Response -->
        <div v-if="request.response_text" class="card">
          <div class="card-header">
            <h3 class="card-title">
              <i class="bi bi-robot"></i>
              Assistant Response
            </h3>
          </div>
          <div class="card-body">
            <pre>{{ request.response_text }}</pre>
          </div>
        </div>

        <!-- Thinking -->
        <div v-if="request.response_thinking" class="card">
          <div class="card-header">
            <h3 class="card-title">
              <i class="bi bi-brain"></i>
              Thinking Process
            </h3>
          </div>
          <div class="card-body">
            <pre>{{ request.response_thinking }}</pre>
          </div>
        </div>
      </div>

      <div class="right-column">
        <!-- Metadata Panel -->
        <div class="metadata-panel">
          <div class="metadata-section">
            <div class="metadata-section-title">Request Info</div>
            <div class="metadata-item">
              <span class="metadata-label">Request ID</span>
              <span class="metadata-value">{{ request.request_id }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Session ID</span>
              <router-link :to="`/sessions/${request.session_id}`" class="metadata-value">
                {{ request.session_id }}
              </router-link>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Timestamp</span>
              <span class="metadata-value">{{ formatDateTime(request.timestamp) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Model</span>
              <span class="metadata-value">{{ request.model || '-' }}</span>
            </div>
          </div>

          <div class="metadata-section">
            <div class="metadata-section-title">Token Usage</div>
            <div class="metadata-item">
              <span class="metadata-label">Input Tokens</span>
              <span class="metadata-value">{{ formatNumber(request.input_tokens) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Output Tokens</span>
              <span class="metadata-value">{{ formatNumber(request.output_tokens) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Cache Creation</span>
              <span class="metadata-value">{{ formatNumber(request.cache_creation_tokens) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Cache Read</span>
              <span class="metadata-value">{{ formatNumber(request.cache_read_tokens) }}</span>
            </div>
          </div>

          <div class="metadata-section">
            <div class="metadata-section-title">Tool Calls</div>
            <div v-if="toolCalls.length > 0" class="tool-calls-list">
              <div
                v-for="tool in toolCalls"
                :key="tool.id"
                class="tool-call-item"
              >
                <i class="bi bi-hammer tool-call-item-icon"></i>
                <span class="tool-call-item-name">{{ tool.tool_name }}</span>
                <span class="tool-call-item-time">{{ formatDuration(tool.duration_ms) }}</span>
              </div>
            </div>
            <div v-else class="text-muted" style="font-size: 12px;">
              No tool calls
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Loading -->
  <div v-else-if="loading" class="loading">
    <div class="loading-spinner"></div>
    Loading request...
  </div>

  <!-- Error -->
  <div v-else class="error-state">
    <i class="bi bi-exclamation-triangle" style="font-size: 48px;"></i>
    <div class="empty-state-title">Request not found</div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { formatDateTime, formatNumber, formatTokens, formatCost, formatDuration } from '@/utils/formatters'

const route = useRoute()
const requestId = route.params.id

const request = ref(null)
const toolCalls = ref([])
const loading = ref(false)
const error = ref(null)

const parsedMessages = computed(() => {
  if (!request.value?.messages_json) return []
  try {
    return JSON.parse(request.value.messages_json)
  } catch {
    return []
  }
})

function formatMessageContent(content) {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content.map(c => {
      if (typeof c === 'string') return c
      if (c.text) return c.text
      return JSON.stringify(c)
    }).join('\n')
  }
  return JSON.stringify(content, null, 2)
}

async function loadRequest() {
  loading.value = true
  try {
    const response = await fetch(`/api/requests/${requestId}`)
    if (!response.ok) throw new Error('Request not found')
    const data = await response.json()
    request.value = data.request
    toolCalls.value = data.tool_calls || []
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRequest()
})
</script>
