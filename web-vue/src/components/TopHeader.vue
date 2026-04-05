<template>
  <header class="top-header">
    <h1 class="page-title">{{ title }}</h1>
    <div class="header-actions">
      <LanguageSwitcher />
      <span class="text-muted" style="font-size: 13px;">
        <i class="bi bi-circle-fill" style="color: var(--success); font-size: 8px;"></i>
        {{ $t('app.systemOnline') }}
      </span>
    </div>
  </header>
</template>

<script setup>
import LanguageSwitcher from './LanguageSwitcher.vue'

defineProps({
  title: {
    type: String,
    default: 'Dashboard'
  }
})
</script>
