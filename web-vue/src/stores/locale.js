import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { supportedLocales, defaultLocale } from '@/i18n'

const STORAGE_KEY = 'app-locale'

export const useLocaleStore = defineStore('locale', () => {
  // State
  const currentLocale = ref(defaultLocale)
  const initialized = ref(false)

  // Getters
  const currentLanguage = () => {
    const locale = supportedLocales.find(l => l.code === currentLocale.value)
    return locale || supportedLocales[0]
  }

  const isLocaleSupported = (locale) => {
    return supportedLocales.some(l => l.code === locale)
  }

  // Actions
  function init() {
    if (initialized.value) return

    // Load from localStorage
    const savedLocale = localStorage.getItem(STORAGE_KEY)
    if (savedLocale && isLocaleSupported(savedLocale)) {
      currentLocale.value = savedLocale
    } else {
      // Try to detect browser language
      const browserLang = navigator.language
      if (isLocaleSupported(browserLang)) {
        currentLocale.value = browserLang
      } else if (browserLang.startsWith('zh')) {
        // Handle Chinese variants
        currentLocale.value = 'zh-CN'
      }
    }

    initialized.value = true

    // Update document language
    document.documentElement.setAttribute('lang', currentLocale.value)

    return currentLocale.value
  }

  function setLocale(locale) {
    if (!isLocaleSupported(locale)) {
      console.warn(`Locale ${locale} is not supported`)
      return false
    }

    currentLocale.value = locale
    localStorage.setItem(STORAGE_KEY, locale)

    // Update document language
    document.documentElement.setAttribute('lang', locale)

    return true
  }

  // Watch for changes and sync to localStorage
  watch(currentLocale, (newLocale) => {
    localStorage.setItem(STORAGE_KEY, newLocale)
    document.documentElement.setAttribute('lang', newLocale)
  })

  return {
    currentLocale,
    initialized,
    currentLanguage,
    isLocaleSupported,
    init,
    setLocale
  }
})
