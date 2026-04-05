<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <router-link to="/" class="brand">
        <div class="brand-icon">
          <i class="bi bi-lightning-charge-fill"></i>
        </div>
        <span>{{ $t('app.name') }}</span>
      </router-link>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <div class="nav-section-title">{{ $t('nav.overview') }}</div>
        <ul class="nav-items">
          <li class="nav-item">
            <router-link to="/" class="nav-link" :class="{ active: currentRoute === 'Dashboard' }">
              <i class="bi bi-speedometer2"></i>
              {{ $t('nav.dashboard') }}
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/sessions" class="nav-link" :class="{ active: currentRoute === 'Sessions' || currentRoute === 'SessionDetail' }">
              <i class="bi bi-collection"></i>
              {{ $t('nav.sessions') }}
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/analysis" class="nav-link" :class="{ active: currentRoute === 'Analysis' }">
              <i class="bi bi-graph-up"></i>
              {{ $t('nav.analysis') }}
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/recycle-bin" class="nav-link" :class="{ active: currentRoute === 'RecycleBin' }">
              <i class="bi bi-recycle"></i>
              {{ $t('nav.recycleBin') }}
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/cleanup-logs" class="nav-link" :class="{ active: currentRoute === 'CleanupLogs' }">
              <i class="bi bi-journal-text"></i>
              {{ $t('nav.cleanupLogs') }}
            </router-link>
          </li>
          <li class="nav-item">
            <router-link to="/settings" class="nav-link" :class="{ active: currentRoute === 'Settings' }">
              <i class="bi bi-gear"></i>
              {{ $t('nav.settings') }}
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

<style scoped>
.sidebar {
  width: 240px;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 18px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  background: var(--primary);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.sidebar-nav {
  padding: 16px 0;
}

.nav-section {
  margin-bottom: 24px;
}

.nav-section-title {
  padding: 0 20px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.nav-items {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin: 2px 0;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-link:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-link.active {
  background: rgba(99, 102, 241, 0.08);
  color: var(--primary);
  border-left-color: var(--primary);
}

.nav-link i {
  font-size: 16px;
  width: 20px;
  text-align: center;
}
</style>
