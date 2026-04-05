<template>
  <div class="language-switcher">
    <div
      class="language-trigger"
      :class="{ active: isOpen }"
      @click="toggleDropdown"
    >
      <i class="bi bi-globe"></i>
      <span class="language-name">{{ currentLanguage.name }}</span>
      <i class="bi bi-chevron-down" :class="{ rotated: isOpen }"></i>
    </div>

    <div v-if="isOpen" class="language-dropdown">
      <div
        v-for="locale in supportedLocales"
        :key="locale.code"
        class="language-option"
        :class="{ active: locale.code === currentLocale }"
        @click="selectLocale(locale.code)"
      >
        <span class="language-flag">{{ getFlagEmoji(locale.flag) }}</span>
        <span class="language-label">{{ locale.name }}</span>
        <i v-if="locale.code === currentLocale" class="bi bi-check"></i>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'
import { supportedLocales } from '@/i18n'

const { locale } = useI18n()
const localeStore = useLocaleStore()

const isOpen = ref(false)

const currentLocale = computed(() => localeStore.currentLocale)
const currentLanguage = computed(() => localeStore.currentLanguage())

function getFlagEmoji(flagCode) {
  const flagEmojis = {
    us: '🇺🇸',
    cn: '🇨🇳'
  }
  return flagEmojis[flagCode] || '🌐'
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function selectLocale(code) {
  if (localeStore.setLocale(code)) {
    locale.value = code
  }
  isOpen.value = false
}

function handleClickOutside(event) {
  const dropdown = document.querySelector('.language-switcher')
  if (dropdown && !dropdown.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  // Initialize store and sync with i18n
  const savedLocale = localeStore.init()
  if (savedLocale && savedLocale !== locale.value) {
    locale.value = savedLocale
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.language-switcher {
  position: relative;
  display: inline-block;
}

.language-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 13px;
  color: var(--text-secondary);
}

.language-trigger:hover {
  background-color: var(--bg-secondary);
}

.language-trigger.active {
  background-color: var(--bg-secondary);
}

.language-name {
  font-weight: 500;
}

.bi-chevron-down {
  font-size: 10px;
  transition: transform 0.2s;
}

.bi-chevron-down.rotated {
  transform: rotate(180deg);
}

.language-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 160px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  z-index: 100;
  padding: 4px 0;
}

.language-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.language-option:hover {
  background-color: var(--bg-secondary);
}

.language-option.active {
  background-color: rgba(99, 102, 241, 0.08);
}

.language-flag {
  font-size: 14px;
}

.language-label {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}

.language-option .bi-check {
  color: var(--primary);
  font-size: 12px;
}
</style>
