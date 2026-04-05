<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <router-link to="/" class="brand">
        <div class="brand-icon">
          <i class="bi bi-lightning-charge-fill"></i>
        </div>
        <span>Capture</span>
      </router-link>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <div class="nav-section-title">Overview</div>
        <ul class="nav-items">
          <li class="nav-item">
            <router-link to="/" class="nav-link" :class="{ active: currentRoute === 'Dashboard' }">
              <i class="bi bi-speedometer2"></i>
              Dashboard
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/sessions" class="nav-link" :class="{ active: currentRoute === 'Sessions' || currentRoute === 'SessionDetail' }">
              <i class="bi bi-collection"></i>
              Sessions
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/analysis" class="nav-link" :class="{ active: currentRoute === 'Analysis' }">
              <i class="bi bi-graph-up"></i>
              Analysis
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/settings" class="nav-link" :class="{ active: currentRoute === 'Settings' }">
              <i class="bi bi-gear"></i>
              Settings
            </router-link>
          </li>
        </ul>
      </div>
    </nav>
  </aside>
</template>

<script setup>
defineProps({
  currentRoute: {
    type: String,
    default: ''
  }
})
</script>
