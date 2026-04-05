import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'

// Import i18n
import i18n from './i18n'
import { useLocaleStore } from './stores/locale'

const app = createApp(App)

// Use Pinia first (before i18n to allow store initialization)
const pinia = createPinia()
app.use(pinia)

// Use i18n
app.use(i18n)

// Initialize locale store
const localeStore = useLocaleStore()
const savedLocale = localeStore.init()
if (savedLocale) {
  i18n.global.locale.value = savedLocale
}

// Use router
app.use(router)

app.mount('#app')
