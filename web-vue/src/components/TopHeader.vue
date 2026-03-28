<template>
  <header class="top-header">
    <h1 class="page-title">{{ title }}</h1>
    <div class="header-actions">
      <span class="text-muted" style="font-size: 13px;">
        <i class="bi bi-circle-fill" style="color: var(--success); font-size: 8px;"></i>
        System Online
      </span>
    </div>
  </header>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'Dashboard'
  }
})
</script>
