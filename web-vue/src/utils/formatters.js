// Formatting utilities

export function formatNumber(n) {
  if (n === undefined || n === null) return '-'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toLocaleString()
}

export function formatTokens(n) {
  if (n === undefined || n === null) return '0'
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toLocaleString()
}

export function formatCost(c) {
  if (c === undefined || c === null) return '$0.0000'
  const num = typeof c === 'number' ? c : parseFloat(c)
  if (num >= 1) return '$' + num.toFixed(2)
  if (num >= 0.01) return '$' + num.toFixed(3)
  return '$' + num.toFixed(4)
}

export function formatDateTime(d) {
  if (!d) return '-'
  const date = new Date(d)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function formatDateTimeDetailed(d) {
  if (!d) return '-'
  const date = new Date(d)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }) + '.' + date.getMilliseconds().toString().padStart(3, '0')
}

export function formatShortDate(d) {
  if (!d) return '-'
  const date = new Date(d)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatRelativeTime(d) {
  if (!d) return '-'
  const date = new Date(d)
  const now = new Date()
  const diff = now - date
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (seconds < 60) return 'just now'
  if (minutes < 60) return minutes + 'm ago'
  if (hours < 24) return hours + 'h ago'
  if (days < 30) return days + 'd ago'
  return formatShortDate(d)
}

export function formatDuration(ms) {
  if (ms === undefined || ms === null) return '-'
  if (ms >= 1000) return (ms / 1000).toFixed(2) + 's'
  return ms + 'ms'
}

export function formatModel(model) {
  if (!model) return '-'
  if (model.includes('opus')) return 'Claude 3 Opus'
  if (model.includes('sonnet')) return 'Claude 3 Sonnet'
  if (model.includes('haiku')) return 'Claude 3 Haiku'
  return model.split('-').slice(0, 2).join(' ')
}

export function escapeHtml(text) {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// API helper
export async function fetchApi(endpoint) {
  const response = await fetch(endpoint)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

// Copy to clipboard
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    console.error('Failed to copy:', err)
    return false
  }
}
