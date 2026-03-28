<template>
  <div class="app-container">
    <Sidebar :current-route="$route.name" />
    <main class="main-content">
      <TopHeader :title="pageTitle" />
      <div class="content-area">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import TopHeader from '@/components/TopHeader.vue'

const route = useRoute()

const pageTitle = computed(() => {
  return route.meta.title || 'Dashboard'
})
</script>
