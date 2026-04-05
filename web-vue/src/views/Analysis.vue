<template>
  <div>
    <div class="page-header">
      <h1>{{ $t('analysis.title') }}</h1>
      <p>{{ $t('analysis.subtitle') }}</p>
    </div>

    <!-- Token Analysis Section -->
    <div class="card" style="margin-bottom: 24px;">
      <div class="card-header">
        <h3 class="card-title">
          <i class="bi bi-cpu"></i>
          {{ $t('analysis.tokenUsage.title') }}
        </h3>
      </div>
      <div class="card-body">
        <div v-if="tokenLoading" class="loading">
          <div class="loading-spinner"></div>
          {{ $t('analysis.loading') }}
        </div>
        <div v-else-if="tokenData" class="section-grid section-grid-2">
          <!-- Overall Stats -->
          <div>
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">{{ $t('analysis.tokenUsage.overall') }}</h4>
            <div class="stats-grid" style="grid-template-columns: repeat(2, 1fr);">
              <div class="stat-card">
                <div class="stat-header">
                  <span class="stat-label">{{ $t('analysis.tokenUsage.inputTokens') }}</span>
                  <div class="stat-icon primary"><i class="bi bi-arrow-down"></i></div>
                </div>
                <div class="stat-value">{{ formatTokens(tokenData.overall?.input_tokens) }}</div>
              </div>
              <div class="stat-card">
                <div class="stat-header">
                  <span class="stat-label">{{ $t('analysis.tokenUsage.outputTokens') }}</span>
                  <div class="stat-icon success"><i class="bi bi-arrow-up"></i></div>
                </div>
                <div class="stat-value">{{ formatTokens(tokenData.overall?.output_tokens) }}</div>
              </div>
              <div class="stat-card">
                <div class="stat-header">
                  <span class="stat-label">{{ $t('analysis.tokenUsage.totalTokens') }}</span>
                  <div class="stat-icon info"><i class="bi bi-cpu"></i></div>
                </div>
                <div class="stat-value">{{ formatTokens(tokenData.overall?.total_tokens) }}</div>
              </div>
              <div class="stat-card">
                <div class="stat-header">
                  <span class="stat-label">{{ $t('analysis.tokenUsage.totalCost') }}</span>
                  <div class="stat-icon warning"><i class="bi bi-currency-dollar"></i></div>
                </div>
                <div class="stat-value">{{ formatCost(tokenData.overall?.cost) }}</div>
              </div>
            </div>
          </div>

          <!-- By Model -->
          <div v-if="Object.keys(tokenData.by_model || {}).length > 0">
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">{{ $t('analysis.tokenUsage.byModel') }}</h4>
            <div class="table-container">
              <table class="table">
                <thead>
                  <tr>
                    <th>{{ $t('analysis.tokenUsage.model') }}</th>
                    <th>{{ $t('analysis.tokenUsage.input') }}</th>
                    <th>{{ $t('analysis.tokenUsage.output') }}</th>
                    <th>{{ $t('analysis.tokenUsage.cost') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(data, model) in tokenData.by_model" :key="model">
                    <td><span class="badge badge-primary">{{ model }}</span></td>
                    <td>{{ formatTokens(data.input_tokens) }}</td>
                    <td>{{ formatTokens(data.output_tokens) }}</td>
                    <td>{{ formatCost(data.cost) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tool Analysis Section -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="bi bi-tools"></i>
          {{ $t('analysis.toolUsage.title') }}
        </h3>
      </div>
      <div class="card-body">
        <div v-if="toolLoading" class="loading">
          <div class="loading-spinner"></div>
          {{ $t('analysis.loading') }}
        </div>
        <div v-else-if="toolData" class="section-grid section-grid-2">
          <!-- Most Used Tools -->
          <div v-if="toolData.most_used?.length > 0">
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">{{ $t('analysis.toolUsage.mostUsed') }}</h4>
            <ul class="list-group">
              <li v-for="tool in toolData.most_used" :key="tool.name" class="list-item">
                <div class="list-item-content">
                  <div class="list-item-title">{{ tool.name }}</div>
                </div>
                <div class="list-item-meta">
                  <span class="badge badge-primary">{{ tool.calls }} {{ $t('analysis.toolUsage.calls') }}</span>
                  <span v-if="tool.avg_duration_ms" class="text-muted" style="font-size: 12px; margin-left: 8px;">
                    {{ formatDuration(tool.avg_duration_ms) }}
                  </span>
                </div>
              </li>
            </ul>
          </div>

          <!-- Distribution -->
          <div v-if="Object.keys(toolData.distribution || {}).length > 0">
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 16px;">{{ $t('analysis.toolUsage.distribution') }}</h4>
            <div class="table-container">
              <table class="table">
                <thead>
                  <tr>
                    <th>{{ $t('analysis.toolUsage.tool') }}</th>
                    <th>{{ $t('analysis.toolUsage.calls') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(count, tool) in toolData.distribution" :key="tool">
                    <td>{{ tool }}</td>
                    <td><span class="badge badge-primary">{{ count }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <div class="empty-state-icon"><i class="bi bi-tools"></i></div>
          <div class="empty-state-title">{{ $t('analysis.toolUsage.empty') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatTokens, formatCost, formatDuration } from '@/utils/formatters'

const { t } = useI18n()

const tokenData = ref(null)
const toolData = ref(null)
const tokenLoading = ref(false)
const toolLoading = ref(false)

async function loadTokenAnalysis() {
  tokenLoading.value = true
  try {
    const response = await fetch('/api/analysis/tokens')
    if (response.ok) {
      tokenData.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load token analysis:', err)
  } finally {
    tokenLoading.value = false
  }
}

async function loadToolAnalysis() {
  toolLoading.value = true
  try {
    const response = await fetch('/api/analysis/tools')
    if (response.ok) {
      toolData.value = await response.json()
    }
  } catch (err) {
    console.error('Failed to load tool analysis:', err)
  } finally {
    toolLoading.value = false
  }
}

onMounted(() => {
  loadTokenAnalysis()
  loadToolAnalysis()
})
</script>
