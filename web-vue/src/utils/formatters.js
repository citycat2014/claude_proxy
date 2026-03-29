// Formatting utilities

/**
 * Format a number for display with configurable options.
 * @param {number} n - Number to format
 * @param {object} options - Formatting options
 * @param {number} options.decimalsM - Decimals for millions (default: 1)
 * @param {number} options.decimalsK - Decimals for thousands (default: 1)
 * @param {string} options.defaultValue - Default value for null/undefined (default: '-')
 * @returns {string} Formatted number
 */
export function formatNumber(n, options = {}) {
  if (n === undefined || n === null) return options.defaultValue || '-'
  const decimalsM = options.decimalsM ?? 1
  const decimalsK = options.decimalsK ?? 1

  if (n >= 1000000) return (n / 1000000).toFixed(decimalsM) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(decimalsK) + 'K'
  return n.toLocaleString()
}

/**
 * Format tokens (alias for formatNumber with token defaults).
 * @param {number} n - Token count
 * @returns {string} Formatted token count
 */
export function formatTokens(n) {
  return formatNumber(n, { decimalsM: 2, decimalsK: 1, defaultValue: '0' })
}

export function formatCost(c) {
  if (c === undefined || c === null) return '$0.0000'
  const num = typeof c === 'number' ? c : parseFloat(c)
  if (num >= 1) return '$' + num.toFixed(2)
  if (num >= 0.01) return '$' + num.toFixed(3)
  return '$' + num.toFixed(4)
}

/**
 * Format a datetime with configurable precision.
 * @param {string|Date} d - Date to format
 * @param {object} options - Formatting options
 * @param {boolean} options.includeSeconds - Include seconds (default: false)
 * @param {boolean} options.includeMilliseconds - Include milliseconds (default: false)
 * @returns {string} Formatted date
 */
export function formatDateTime(d, options = {}) {
  if (!d) return '-'
  const { includeSeconds = false, includeMilliseconds = false } = options
  const date = new Date(d)

  const parts = {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit'
  }

  if (includeSeconds) parts.second = '2-digit'

  let result = date.toLocaleString('en-US', parts)

  if (includeMilliseconds) {
    result += '.' + date.getMilliseconds().toString().padStart(3, '0')
  }

  return result
}

/**
 * Format a datetime with full precision (seconds + milliseconds).
 * @param {string|Date} d - Date to format
 * @returns {string} Formatted date with seconds and milliseconds
 */
export function formatDateTimeDetailed(d) {
  return formatDateTime(d, { includeSeconds: true, includeMilliseconds: true })
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
