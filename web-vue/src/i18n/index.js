import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import zhCN from './locales/zh-CN.json'

// List of supported locales
export const supportedLocales = [
  { code: 'en', name: 'English', flag: 'us' },
  { code: 'zh-CN', name: '简体中文', flag: 'cn' }
]

// Default locale
export const defaultLocale = 'en'

// Messages object
const messages = {
  en,
  'zh-CN': zhCN
}

// Create i18n instance
const i18n = createI18n({
  legacy: false, // Use Composition API
  locale: defaultLocale, // Default locale
  fallbackLocale: 'en', // Fallback if translation missing
  messages,
  // Number formatting
  numberFormats: {
    en: {
      currency: {
        style: 'currency',
        currency: 'USD'
      },
      percent: {
        style: 'percent',
        minimumFractionDigits: 1
      }
    },
    'zh-CN': {
      currency: {
        style: 'currency',
        currency: 'CNY'
      },
      percent: {
        style: 'percent',
        minimumFractionDigits: 1
      }
    }
  },
  // DateTime formatting
  datetimeFormats: {
    en: {
      short: {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      },
      long: {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }
    },
    'zh-CN': {
      short: {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      },
      long: {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }
    }
  }
})

export default i18n

// Helper function to set locale
export function setI18nLocale(i18nInstance, locale) {
  if (i18nInstance.mode === 'legacy') {
    i18nInstance.global.locale = locale
  } else {
    i18nInstance.global.locale.value = locale
  }
}
