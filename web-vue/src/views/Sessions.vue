<template>
  <div>
    <div class="page-header">
      <h1>{{ $t('sessions.title') }}</h1>
      <p>{{ $t('sessions.subtitle') }}</p>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar" style="margin-bottom: 20px; padding: 16px; background: var(--bg-secondary); border-radius: var(--radius); border: 1px solid var(--border-color);">
      <div class="filter-row" style="display: flex; gap: 16px; align-items: end; flex-wrap: wrap;">
        <div class="filter-group" style="flex: 1; min-width: 200px;">
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px;">{{ $t('sessions.filters.sessionId') }}</label>
          <input
            v-model="filters.sessionId"
            type="text"
            :placeholder="$t('sessions.filters.searchSessionId')"
            @keyup.enter="applyFilters"
            style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary);"
          />
        </div>
        <div class="filter-group" style="flex: 1; min-width: 200px;">
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px;">{{ $t('sessions.filters.requestId') }}</label>
          <input
            v-model="filters.requestId"
            type="text"
            :placeholder="$t('sessions.filters.searchRequestId')"
            @keyup.enter="applyFilters"
            style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary);"
          />
        </div>
        <div class="filter-group" style="flex: 1; min-width: 150px;">
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px;">{{ $t('sessions.filters.model') }}</label>
          <select v-model="filters.model" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary);">
            <option value="">{{ $t('sessions.filters.allModels') }}</option>
            <option value="claude">Claude</option>
            <option value="kimi">Kimi</option>
            <option value="gpt">GPT</option>
          </select>
        </div>
        <div class="filter-group" style="flex: 0.8; min-width: 140px;">
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px;">{{ $t('sessions.filters.fromDate') }}</label>
          <input v-model="filters.dateFrom" type="date" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary);" />
        </div>
        <div class="filter-group" style="flex: 0.8; min-width: 140px;">
          <label style="display: block; font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px;">{{ $t('sessions.filters.toDate') }}</label>
          <input v-model="filters.dateTo" type="date" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: var(--radius); background: var(--bg-primary); color: var(--text-primary);" />
        </div>
        <div class="filter-group" style="flex: 0; min-width: auto;">
          <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px; cursor: pointer;">
            <input
              v-model="filters.failedOnly"
              @change="applyFilters"
              type="checkbox"
              style="width: 16px; height: 16px; cursor: pointer;"
            />
            {{ $t('sessions.filters.failedOnly') }}
          </label>
        </div>
        <div class="filter-actions" style="display: flex; gap: 8px;">
          <button @click="applyFilters" class="btn btn-primary" style="padding: 8px 16px;">
            <i class="bi bi-search"></i> {{ $t('common.search') }}
          </button>
          <button @click="clearFilters" class="btn btn-outline" style="padding: 8px 16px;">
            <i class="bi bi-x-circle"></i> {{ $t('common.clear') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Results Info -->
    <div v-if="store.hasFilters" style="margin-bottom: 12px; padding: 8px 12px; background: var(--bg-secondary); border-radius: var(--radius); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
      <span style="color: var(--text-secondary); font-size: 13px;">
        {{ $t('sessions.results.foundSessions', { count: store.total }) }}
      </span>
      <span v-if="filters.failedOnly" style="color: var(--danger); font-size: 12px; font-weight: 500;">
        <i class="bi bi-exclamation-circle"></i> {{ $t('sessions.results.failedOnly') }}
      </span>
      <button @click="clearFilters" style="background: none; border: none; color: var(--primary); font-size: 13px; cursor: pointer; text-decoration: underline;">
        {{ $t('sessions.results.clearFilters') }}
      </button>
    </div>

    <!-- Sessions Table -->
    <div class="card">
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>{{ $t('sessions.table.sessionId') }}</th>
              <th>{{ $t('sessions.table.started') }}</th>
              <th>{{ $t('sessions.table.model') }}</th>
              <th>{{ $t('sessions.table.requests') }}</th>
              <th>{{ $t('sessions.table.inputTokens') }}</th>
              <th>{{ $t('sessions.table.outputTokens') }}</th>
              <th>{{ $t('sessions.table.cost') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="8" class="text-center">
                <div class="loading">
                  <div class="loading-spinner"></div>
                  {{ $t('sessions.loading') }}
                </div>
              </td>
            </tr>
            <tr v-else-if="store.error">
              <td colspan="8">
                <div class="error-state">
                  <i class="bi bi-exclamation-triangle" style="font-size: 32px; color: var(--warning); margin-bottom: 12px;"></i>
                  <div style="color: var(--text-primary); font-weight: 500; margin-bottom: 8px;">{{ $t('sessions.error.title') }}</div>
                  <div style="color: var(--text-secondary); font-size: 12px;">{{ store.error }}</div>
                </div>
              </td>
            </tr>
            <template v-else-if="store.sessions.length > 0">
              <tr v-for="session in store.sessions" :key="session.session_id">
                <td><code>{{ session.session_id.substring(0, 16) }}...</code></td>
                <td>{{ formatDateTime(session.started_at) }}</td>
                <td>
                  <span class="badge badge-primary">{{ formatModel(session.model) }}</span>
                </td>
                <td>{{ session.total_requests }}</td>
                <td>{{ formatTokens(session.total_input_tokens) }}</td>
                <td>{{ formatTokens(session.total_output_tokens) }}</td>
                <td><strong>{{ formatCost(session.total_cost) }}</strong></td>
                <td>
                  <router-link :to="`/sessions/${session.session_id}`" class="btn btn-sm btn-outline">
                    <i class="bi bi-eye"></i> {{ $t('sessions.table.view') }}
                  </router-link>
                </td>
              </tr>
            </template>
            <tr v-else>
              <td colspan="8">
                <div class="empty-state">
                  <div class="empty-state-icon"><i class="bi bi-inbox"></i></div>
                  <div class="empty-state-title">
                    {{ store.hasFilters ? $t('sessions.empty.withFilters') : $t('sessions.empty.noFilters') }}
                  </div>
                  <p>{{ store.hasFilters ? $t('sessions.empty.tryAdjusting') : $t('sessions.empty.willAppear') }}</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <nav v-if="store.totalPages > 1" style="padding: 16px;">
        <ul class="pagination">
          <li v-if="store.page > 1" class="page-item" @click="changePage(store.page - 1)">
            <a href="#"><i class="bi bi-chevron-left"></i></a>
          </li>
          <li
            v-for="pageNum in displayedPages"
            :key="pageNum"
            class="page-item"
            :class="{ active: pageNum === store.page }"
            @click="changePage(pageNum)"
          >
            <a href="#">{{ pageNum }}</a>
          </li>
          <li v-if="store.page < store.totalPages" class="page-item" @click="changePage(store.page + 1)">
            <a href="#"><i class="bi bi-chevron-right"></i></a>
          </li>
        </ul>
      </nav>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { formatDateTime, formatTokens, formatCost, formatModel } from '@/utils/formatters'

const { t } = useI18n()
const store = useSessionsStore()

const filters = ref({
  sessionId: '',
  requestId: '',
  model: '',
  dateFrom: '',
  dateTo: '',
  failedOnly: false
})

const displayedPages = computed(() => {
  const pages = []
  const total = store.totalPages
  const current = store.page

  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - 1 && i <= current + 1)) {
      pages.push(i)
    } else if (i === current - 2 || i === current + 2) {
      pages.push('...')
    }
  }
  return pages.filter((p, idx, arr) => p !== '...' || arr[idx - 1] !== '...')
})

function applyFilters() {
  store.setFilters({
    sessionId: filters.value.sessionId,
    requestId: filters.value.requestId,
    model: filters.value.model,
    dateFrom: filters.value.dateFrom,
    dateTo: filters.value.dateTo,
    failedOnly: filters.value.failedOnly
  })
}

function clearFilters() {
  filters.value = {
    sessionId: '',
    requestId: '',
    model: '',
    dateFrom: '',
    dateTo: '',
    failedOnly: false
  }
  store.clearFilters()
}

function changePage(page) {
  store.fetchSessions(page)
}

onMounted(() => {
  store.fetchSessions(1)
})
</script>
